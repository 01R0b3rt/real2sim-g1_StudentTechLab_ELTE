from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.mujoco_g1 import MujocoG1Controller
from src.utils import DEFAULT_CONFIG, load_yaml, resolve_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Print joints and actuators from a Unitree G1 MuJoCo XML.")
    parser.add_argument(
        "--model",
        default=str(DEFAULT_CONFIG),
        help="YAML config path, kept as --model to match the competition command.",
    )
    parser.add_argument("--model-xml", default=None, help="Direct XML path override.")
    args = parser.parse_args()

    try:
        config = load_yaml(args.model)
        model_xml = resolve_path(args.model_xml or dict(config.get("model", {}) or {}).get("xml_path"))
        controller = MujocoG1Controller(
            model_xml_path=model_xml,
            joint_mapping=dict(config.get("joint_mapping", {}) or {}),
            use_viewer=False,
        )
        controller.load_model()
        controller.print_available_joints()
        controller.close()
    except (FileNotFoundError, RuntimeError, ImportError) as exc:
        print(exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
