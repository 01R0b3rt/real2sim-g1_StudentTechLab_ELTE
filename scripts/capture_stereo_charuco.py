from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.camera_pose import rotate_frame
from src.utils import DEFAULT_CONFIG, load_yaml, resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture stereo image pairs for ChArUco calibration.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Project YAML config used for camera defaults.")
    parser.add_argument("--left-camera", type=int, default=None, help="Left/laptop camera index.")
    parser.add_argument("--right-camera", type=int, default=None, help="Right/USB camera index.")
    parser.add_argument("--output-dir", default="data/stereo_charuco", help="Directory for saved image pairs.")
    parser.add_argument("--backend", default=None, choices=["auto", "dshow", "msmf"], help="OpenCV camera backend.")
    parser.add_argument("--width", type=int, default=None, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=None, help="Requested capture height.")
    parser.add_argument("--left-rotation", default=None, choices=["none", "cw", "ccw", "180"])
    parser.add_argument("--right-rotation", default=None, choices=["none", "cw", "ccw", "180"])
    parser.add_argument("--squares-x", type=int, default=5, help="ChArUco board squares across.")
    parser.add_argument("--squares-y", type=int, default=7, help="ChArUco board squares down.")
    parser.add_argument("--dictionary", default="DICT_5X5_50", help="OpenCV aruco dictionary name.")
    parser.add_argument("--min-corners", type=int, default=8, help="Minimum ChArUco corners required per camera.")
    parser.add_argument("--display-scale", type=float, default=0.75, help="Scale the side-by-side preview window.")
    return apply_config_defaults(parser.parse_args())


def apply_config_defaults(args: argparse.Namespace) -> argparse.Namespace:
    config = load_yaml(resolve_path(args.config))
    camera_cfg = dict(config.get("camera", {}) or {})
    stereo_cfg = dict(config.get("stereo", {}) or {})

    args.left_camera = int(args.left_camera if args.left_camera is not None else stereo_cfg.get("left_camera", 0))
    args.right_camera = int(args.right_camera if args.right_camera is not None else stereo_cfg.get("right_camera", 1))
    args.width = int(args.width if args.width is not None else camera_cfg.get("width", 640))
    args.height = int(args.height if args.height is not None else camera_cfg.get("height", 480))
    args.backend = args.backend or stereo_cfg.get("backend", "dshow")
    args.left_rotation = args.left_rotation or stereo_cfg.get("left_rotation", "none")
    args.right_rotation = args.right_rotation or stereo_cfg.get("right_rotation", "none")
    return args


def make_board(cv2, args: argparse.Namespace):
    dictionary_id = getattr(cv2.aruco, args.dictionary)
    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    # Physical lengths are irrelevant for capture. Calibration asks for them.
    board = cv2.aruco.CharucoBoard(
        (args.squares_x, args.squares_y),
        1.0,
        0.7475,
        dictionary,
    )
    return board, dictionary


def open_camera(cv2, index: int, width: int, height: int, backend: str):
    backend_id = {
        "auto": cv2.CAP_ANY,
        "dshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
    }.get(backend, cv2.CAP_ANY)
    capture = cv2.VideoCapture(index, backend_id)
    if not capture.isOpened() and backend != "auto":
        capture = cv2.VideoCapture(index, cv2.CAP_ANY)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera {index}.")
    return capture


def detect_charuco(cv2, frame, board, dictionary):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    marker_corners, marker_ids, _ = detector.detectMarkers(gray)
    debug = frame.copy()

    charuco_corners = None
    charuco_ids = None
    count = 0
    if marker_ids is not None and len(marker_ids) > 0:
        cv2.aruco.drawDetectedMarkers(debug, marker_corners, marker_ids)
        count, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            marker_corners,
            marker_ids,
            gray,
            board,
        )
        if charuco_corners is not None and charuco_ids is not None and count > 0:
            cv2.aruco.drawDetectedCornersCharuco(debug, charuco_corners, charuco_ids)

    return int(count), debug


def next_index(output_dir: Path) -> int:
    existing = sorted(output_dir.glob("left_*.png"))
    if not existing:
        return 0
    last = existing[-1].stem.split("_")[-1]
    return int(last) + 1 if last.isdigit() else len(existing)


def main() -> int:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run pip install -r requirements.txt first.")
        return 2

    args = parse_args()
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    board, dictionary = make_board(cv2, args)

    try:
        left = open_camera(cv2, args.left_camera, args.width, args.height, args.backend)
        right = open_camera(cv2, args.right_camera, args.width, args.height, args.backend)
    except RuntimeError as exc:
        print(exc)
        return 1

    index = next_index(output_dir)
    print(f"Saving stereo pairs to: {output_dir}")
    print(
        "Camera setup: "
        f"left={args.left_camera} rot={args.left_rotation}, "
        f"right={args.right_camera} rot={args.right_rotation}, "
        f"{args.width}x{args.height}, backend={args.backend}"
    )
    print("Move the board around the shared view. Press SPACE to save a good pair, q/ESC to quit.")
    cv2.namedWindow("stereo charuco capture", cv2.WINDOW_NORMAL)

    try:
        while True:
            ok_l, frame_l = left.read()
            ok_r, frame_r = right.read()
            if not ok_l or frame_l is None or not ok_r or frame_r is None:
                print("Could not read both camera frames.")
                break
            frame_l = rotate_frame(cv2, frame_l, args.left_rotation)
            frame_r = rotate_frame(cv2, frame_r, args.right_rotation)

            count_l, debug_l = detect_charuco(cv2, frame_l, board, dictionary)
            count_r, debug_r = detect_charuco(cv2, frame_r, board, dictionary)
            good = count_l >= args.min_corners and count_r >= args.min_corners
            color = (0, 255, 0) if good else (0, 0, 255)
            status = "READY - SPACE saves" if good else "show board to both cameras"

            for title, count, debug in (
                (f"left cam {args.left_camera}", count_l, debug_l),
                (f"right cam {args.right_camera}", count_r, debug_r),
            ):
                cv2.putText(
                    debug,
                    f"{title} | charuco corners: {count}",
                    (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    color,
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    debug,
                    status,
                    (16, 64),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    color,
                    2,
                    cv2.LINE_AA,
                )

            height = min(debug_l.shape[0], debug_r.shape[0])
            if debug_l.shape[0] != height:
                debug_l = cv2.resize(debug_l, (int(debug_l.shape[1] * height / debug_l.shape[0]), height))
            if debug_r.shape[0] != height:
                debug_r = cv2.resize(debug_r, (int(debug_r.shape[1] * height / debug_r.shape[0]), height))
            canvas = np.hstack([debug_l, debug_r])
            if args.display_scale > 0 and abs(args.display_scale - 1.0) > 1e-6:
                h, w = canvas.shape[:2]
                canvas = cv2.resize(
                    canvas,
                    (max(1, int(w * args.display_scale)), max(1, int(h * args.display_scale))),
                )
            cv2.imshow("stereo charuco capture", canvas)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord(" ") and good:
                left_path = output_dir / f"left_{index:03d}.png"
                right_path = output_dir / f"right_{index:03d}.png"
                cv2.imwrite(str(left_path), frame_l)
                cv2.imwrite(str(right_path), frame_r)
                print(f"saved pair {index:03d}: left={count_l} right={count_r}")
                index += 1
    finally:
        left.release()
        right.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
