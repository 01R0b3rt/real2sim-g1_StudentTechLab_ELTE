from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.mujoco_g1 import MujocoG1Controller
from src.utils import DEFAULT_CONFIG, load_yaml, resolve_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Load G1 and move torso, hips, knees, and arms gently.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config.")
    parser.add_argument("--model-xml", default=None, help="Override G1 XML path.")
    parser.add_argument("--duration", type=float, default=20.0, help="Seconds to run.")
    parser.add_argument("--fps", type=float, default=60.0, help="Control loop rate.")
    parser.add_argument("--no-viewer", action="store_true", help="Run without MuJoCo viewer.")
    args = parser.parse_args()

    try:
        config = load_yaml(args.config)
        model_xml = resolve_path(args.model_xml or dict(config.get("model", {}) or {}).get("xml_path"))
        controller = MujocoG1Controller(
            model_xml_path=model_xml,
            joint_mapping=dict(config.get("joint_mapping", {}) or {}),
            use_viewer=not args.no_viewer,
        )
        controller.load_model()
        print("Loaded G1 model. Moving experimental full-body mapped joints.")
        start = time.perf_counter()
        while time.perf_counter() - start < args.duration:
            t = time.perf_counter() - start
            targets = {
                "waist_yaw": 0.25 * math.sin(0.5 * t),
                "waist_roll": 0.15 * math.sin(0.7 * t),
                "waist_pitch": 0.12 * math.sin(0.6 * t),
                "left_hip_pitch": 0.25 * math.sin(0.8 * t),
                "right_hip_pitch": 0.25 * math.sin(0.8 * t + math.pi),
                "left_hip_roll": 0.15 * math.sin(0.6 * t),
                "right_hip_roll": -0.15 * math.sin(0.6 * t),
                "left_knee": 0.35 + 0.25 * math.sin(0.9 * t),
                "right_knee": 0.35 + 0.25 * math.sin(0.9 * t + math.pi),
                "base_x": 0.15 * math.sin(0.35 * t),
                "base_y": 0.10 * math.sin(0.5 * t),
                "base_z": 0.04 * math.sin(0.9 * t),
                "base_yaw": 0.35 * math.sin(0.4 * t),
                "left_shoulder_pitch": 0.15 * math.sin(t),
                "right_shoulder_pitch": 0.15 * math.sin(t),
                "left_elbow": 1.3 + 0.25 * math.sin(1.1 * t),
                "right_elbow": 1.3 + 0.25 * math.sin(1.1 * t + math.pi),
            }
            controller.apply_arm_targets(targets)
            controller.step_simulation()
            controller.render()
            if controller.viewer is not None and hasattr(controller.viewer, "is_running"):
                if not controller.viewer.is_running():
                    break
            time.sleep(max(0.0, 1.0 / args.fps))
        controller.close()
    except (FileNotFoundError, RuntimeError, ImportError) as exc:
        print(exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
