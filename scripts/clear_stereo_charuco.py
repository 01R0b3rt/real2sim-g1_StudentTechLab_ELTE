from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "stereo_charuco"
PATTERNS = ("left_*.png", "right_*.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete old ChArUco stereo calibration image pairs before a new capture."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Calibration image directory containing left_###.png/right_###.png.",
    )
    parser.add_argument("--yes", action="store_true", help="Delete without an interactive confirmation.")
    parser.add_argument("--dry-run", action="store_true", help="Only list what would be deleted.")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Move images to data/stereo_charuco_archive/<timestamp> instead of deleting.",
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
        raise RuntimeError(f"Refusing to clean a directory outside the project: {input_dir}") from exc
    if input_dir == project_root:
        raise RuntimeError("Refusing to clean the project root.")


def find_calibration_images(input_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in PATTERNS:
        files.extend(input_dir.glob(pattern))
    return sorted(path for path in files if path.is_file())


def confirm(files: list[Path], input_dir: Path, archive: bool) -> bool:
    action = "archive" if archive else "delete"
    print(f"About to {action} {len(files)} calibration image files from:")
    print(f"  {input_dir}")
    print("Only these patterns are affected:")
    for pattern in PATTERNS:
        print(f"  {pattern}")
    answer = input("Type DELETE to continue: ").strip()
    return answer == "DELETE"


def main() -> int:
    args = parse_args()
    input_dir = resolve_input_dir(args.input_dir)
    ensure_safe_directory(input_dir)

    if not input_dir.exists():
        print(f"No calibration image directory found: {input_dir}")
        return 0

    files = find_calibration_images(input_dir)
    if not files:
        print(f"No ChArUco calibration images found in: {input_dir}")
        return 0

    print(f"Found {len(files)} ChArUco calibration image files.")
    for path in files[:10]:
        print(f"  {path.name}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")

    if args.dry_run:
        print("Dry run only. No files changed.")
        return 0

    if not args.yes and not confirm(files, input_dir, args.archive):
        print("Cancelled. No files changed.")
        return 1

    if args.archive:
        archive_dir = PROJECT_ROOT / "data" / "stereo_charuco_archive" / datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir.mkdir(parents=True, exist_ok=True)
        for path in files:
            shutil.move(str(path), str(archive_dir / path.name))
        print(f"Archived {len(files)} calibration images to: {archive_dir}")
    else:
        for path in files:
            path.unlink()
        print(f"Deleted {len(files)} calibration images from: {input_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
