from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.stereo_pose import StereoPoseEstimator


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview triangulated 3D upper-body pose from two cameras.")
    parser.add_argument("--stereo-config", default="configs/stereo_calibration.yaml")
    parser.add_argument("--left-camera", type=int, default=0)
    parser.add_argument("--right-camera", type=int, default=1)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--backend", default="dshow", choices=["auto", "dshow", "msmf"])
    parser.add_argument("--left-rotation", default="none", choices=["none", "cw", "ccw", "180"])
    parser.add_argument("--right-rotation", default="none", choices=["none", "cw", "ccw", "180"])
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--full-body", action="store_true", help="Require and triangulate knees/ankles too.")
    parser.add_argument("--display-scale", type=float, default=0.75)
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()

    estimator = None
    try:
        estimator = StereoPoseEstimator(
            calibration_path=args.stereo_config,
            left_source=args.left_camera,
            right_source=args.right_camera,
            width=args.width,
            height=args.height,
            backend=args.backend,
            left_rotation=args.left_rotation,
            right_rotation=args.right_rotation,
            min_detection_confidence=args.confidence,
            min_tracking_confidence=args.confidence,
        )
        print("Stereo pose test running. Press q/ESC to quit.")
        estimator.cv2.namedWindow("test_stereo_pose", estimator.cv2.WINDOW_NORMAL)
        frame_count = 0
        while True:
            frames = estimator.read_frames()
            if frames is None:
                print("Could not read both cameras.")
                break
            human_pose, debug_frame = estimator.estimate_pose(
                frames,
                args.confidence,
                include_lower_body=args.full_body,
            )
            if human_pose is None:
                estimator.annotate_status(debug_frame, "no reliable stereo upper-body pose")
            else:
                lw = human_pose.points["left_wrist"]
                rw = human_pose.points["right_wrist"]
                estimator.annotate_status(
                    debug_frame,
                    f"stereo 3D ok | L wrist {lw[0]:+.2f},{lw[1]:+.2f},{lw[2]:+.2f} m | "
                    f"R wrist {rw[0]:+.2f},{rw[1]:+.2f},{rw[2]:+.2f} m",
                )
            if args.display_scale > 0 and abs(args.display_scale - 1.0) > 1e-6:
                h, w = debug_frame.shape[:2]
                debug_frame = estimator.cv2.resize(
                    debug_frame,
                    (max(1, int(w * args.display_scale)), max(1, int(h * args.display_scale))),
                )
            estimator.cv2.imshow("test_stereo_pose", debug_frame)
            key = estimator.cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            frame_count += 1
            if args.max_frames and frame_count >= args.max_frames:
                break
    finally:
        if estimator is not None:
            estimator.close()
            estimator.cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
