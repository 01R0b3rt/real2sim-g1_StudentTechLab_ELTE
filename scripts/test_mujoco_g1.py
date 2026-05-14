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


TARGET_NAMES = (
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_elbow",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_elbow",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Load G1 in MuJoCo and move both arms sinusoidally.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to YAML config.")
    parser.add_argument("--model-xml", default=None, help="Override G1 XML path.")
    parser.add_argument("--duration", type=float, default=20.0, help="Seconds to run.")
    parser.add_argument("--fps", type=float, default=60.0, help="Control loop rate.")
    parser.add_argument("--no-viewer", action="store_true", help="Run without MuJoCo viewer.")
    parser.add_argument("--advance-physics", action="store_true", help="Use mj_step physics instead of stable qpos visualization.")
    args = parser.parse_args()

    try:
        config = load_yaml(args.config)
        model_xml = resolve_path(args.model_xml or dict(config.get("model", {}) or {}).get("xml_path"))
        controller = MujocoG1Controller(
            model_xml_path=model_xml,
            joint_mapping=dict(config.get("joint_mapping", {}) or {}),
            use_viewer=not args.no_viewer,
            advance_physics=args.advance_physics,
        )
        controller.load_model()
        print("Loaded G1 model. Moving configured arm joints.")
        start = time.perf_counter()
        while time.perf_counter() - start < args.duration:
            t = time.perf_counter() - start
            targets = {name: 0.0 for name in TARGET_NAMES}
            targets["left_shoulder_pitch"] = 0.45 * math.sin(t)
            targets["right_shoulder_pitch"] = 0.45 * math.sin(t)
            targets["left_shoulder_roll"] = 0.35 * math.sin(0.8 * t)
            targets["right_shoulder_roll"] = -0.35 * math.sin(0.8 * t)
            targets["left_elbow"] = 0.8 + 0.45 * math.sin(1.2 * t)
            targets["right_elbow"] = 0.8 + 0.45 * math.sin(1.2 * t + math.pi)

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
