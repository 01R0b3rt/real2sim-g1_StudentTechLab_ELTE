from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.camera_pose import rotate_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview multiple camera indices side by side.")
    parser.add_argument("--cameras", nargs="+", type=int, default=[0, 1, 2], help="Camera indices to preview.")
    parser.add_argument(
        "--backend",
        choices=["auto", "dshow", "msmf"],
        default="dshow",
        help="OpenCV backend. On Windows, dshow or msmf often fixes no-frame cameras.",
    )
    parser.add_argument("--width", type=int, default=640, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=480, help="Requested capture height.")
    parser.add_argument(
        "--rotate",
        nargs="*",
        default=[],
        help="Per-camera rotations, for example: --rotate 1:cw 0:none",
    )
    parser.add_argument("--tile-width", type=int, default=426, help="Display tile width.")
    parser.add_argument("--tile-height", type=int, default=320, help="Display tile height.")
    return parser.parse_args()


def backend_id(cv2, backend: str) -> int:
    if backend == "dshow":
        return cv2.CAP_DSHOW
    if backend == "msmf":
        return cv2.CAP_MSMF
    return cv2.CAP_ANY


def main() -> int:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run pip install -r requirements.txt first.")
        return 2

    args = parse_args()
    rotations: dict[int, str] = {}
    for item in args.rotate:
        try:
            camera_text, rotation = item.split(":", 1)
            rotations[int(camera_text)] = rotation
        except ValueError:
            print(f"Ignoring invalid rotation spec '{item}'. Use camera:rotation, for example 1:cw.")
    captures: list[tuple[int, object]] = []
    backend = backend_id(cv2, args.backend)

    for camera_id in args.cameras:
        capture = cv2.VideoCapture(camera_id, backend)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        if capture.isOpened():
            got_frame = False
            for _ in range(10):
                got_frame, _ = capture.read()
                if got_frame:
                    break
            captures.append((camera_id, capture))
            state = "opened with frame" if got_frame else "opened but no frame yet"
            print(f"Camera {camera_id}: {state}")
        else:
            capture.release()
            print(f"Camera {camera_id}: unavailable")

    if not captures:
        print("No cameras opened. Check USB connection or camera permissions.")
        return 1

    print("Press q or ESC to quit.")
    try:
        while True:
            tiles = []
            for camera_id, capture in captures:
                ok, frame = capture.read()
                if not ok or frame is None:
                    frame = np.zeros((args.tile_height, args.tile_width, 3), dtype=np.uint8)
                    label = f"camera {camera_id}: no frame"
                else:
                    frame = rotate_frame(cv2, frame, rotations.get(camera_id, "none"))
                    frame = cv2.resize(frame, (args.tile_width, args.tile_height))
                    label = f"camera {camera_id}"

                cv2.putText(
                    frame,
                    label,
                    (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                tiles.append(frame)

            canvas = np.hstack(tiles)
            cv2.imshow("camera preview", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        for _, capture in captures:
            capture.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
