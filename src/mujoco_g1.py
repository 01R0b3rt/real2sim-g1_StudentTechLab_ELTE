from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from pathlib import Path
from typing import Mapping

from src.utils import print_dependency_help, resolve_path


class MujocoModelError(RuntimeError):
    """Raised when the MuJoCo model cannot be loaded or addressed."""


@dataclass
class JointInfo:
    index: int
    name: str
    qpos_addr: int
    joint_type: int


class MujocoG1Controller:
    """Small MuJoCo wrapper for direct G1 arm qpos targets."""

    def __init__(
        self,
        model_xml_path: str | Path,
        joint_mapping: Mapping[str, str],
        use_viewer: bool = True,
        advance_physics: bool = False,
    ) -> None:
        self.model_xml_path = resolve_path(model_xml_path)
        self.joint_mapping = dict(joint_mapping)
        self.use_viewer = use_viewer
        self.advance_physics = advance_physics
        self.model = None
        self.data = None
        self.viewer = None
        self.mujoco = None
        self.joint_name_to_qpos_index: dict[str, int] = {}
        self.base_qpos_index: int | None = None
        self.base_qpos0 = None
        self._warned_missing_joints: set[str] = set()
        self.last_targets: dict[str, float] = {}

    def load_model(self) -> None:
        try:
            import mujoco
        except ImportError as exc:
            print_dependency_help("mujoco")
            raise exc

        if not self.model_xml_path.exists():
            raise FileNotFoundError(
                "MuJoCo XML not found: "
                f"{self.model_xml_path}\n"
                "Download the Unitree MuJoCo repository and update "
                "configs/g1_arm_mapping.yaml:model.xml_path or pass --model-xml."
            )

        self.mujoco = mujoco
        try:
            self.model = mujoco.MjModel.from_xml_path(str(self.model_xml_path))
            self.data = mujoco.MjData(self.model)
        except Exception as exc:  # MuJoCo raises several model parse exceptions.
            raise MujocoModelError(f"Failed to load MuJoCo XML '{self.model_xml_path}': {exc}") from exc

        self.joint_name_to_qpos_index = self._build_joint_qpos_index_map()
        self.base_qpos_index = self.joint_name_to_qpos_index.get("floating_base_joint")
        self.base_qpos0 = self.data.qpos[:7].copy() if self.base_qpos_index == 0 else None

        if self.use_viewer:
            try:
                import mujoco.viewer

                self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
            except Exception as exc:
                raise MujocoModelError(
                    "MuJoCo model loaded, but the passive viewer could not start. "
                    "Try running with --no-viewer for a headless validation, or check "
                    f"your display/OpenGL setup. Original error: {exc}"
                ) from exc

    def _build_joint_qpos_index_map(self) -> dict[str, int]:
        assert self.model is not None
        assert self.mujoco is not None
        mapping: dict[str, int] = {}
        for joint_id in range(self.model.njnt):
            name = self.mujoco.mj_id2name(
                self.model,
                self.mujoco.mjtObj.mjOBJ_JOINT,
                joint_id,
            )
            if name:
                mapping[name] = int(self.model.jnt_qposadr[joint_id])
        return mapping

    def print_available_joints(self) -> None:
        if self.model is None or self.mujoco is None:
            self.load_model()
        assert self.model is not None
        assert self.mujoco is not None

        print("Joints:")
        for joint_id in range(self.model.njnt):
            name = self.mujoco.mj_id2name(
                self.model,
                self.mujoco.mjtObj.mjOBJ_JOINT,
                joint_id,
            )
            qpos_addr = int(self.model.jnt_qposadr[joint_id])
            joint_type = int(self.model.jnt_type[joint_id])
            print(f"  {joint_id:3d}  qpos[{qpos_addr:3d}]  type={joint_type}  {name}")

        print("\nActuators:")
        for actuator_id in range(self.model.nu):
            name = self.mujoco.mj_id2name(
                self.model,
                self.mujoco.mjtObj.mjOBJ_ACTUATOR,
                actuator_id,
            )
            print(f"  {actuator_id:3d}  {name}")

    def available_joint_names(self) -> list[str]:
        if not self.joint_name_to_qpos_index:
            self.load_model()
        return sorted(self.joint_name_to_qpos_index)

    def apply_arm_targets(self, target_joint_angles: Mapping[str, float]) -> None:
        if self.model is None or self.data is None or self.mujoco is None:
            raise MujocoModelError("Call load_model() before applying targets.")

        self.last_targets = dict(target_joint_angles)
        self._apply_base_targets(target_joint_angles)
        for target_name, angle in target_joint_angles.items():
            if target_name.startswith("base_"):
                continue
            mujoco_joint_name = self.joint_mapping.get(target_name)
            if not mujoco_joint_name:
                continue
            qpos_index = self.joint_name_to_qpos_index.get(mujoco_joint_name)
            if qpos_index is None:
                self._warn_missing_joint_once(target_name, mujoco_joint_name)
                continue
            self.data.qpos[qpos_index] = float(angle)
        self.mujoco.mj_forward(self.model, self.data)

    def _apply_base_targets(self, target_joint_angles: Mapping[str, float]) -> None:
        if not any(name in target_joint_angles for name in ("base_x", "base_y", "base_z", "base_yaw")):
            return
        if self.base_qpos_index is None or self.base_qpos0 is None:
            if "floating_base_joint" not in self._warned_missing_joints:
                self._warned_missing_joints.add("floating_base_joint")
                print("Warning: floating_base_joint not found; locomotion root targets are ignored.")
            return

        addr = self.base_qpos_index
        self.data.qpos[addr + 0] = float(self.base_qpos0[0]) + float(target_joint_angles.get("base_x", 0.0))
        self.data.qpos[addr + 1] = float(self.base_qpos0[1]) + float(target_joint_angles.get("base_y", 0.0))
        self.data.qpos[addr + 2] = float(self.base_qpos0[2]) + float(target_joint_angles.get("base_z", 0.0))

        yaw = float(target_joint_angles.get("base_yaw", 0.0))
        half = 0.5 * yaw
        # MuJoCo free-joint quaternion order is w, x, y, z.
        self.data.qpos[addr + 3] = cos(half)
        self.data.qpos[addr + 4] = 0.0
        self.data.qpos[addr + 5] = 0.0
        self.data.qpos[addr + 6] = sin(half)

    def hold_previous_pose(self) -> None:
        if self.last_targets:
            self.apply_arm_targets(self.last_targets)

    def step_simulation(self) -> None:
        if self.model is None or self.data is None or self.mujoco is None:
            raise MujocoModelError("Call load_model() before stepping simulation.")
        if self.advance_physics:
            self.mujoco.mj_step(self.model, self.data)
        else:
            # The MVP directly writes arm qpos values. Advancing the full free-base
            # humanoid physics after teleporting joints can make the G1 fall or
            # generate huge accelerations. For visible imitation, keep this as a
            # stable kinematic visualization unless physics mode is requested.
            self.data.qvel[:] = 0.0
            self.data.qacc[:] = 0.0
            self.mujoco.mj_forward(self.model, self.data)

    def render(self) -> None:
        if self.viewer is not None:
            self.viewer.sync()

    def close(self) -> None:
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

    def _warn_missing_joint_once(self, target_name: str, mujoco_joint_name: str) -> None:
        key = f"{target_name}:{mujoco_joint_name}"
        if key in self._warned_missing_joints:
            return
        self._warned_missing_joints.add(key)
        print(
            f"Warning: target '{target_name}' maps to missing MuJoCo joint "
            f"'{mujoco_joint_name}'. Run scripts/print_g1_joints.py and update the YAML mapping."
        )
