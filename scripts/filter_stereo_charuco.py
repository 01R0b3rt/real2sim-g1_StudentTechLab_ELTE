from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "stereo_charuco"


@dataclass
class PairScore:
    suffix: str
    left_path: Path | None
    right_path: Path | None
    left_count: int
    right_count: int

    @property
    def is_complete(self) -> bool:
        return self.left_path is not None and self.right_path is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete or archive ChArUco stereo pairs with too few detected corners."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Calibration image directory containing left_###.png/right_###.png.",
    )
    parser.add_argument("--min-corners", type=int, default=12, help="Minimum ChArUco corners required on each side.")
    parser.add_argument("--squares-x", type=int, default=5, help="ChArUco board squares across.")
    parser.add_argument("--squares-y", type=int, default=7, help="ChArUco board squares down.")
    parser.add_argument("--dictionary", default="DICT_5X5_50", help="OpenCV aruco dictionary name.")
    parser.add_argument("--yes", action="store_true", help="Delete without an interactive confirmation.")
    parser.add_argument("--dry-run", action="store_true", help="Only list what would be removed.")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Move rejected pairs to data/stereo_charuco_rejected/<timestamp> instead of deleting.",
    )
    parser.add_argument(
        "--keep-incomplete",
        action="store_true",
        help="Do not remove incomplete pairs where one side is missing.",
    )
    return parser.parse_args()


def resolve_input_dir(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def ensure_safe_directory(input_dir: Path) -> None:
    project_root = PROJECT_ROOT.resolve()
    try:
        input_dir.relative_to(project_root)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to filter a directory outside the project: {input_dir}") from exc
    if input_dir == project_root:
        raise RuntimeError("Refusing to filter the project root.")


def make_board(cv2, args: argparse.Namespace):
    dictionary_id = getattr(cv2.aruco, args.dictionary)
    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    board = cv2.aruco.CharucoBoard((args.squares_x, args.squares_y), 1.0, 0.7475, dictionary)
    return board, dictionary


def detect_count(cv2, image_path: Path, board, dictionary) -> int:
    image = cv2.imread(str(image_path))
    if image is None:
        return 0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    marker_corners, marker_ids, _ = detector.detectMarkers(gray)
    if marker_ids is None or len(marker_ids) == 0:
        return 0
    count, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
        marker_corners,
        marker_ids,
        gray,
        board,
    )
    if charuco_corners is None or charuco_ids is None:
        return 0
    return int(count)


def collect_pair_paths(input_dir: Path) -> list[tuple[str, Path | None, Path | None]]:
    suffixes: set[str] = set()
    left_lookup: dict[str, Path] = {}
    right_lookup: dict[str, Path] = {}
    for path in input_dir.glob("left_*.png"):
        suffix = path.stem.split("_")[-1]
        suffixes.add(suffix)
        left_lookup[suffix] = path
    for path in input_dir.glob("right_*.png"):
        suffix = path.stem.split("_")[-1]
        suffixes.add(suffix)
        right_lookup[suffix] = path
    return [(suffix, left_lookup.get(suffix), right_lookup.get(suffix)) for suffix in sorted(suffixes)]


def score_pairs(cv2, input_dir: Path, board, dictionary) -> list[PairScore]:
    scores: list[PairScore] = []
    for suffix, left_path, right_path in collect_pair_paths(input_dir):
        left_count = detect_count(cv2, left_path, board, dictionary) if left_path else 0
        right_count = detect_count(cv2, right_path, board, dictionary) if right_path else 0
        scores.append(PairScore(suffix, left_path, right_path, left_count, right_count))
    return scores


def rejected_scores(scores: list[PairScore], min_corners: int, keep_incomplete: bool) -> list[PairScore]:
    rejected: list[PairScore] = []
    for score in scores:
        if not score.is_complete:
            if not keep_incomplete:
                rejected.append(score)
            continue
        if score.left_count < min_corners or score.right_count < min_corners:
            rejected.append(score)
    return rejected


def files_for(scores: list[PairScore]) -> list[Path]:
    files: list[Path] = []
    for score in scores:
        if score.left_path is not None:
            files.append(score.left_path)
        if score.right_path is not None:
            files.append(score.right_path)
    return files


def confirm(rejected: list[PairScore], min_corners: int, archive: bool) -> bool:
    action = "archive" if archive else "delete"
    print(f"About to {action} {len(rejected)} stereo pairs with either side below {min_corners} corners.")
    answer = input("Type DELETE to continue: ").strip()
    return answer == "DELETE"


def print_summary(scores: list[PairScore], rejected: list[PairScore], min_corners: int) -> None:
    kept = len(scores) - len(rejected)
    print(f"Checked {len(scores)} stereo pairs.")
    print(f"Keeping {kept} pairs with left/right corners >= {min_corners}.")
    print(f"Rejecting {len(rejected)} weak or incomplete pairs.")
    if rejected:
        print("Rejected pairs:")
        for score in rejected[:40]:
            completeness = "" if score.is_complete else " incomplete"
            print(
                f"  {score.suffix}: left={score.left_count:2d} "
                f"right={score.right_count:2d}{completeness}"
            )
        if len(rejected) > 40:
            print(f"  ... and {len(rejected) - 40} more")


def main() -> int:
    try:
        import cv2
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run pip install -r requirements.txt first.")
        return 2

    args = parse_args()
    input_dir = resolve_input_dir(args.input_dir)
    ensure_safe_directory(input_dir)
    if not input_dir.exists():
        print(f"No calibration image directory found: {input_dir}")
        return 0

    board, dictionary = make_board(cv2, args)
    scores = score_pairs(cv2, input_dir, board, dictionary)
    if not scores:
        print(f"No left_*.png/right_*.png calibration pairs found in: {input_dir}")
        return 0

    rejected = rejected_scores(scores, args.min_corners, args.keep_incomplete)
    print_summary(scores, rejected, args.min_corners)
    if not rejected:
        print("Nothing to remove.")
        return 0
    if args.dry_run:
        print("Dry run only. No files changed.")
        return 0
    if not args.yes and not confirm(rejected, args.min_corners, args.archive):
        print("Cancelled. No files changed.")
        return 1

    remove_files = files_for(rejected)
    if args.archive:
        archive_dir = PROJECT_ROOT / "data" / "stereo_charuco_rejected" / datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir.mkdir(parents=True, exist_ok=True)
        for path in remove_files:
            shutil.move(str(path), str(archive_dir / path.name))
        print(f"Archived {len(remove_files)} images from {len(rejected)} rejected pairs to: {archive_dir}")
    else:
        for path in remove_files:
            path.unlink()
        print(f"Deleted {len(remove_files)} images from {len(rejected)} rejected pairs.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
