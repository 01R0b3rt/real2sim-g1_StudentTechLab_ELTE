from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import DEFAULT_CONFIG, PROJECT_ROOT, load_yaml, parse_camera_source, resolve_path


def _package_state(name: str) -> str:
    return "ok" if importlib.util.find_spec(name) is not None else "missing"


def _camera_state(source: int | str) -> str:
    if importlib.util.find_spec("cv2") is None:
        return "unknown (opencv-python missing)"
    import cv2

    capture = cv2.VideoCapture(source)
    try:
        return "ok" if capture.isOpened() else "unavailable"
    finally:
        capture.release()


def _run_app(extra_args: list[str]) -> int:
    command = [sys.executable, str(PROJECT_ROOT / "src" / "real2sim_app.py"), *extra_args]
    print("Running:", " ".join(command))
    return subprocess.run(command, cwd=str(PROJECT_ROOT), check=False).returncode


def command_status(args: argparse.Namespace) -> int:
    print("OpenClaw Real2Sim G1 tool status")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python: {sys.version.split()[0]}")

    for package in ("cv2", "mediapipe", "mujoco", "numpy", "yaml"):
        print(f"{package:10s}: {_package_state(package)}")

    config_path = resolve_path(args.config)
    print(f"Config:     {'ok' if config_path.exists() else 'missing'} ({config_path})")

    if config_path.exists() and importlib.util.find_spec("yaml") is not None:
        config = load_yaml(config_path)
        model_xml = resolve_path(dict(config.get("model", {}) or {}).get("xml_path"))
        source = parse_camera_source(dict(config.get("camera", {}) or {}).get("source", 0))
        print(f"G1 XML:     {'ok' if model_xml.exists() else 'missing'} ({model_xml})")
        print(f"Camera:     {_camera_state(source)} (source={source})")
    elif config_path.exists():
        print("G1 XML:     unknown (PyYAML missing; install requirements first)")
        print("Camera:     unknown (PyYAML missing; install requirements first)")
    else:
        print("G1 XML:     unknown (config missing)")
        print("Camera:     unknown (config missing)")

    return 0


def command_start(args: argparse.Namespace) -> int:
    extra = ["--config", args.config]
    if args.camera is not None:
        extra.extend(["--camera", args.camera])
    if args.video:
        extra.extend(["--video", args.video])
    if args.model_xml:
        extra.extend(["--model-xml", args.model_xml])
    _append_stereo_args(args, extra)
    return _run_app(extra)


def command_calibrate(args: argparse.Namespace) -> int:
    extra = ["--config", args.config, "--calibrate"]
    if args.camera is not None:
        extra.extend(["--camera", args.camera])
    if args.model_xml:
        extra.extend(["--model-xml", args.model_xml])
    _append_stereo_args(args, extra)
    return _run_app(extra)


def command_run_demo(args: argparse.Namespace) -> int:
    extra = ["--config", args.config]
    if args.camera is not None:
        extra.extend(["--camera", args.camera])
    if args.video:
        extra.extend(["--video", args.video])
    if args.model_xml:
        extra.extend(["--model-xml", args.model_xml])
    _append_stereo_args(args, extra)
    return _run_app(extra)


def command_record_demo(args: argparse.Namespace) -> int:
    extra = [
        "--config",
        args.config,
        "--record-output",
        args.output,
    ]
    if args.camera is not None:
        extra.extend(["--camera", args.camera])
    if args.video:
        extra.extend(["--video", args.video])
    if args.model_xml:
        extra.extend(["--model-xml", args.model_xml])
    if args.max_frames:
        extra.extend(["--max-frames", str(args.max_frames)])
    _append_stereo_args(args, extra)
    return _run_app(extra)


