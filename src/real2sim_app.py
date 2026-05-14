from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import DEFAULT_CONFIG, load_yaml, parse_camera_source, resolve_path


def _camera_source_from_args(args: argparse.Namespace, config: dict[str, Any]) -> int | str:
    if args.video:
        return str(resolve_path(args.video))
    if args.camera is not None:
        return parse_camera_source(args.camera)
    camera_cfg = dict(config.get("camera", {}) or {})
    return parse_camera_source(camera_cfg.get("source", 0))


def _stereo_sources_from_args(args: argparse.Namespace, config: dict[str, Any]) -> tuple[int, int]:
    stereo_cfg = dict(config.get("stereo", {}) or {})
    left = args.left_camera if args.left_camera is not None else stereo_cfg.get("left_camera", 0)
    right = args.right_camera if args.right_camera is not None else stereo_cfg.get("right_camera", 1)
    return int(left), int(right)


def _model_xml_from_args(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    if args.model_xml:
        return resolve_path(args.model_xml)
    return resolve_path(dict(config.get("model", {}) or {}).get("xml_path"))


def _open_video_writer(estimator: Any, output_path: Path, frame: Any):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2 = estimator.cv2
    height, width = frame.shape[:2]
    fps = estimator.capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1:
        fps = 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, float(fps), (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create demo video writer: {output_path}")
    return writer


def _scaled_for_display(cv2: Any, frame: Any, scale: float) -> Any:
    if scale <= 0 or abs(scale - 1.0) < 1e-6:
        return frame
    height, width = frame.shape[:2]
    return cv2.resize(frame, (max(1, int(width * scale)), max(1, int(height * scale))))


def run_app(args: argparse.Namespace) -> int:
    pose_estimator: Any | None = None
    robot = None
    writer = None

    try:
        from src.camera_pose import CameraPoseEstimator
        from src.mujoco_g1 import MujocoG1Controller
        from src.retarget import ArmRetargeter
        from src.stereo_pose import StereoPoseEstimator

        config = load_yaml(args.config)
        camera_cfg = dict(config.get("camera", {}) or {})
        retargeting_cfg = dict(config.get("retargeting", {}) or {})
        stereo_cfg = dict(config.get("stereo", {}) or {})

        model_xml = _model_xml_from_args(args, config)
        source = _camera_source_from_args(args, config)
        confidence_threshold = float(args.confidence or retargeting_cfg.get("confidence_threshold", 0.5))
        lower_body_confidence_threshold = float(
            args.lower_confidence
            if args.lower_confidence is not None
            else retargeting_cfg.get("lower_body_confidence_threshold", min(confidence_threshold, 0.25))
        )

        robot = MujocoG1Controller(
            model_xml_path=model_xml,
            joint_mapping=dict(config.get("joint_mapping", {}) or {}),
            use_viewer=not args.no_viewer,
            advance_physics=args.advance_physics,
        )
        robot.load_model()
        if args.debug_joints:
            robot.print_available_joints()

        if args.stereo:
            left_camera, right_camera = _stereo_sources_from_args(args, config)
            stereo_config = resolve_path(args.stereo_config or stereo_cfg.get("calibration_path", "configs/stereo_calibration.yaml"))
            pose_estimator = StereoPoseEstimator(
                calibration_path=stereo_config,
                left_source=left_camera,
                right_source=right_camera,
                width=int(camera_cfg.get("width", 0) or 0) or None,
                height=int(camera_cfg.get("height", 0) or 0) or None,
                backend=args.camera_backend or stereo_cfg.get("backend", "dshow"),
                left_rotation=args.left_rotation or stereo_cfg.get("left_rotation", "none"),
                right_rotation=args.right_rotation or stereo_cfg.get("right_rotation", "none"),
                min_detection_confidence=confidence_threshold,
                min_tracking_confidence=confidence_threshold,
            )
        else:
            pose_estimator = CameraPoseEstimator(
                source=source,
                width=int(camera_cfg.get("width", 0) or 0) or None,
                height=int(camera_cfg.get("height", 0) or 0) or None,
                backend=args.camera_backend or camera_cfg.get("backend", "auto"),
                rotation=args.camera_rotation,
                min_detection_confidence=confidence_threshold,
                min_tracking_confidence=confidence_threshold,
            )
        retargeter = ArmRetargeter(config)

        print("Real2Sim G1 app running.")
        print("Controls: ESC/q quits, c recalibrates neutral pose.")
        if args.stereo:
            print(f"Stereo camera sources: left={left_camera}, right={right_camera}")
            print(f"Stereo calibration: {stereo_config}")
        else:
            print(f"Camera/video source: {source}")
        print(f"MuJoCo XML: {model_xml}")

        frame_count = 0
        full_body_enabled = bool(args.full_body or args.locomotion_demo)
        calibration_pending = bool(args.calibrate)
        calibrated = False
        no_pose_seen = 0
        show_camera = not args.no_camera_window
        record_path = resolve_path(args.record_output) if args.record_output else None
        window_name = "real2sim-g1 camera pose"
        if show_camera:
            pose_estimator.cv2.namedWindow(window_name, pose_estimator.cv2.WINDOW_NORMAL)

        while True:
            if robot.viewer is not None and hasattr(robot.viewer, "is_running"):
                if not robot.viewer.is_running():
                    break

            if args.stereo:
                frames = pose_estimator.read_frames()
                if frames is None:
                    print("No more frames from stereo camera source. Exiting cleanly.")
                    break
                human_pose, debug_frame = pose_estimator.estimate_pose(
                    frames,
                    confidence_threshold=confidence_threshold,
                    include_lower_body=full_body_enabled,
                    lower_body_confidence_threshold=lower_body_confidence_threshold,
                )
            else:
                frame = pose_estimator.read_frame()
                if frame is None:
                    print("No more frames from camera/video source. Exiting cleanly.")
                    break
                landmarks, debug_frame = pose_estimator.detect_pose(frame)
                human_pose = pose_estimator.extract_body_landmarks(
                    landmarks,
                    confidence_threshold=confidence_threshold,
                    include_lower_body=full_body_enabled,
                    lower_body_confidence_threshold=lower_body_confidence_threshold,
                )

            if human_pose is not None:
                if calibration_pending or (not calibrated and retargeter.use_neutral_calibration):
                    retargeter.set_neutral_pose(
                        human_pose,
                        include_lower_body=full_body_enabled,
                        include_locomotion=args.locomotion_demo,
                    )
                    calibrated = True
                    calibration_pending = False
                    print("Neutral arm pose calibrated from current human pose.")

                targets = retargeter.human_pose_to_robot_targets(
                    human_pose,
                    include_lower_body=full_body_enabled,
                    include_locomotion=args.locomotion_demo,
                )
                robot.apply_arm_targets(targets)
                no_pose_seen = 0
                if args.stereo and args.locomotion_demo:
                    mode = "locomotion stereo 3D"
                elif args.stereo and full_body_enabled:
                    mode = "full-body stereo 3D"
                elif args.stereo:
                    mode = "stereo 3D"
                elif full_body_enabled:
                    mode = "full-body mono"
                else:
                    mode = "mono"
                debug_text = f"tracking arms ({mode}) | visibility {human_pose.min_visibility:.2f}"
            else:
                no_pose_seen += 1
                robot.hold_previous_pose()
                debug_text = f"no reliable upper-body pose | holding target ({no_pose_seen})"

            robot.step_simulation()
            robot.render()

            pose_estimator.annotate_status(debug_frame, debug_text)

            if record_path is not None:
                if writer is None:
                    writer = _open_video_writer(pose_estimator, record_path, debug_frame)
                    print(f"Recording camera overlay to: {record_path}")
                writer.write(debug_frame)

            if show_camera:
                try:
                    display_frame = _scaled_for_display(pose_estimator.cv2, debug_frame, args.display_scale)
                    pose_estimator.cv2.imshow(window_name, display_frame)
                    key = pose_estimator.cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q")):
                        break
                    if key == ord("c"):
                        calibration_pending = True
                        print("Calibration requested. Hold a neutral pose in view.")
                except Exception as exc:
                    print(f"Camera debug window disabled: {exc}")
                    show_camera = False

            frame_count += 1
            if args.max_frames and frame_count >= args.max_frames:
                break

            if args.no_viewer:
                time.sleep(max(0.0, 1.0 / float(args.headless_fps)))

    except FileNotFoundError as exc:
        print(exc)
        return 2
    except RuntimeError as exc:
        print(exc)
        return 3
    except ImportError as exc:
        print(f"Missing dependency: {exc}")
        return 4
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    finally:
        if writer is not None:
            writer.release()
        if pose_estimator is not None:
            pose_estimator.close()
            try:
                pose_estimator.cv2.destroyAllWindows()
            except Exception:
                pass
        if robot is not None:
            robot.close()

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run webcam/video to Unitree G1 MuJoCo arm imitation.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config.")
    parser.add_argument("--camera", default=None, help="OpenCV camera index, for example 0.")
    parser.add_argument("--camera-backend", default=None, choices=["auto", "dshow", "msmf"], help="OpenCV camera backend.")
    parser.add_argument("--camera-rotation", default="none", choices=["none", "cw", "ccw", "180"], help="Rotate mono camera frames.")
    parser.add_argument("--video", default=None, help="Optional video file input instead of a webcam.")
    parser.add_argument("--stereo", action="store_true", help="Use calibrated two-camera 3D pose triangulation.")
    parser.add_argument("--full-body", action="store_true", help="Experimental: also retarget waist, hips, and knees.")
    parser.add_argument("--locomotion-demo", action="store_true", help="Experimental: move G1 root from pelvis translation/yaw.")
    parser.add_argument("--stereo-config", default=None, help="Path to stereo calibration YAML.")
    parser.add_argument("--left-camera", type=int, default=None, help="Left stereo camera index.")
    parser.add_argument("--right-camera", type=int, default=None, help="Right stereo camera index.")
    parser.add_argument("--left-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate left stereo camera frames.")
    parser.add_argument("--right-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate right stereo camera frames.")
    parser.add_argument("--model-xml", default=None, help="Override Unitree G1 MuJoCo XML path.")
    parser.add_argument("--confidence", type=float, default=None, help="MediaPipe visibility threshold.")
    parser.add_argument("--lower-confidence", type=float, default=None, help="Lower-body visibility threshold in full-body mode.")
    parser.add_argument("--calibrate", action="store_true", help="Calibrate neutral pose from first valid frame.")
    parser.add_argument("--debug-joints", action="store_true", help="Print MuJoCo joints/actuators after loading.")
    parser.add_argument("--no-viewer", action="store_true", help="Run MuJoCo without opening the passive viewer.")
    parser.add_argument("--no-camera-window", action="store_true", help="Do not open the OpenCV debug window.")
    parser.add_argument("--display-scale", type=float, default=0.75, help="Scale OpenCV debug windows. Use 0.5 on one monitor.")
    parser.add_argument("--advance-physics", action="store_true", help="Use mj_step physics instead of stable qpos visualization.")
    parser.add_argument("--record-output", default=None, help="Record the camera pose overlay to an MP4 file.")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames. 0 means run until stopped.")
    parser.add_argument("--headless-fps", type=float, default=30.0, help="Sleep rate when --no-viewer is used.")
    return parser


def main() -> int:
    return run_app(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
