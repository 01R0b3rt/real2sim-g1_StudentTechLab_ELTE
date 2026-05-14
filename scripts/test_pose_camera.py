from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import DEFAULT_CONFIG, load_yaml, parse_camera_source, resolve_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Open a camera/video and draw MediaPipe Pose landmarks.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config.")
    parser.add_argument("--camera", default=None, help="OpenCV camera index.")
    parser.add_argument("--video", default=None, help="Optional video input.")
    parser.add_argument("--confidence", type=float, default=None, help="Visibility threshold.")
    parser.add_argument("--max-frames", type=int, default=0, help="Optional frame limit.")
    args = parser.parse_args()

    estimator = None
    try:
        from src.camera_pose import CameraPoseEstimator

        config = load_yaml(args.config)
        camera_cfg = dict(config.get("camera", {}) or {})
        retargeting_cfg = dict(config.get("retargeting", {}) or {})
        source = (
            str(resolve_path(args.video))
            if args.video
            else parse_camera_source(args.camera if args.camera is not None else camera_cfg.get("source", 0))
        )
        confidence = float(args.confidence or retargeting_cfg.get("confidence_threshold", 0.5))

        estimator = CameraPoseEstimator(
            source=source,
            width=int(camera_cfg.get("width", 0) or 0) or None,
            height=int(camera_cfg.get("height", 0) or 0) or None,
            min_detection_confidence=confidence,
            min_tracking_confidence=confidence,
        )

        frame_count = 0
        print("Pose camera test running. Press ESC/q to quit.")
        while True:
            frame = estimator.read_frame()
            if frame is None:
                print("No more frames from source.")
                break
            landmarks, debug_frame = estimator.detect_pose(frame)
            upper = estimator.extract_upper_body_landmarks(landmarks, confidence)
            if upper is None:
                estimator.annotate_status(debug_frame, "no reliable upper-body pose")
            else:
                estimator.annotate_status(debug_frame, f"upper body visible | min visibility {upper.min_visibility:.2f}")

            estimator.cv2.imshow("test_pose_camera", debug_frame)
            key = estimator.cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_count += 1
            if args.max_frames and frame_count >= args.max_frames:
                break
    except (FileNotFoundError, RuntimeError, ImportError) as exc:
        print(exc)
        return 2
    finally:
        if estimator is not None:
            estimator.close()
            estimator.cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