def _append_stereo_args(args: argparse.Namespace, extra: list[str]) -> None:
    if getattr(args, "stereo", False):
        extra.append("--stereo")
    if getattr(args, "full_body", False):
        extra.append("--full-body")
    if getattr(args, "locomotion_demo", False):
        extra.append("--locomotion-demo")
    if getattr(args, "stereo_config", None):
        extra.extend(["--stereo-config", args.stereo_config])
    if getattr(args, "left_camera", None) is not None:
        extra.extend(["--left-camera", str(args.left_camera)])
    if getattr(args, "right_camera", None) is not None:
        extra.extend(["--right-camera", str(args.right_camera)])
    if getattr(args, "camera_backend", None):
        extra.extend(["--camera-backend", args.camera_backend])
    if getattr(args, "camera_rotation", None):
        extra.extend(["--camera-rotation", args.camera_rotation])
    if getattr(args, "left_rotation", None):
        extra.extend(["--left-rotation", args.left_rotation])
    if getattr(args, "right_rotation", None):
        extra.extend(["--right-rotation", args.right_rotation])
    if getattr(args, "display_scale", None) is not None:
        extra.extend(["--display-scale", str(args.display_scale)])
    if getattr(args, "confidence", None) is not None:
        extra.extend(["--confidence", str(args.confidence)])
    if getattr(args, "lower_confidence", None) is not None:
        extra.extend(["--lower-confidence", str(args.lower_confidence)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenClaw-compatible command wrapper for the Real2Sim G1 MVP."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Print dependency, camera, config, and model status.")
    status.set_defaults(func=command_status)

    for name, func, help_text in (
        ("start", command_start, "Start webcam/video to MuJoCo imitation."),
        ("calibrate", command_calibrate, "Start and force neutral-pose calibration."),
        ("run-demo", command_run_demo, "Run the live demo pipeline."),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--config", default=argparse.SUPPRESS, help="Path to YAML config.")
        sub.add_argument("--camera", default=None, help="OpenCV camera index.")
        sub.add_argument("--video", default=None, help="Optional video input.")
        sub.add_argument("--model-xml", default=None, help="Override G1 XML path.")
        sub.add_argument("--stereo", action="store_true", help="Use calibrated stereo pose.")
        sub.add_argument("--full-body", action="store_true", help="Experimental waist/leg retargeting.")
        sub.add_argument("--locomotion-demo", action="store_true", help="Experimental root motion from pelvis movement.")
        sub.add_argument("--stereo-config", default=None, help="Stereo calibration YAML.")
        sub.add_argument("--left-camera", type=int, default=None, help="Left stereo camera index.")
        sub.add_argument("--right-camera", type=int, default=None, help="Right stereo camera index.")
        sub.add_argument("--camera-backend", default=None, choices=["auto", "dshow", "msmf"], help="OpenCV camera backend.")
        sub.add_argument("--camera-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate mono camera frames.")
        sub.add_argument("--left-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate left stereo camera frames.")
        sub.add_argument("--right-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate right stereo camera frames.")
        sub.add_argument("--display-scale", type=float, default=None, help="Scale OpenCV debug window.")
        sub.add_argument("--confidence", type=float, default=None, help="Upper-body visibility threshold.")
        sub.add_argument("--lower-confidence", type=float, default=None, help="Lower-body visibility threshold in full-body mode.")
        sub.set_defaults(func=func)

    record = subparsers.add_parser("record-demo", help="Run demo and save camera overlay video.")
    record.add_argument("--config", default=argparse.SUPPRESS, help="Path to YAML config.")
    record.add_argument("--camera", default=None, help="OpenCV camera index.")
    record.add_argument("--video", default=None, help="Optional video input.")
    record.add_argument("--model-xml", default=None, help="Override G1 XML path.")
    record.add_argument("--stereo", action="store_true", help="Use calibrated stereo pose.")
    record.add_argument("--full-body", action="store_true", help="Experimental waist/leg retargeting.")
    record.add_argument("--locomotion-demo", action="store_true", help="Experimental root motion from pelvis movement.")
    record.add_argument("--stereo-config", default=None, help="Stereo calibration YAML.")
    record.add_argument("--left-camera", type=int, default=None, help="Left stereo camera index.")
    record.add_argument("--right-camera", type=int, default=None, help="Right stereo camera index.")
    record.add_argument("--camera-backend", default=None, choices=["auto", "dshow", "msmf"], help="OpenCV camera backend.")
    record.add_argument("--camera-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate mono camera frames.")
    record.add_argument("--left-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate left stereo camera frames.")
    record.add_argument("--right-rotation", default=None, choices=["none", "cw", "ccw", "180"], help="Rotate right stereo camera frames.")
    record.add_argument("--display-scale", type=float, default=None, help="Scale OpenCV debug window.")
    record.add_argument("--confidence", type=float, default=None, help="Upper-body visibility threshold.")
    record.add_argument("--lower-confidence", type=float, default=None, help="Lower-body visibility threshold in full-body mode.")
    record.add_argument("--output", default="media/demo_output.mp4", help="Output MP4 path.")
    record.add_argument("--max-frames", type=int, default=0, help="Optional frame limit.")
    record.set_defaults(func=command_record_demo)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
