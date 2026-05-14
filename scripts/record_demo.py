from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a Real2Sim G1 demo camera-overlay video.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "g1_arm_mapping.yaml"))
    parser.add_argument("--camera", default=None)
    parser.add_argument("--video", default=None)
    parser.add_argument("--model-xml", default=None)
    parser.add_argument("--output", default="media/demo_output.mp4")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()

    command = [
        sys.executable,
        str(PROJECT_ROOT / "src" / "real2sim_app.py"),
        "--config",
        args.config,
        "--record-output",
        args.output,
    ]
    if args.camera is not None:
        command.extend(["--camera", args.camera])
    if args.video:
        command.extend(["--video", args.video])
    if args.model_xml:
        command.extend(["--model-xml", args.model_xml])
    if args.max_frames:
        command.extend(["--max-frames", str(args.max_frames)])

    print("Running:", " ".join(command))
    return subprocess.run(command, cwd=str(PROJECT_ROOT), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
