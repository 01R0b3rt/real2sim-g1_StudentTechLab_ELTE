from __future__ import annotations

from dataclasses import dataclass
from math import atan2, pi
from typing import Mapping

from src.camera_pose import HumanUpperBodyPose, LOWER_BODY_LANDMARKS
from src.utils import clamp, print_dependency_help

try:
    import numpy as np
except ImportError as exc:
    print_dependency_help("numpy")
    raise exc


ARM_TARGET_NAMES = (
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_elbow",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_elbow",
)

TORSO_TARGET_NAMES = (
    "waist_yaw",
    "waist_roll",
    "waist_pitch",
)

LEG_TARGET_NAMES = (
    "left_hip_pitch",
    "left_hip_roll",
    "left_knee",
    "right_hip_pitch",
    "right_hip_roll",
    "right_knee",
)

LOCOMOTION_TARGET_NAMES = (
    "base_x",
    "base_y",
    "base_z",
    "base_yaw",
)

TARGET_NAMES = ARM_TARGET_NAMES + TORSO_TARGET_NAMES + LEG_TARGET_NAMES + LOCOMOTION_TARGET_NAMES


@dataclass
class TorsoFrame:
    up: np.ndarray
    right: np.ndarray
    forward: np.ndarray


def _normalize(vector: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-8:
        if fallback is None:
            return np.zeros(3, dtype=np.float64)
        return fallback.astype(np.float64)
    return vector / norm


def _angle_between(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = _normalize(a)
    b_norm = _normalize(b)
    denom = float(np.linalg.norm(a_norm) * np.linalg.norm(b_norm))
    if denom < 1e-8:
        return pi
    cos_theta = float(np.clip(np.dot(a_norm, b_norm), -1.0, 1.0))
    return float(np.arccos(cos_theta))


class ArmRetargeter:
    """Approximate MediaPipe upper-body landmarks as six G1 arm targets."""

    def __init__(self, config: Mapping[str, object]) -> None:
        retargeting = dict(config.get("retargeting", {}) or {})
        self.alpha = float(retargeting.get("smoothing_alpha", 0.25))
        self.use_neutral_calibration = bool(retargeting.get("use_neutral_calibration", True))
        self.signs = {name: 1.0 for name in TARGET_NAMES}
        self.signs.update({k: float(v) for k, v in dict(retargeting.get("signs", {}) or {}).items()})
        self.scales = {name: 1.0 for name in TARGET_NAMES}
        self.scales.update({k: float(v) for k, v in dict(retargeting.get("scales", {}) or {}).items()})
        self.offsets = {name: 0.0 for name in TARGET_NAMES}
        self.offsets.update({k: float(v) for k, v in dict(retargeting.get("offsets", {}) or {}).items()})
        self.squat_assist = dict(retargeting.get("squat_assist", {}) or {})

        limits = dict(config.get("joint_limits", {}) or {})
        self.joint_limits: dict[str, tuple[float, float]] = {}
        for name in TARGET_NAMES:
            raw = limits.get(name, [-pi, pi])
            self.joint_limits[name] = (float(raw[0]), float(raw[1]))

        self.previous_targets = {name: 0.0 for name in TARGET_NAMES}
        self.neutral_offsets: dict[str, float] | None = None
        self.neutral_metrics: dict[str, float] | None = None

    def set_neutral_pose(
        self,
        human_pose: HumanUpperBodyPose,
        include_lower_body: bool = False,
        include_locomotion: bool = False,
    ) -> dict[str, float]:
        raw = self._compute_raw_targets(
            human_pose,
            include_lower_body=include_lower_body,
            include_locomotion=include_locomotion,
        )
        self.neutral_offsets = raw
        self.neutral_metrics = self._compute_body_metrics(human_pose)
        return raw

    def hold_previous_targets(self) -> dict[str, float]:
        return dict(self.previous_targets)

    def human_pose_to_robot_targets(
        self,
        human_pose: HumanUpperBodyPose,
        include_lower_body: bool = False,
        include_locomotion: bool = False,
    ) -> dict[str, float]:
        raw = self._compute_raw_targets(
            human_pose,
            include_lower_body=include_lower_body,
            include_locomotion=include_locomotion,
        )

        targets: dict[str, float] = {}
        for name in raw:
            value = raw[name]
            if self.use_neutral_calibration and self.neutral_offsets is not None:
                value -= self.neutral_offsets.get(name, 0.0)
            value = (
                self.signs.get(name, 1.0)
                * self.scales.get(name, 1.0)
                * value
                + self.offsets.get(name, 0.0)
            )
            low, high = self.joint_limits[name]
            targets[name] = clamp(value, low, high)

        if include_lower_body:
            targets = self._apply_squat_assist(human_pose, targets, include_locomotion)

        smoothed = self._smooth_targets(targets)
        self.previous_targets = smoothed
        return smoothed

    def _compute_raw_targets(
        self,
        human_pose: HumanUpperBodyPose,
        include_lower_body: bool = False,
        include_locomotion: bool = False,
    ) -> dict[str, float]:
        frame = self.compute_torso_frame(human_pose)
        left = self.compute_arm_targets(
            human_pose.points["left_shoulder"],
            human_pose.points["left_elbow"],
            human_pose.points["left_wrist"],
            frame,
            "left",
        )
        right = self.compute_arm_targets(
            human_pose.points["right_shoulder"],
            human_pose.points["right_elbow"],
            human_pose.points["right_wrist"],
            frame,
            "right",
        )
        targets = {**left, **right}
        if include_lower_body:
            targets.update(self.compute_torso_targets(human_pose))
            if self._has_lower_body(human_pose):
                targets.update(self.compute_leg_targets(human_pose, self.compute_leg_frame(human_pose)))
        if include_locomotion:
            targets.update(self.compute_locomotion_targets(human_pose))
        return targets

    def _has_lower_body(self, human_pose: HumanUpperBodyPose) -> bool:
        return all(name in human_pose.points for name in LOWER_BODY_LANDMARKS)

    def compute_torso_frame(self, human_pose: HumanUpperBodyPose) -> TorsoFrame:
        points = human_pose.points
        shoulder_center = 0.5 * (points["left_shoulder"] + points["right_shoulder"])
        hip_center = 0.5 * (points["left_hip"] + points["right_hip"])

        up = _normalize(shoulder_center - hip_center, np.array([0.0, -1.0, 0.0]))
        right = _normalize(
            points["right_shoulder"] - points["left_shoulder"],
            np.array([1.0, 0.0, 0.0]),
        )

        # MediaPipe uses image-normalized coordinates. This cross product gives
        # a person-local forward axis good enough for visible arm imitation.
        forward = _normalize(np.cross(right, up), np.array([0.0, 0.0, -1.0]))
        right = _normalize(np.cross(up, forward), right)
        return TorsoFrame(up=up, right=right, forward=forward)

    def compute_leg_frame(self, human_pose: HumanUpperBodyPose) -> TorsoFrame:
        points = human_pose.points
        right = _normalize(
            points["right_hip"] - points["left_hip"],
            np.array([1.0, 0.0, 0.0]),
        )
        # Legs are easier to read against camera/world vertical. If they are
        # tied to torso pitch, bending forward incorrectly swings the hips too.
        up = np.array([0.0, -1.0, 0.0], dtype=np.float64)
        forward = _normalize(np.cross(right, up), np.array([0.0, 0.0, -1.0]))
        right = _normalize(np.cross(up, forward), right)
        return TorsoFrame(up=up, right=right, forward=forward)

    def compute_arm_targets(
        self,
        shoulder: np.ndarray,
        elbow: np.ndarray,
        wrist: np.ndarray,
        torso_frame: TorsoFrame,
        side: str,
    ) -> dict[str, float]:
        upper_arm = elbow - shoulder
        forearm = wrist - elbow
        upper_unit = _normalize(upper_arm, -torso_frame.up)

        down_component = float(np.dot(upper_unit, -torso_frame.up))
        forward_component = float(np.dot(upper_unit, torso_frame.forward))
        side_component = float(np.dot(upper_unit, torso_frame.right))

        shoulder_pitch = atan2(forward_component, down_component)
        shoulder_roll = atan2(side_component, down_component)

        elbow_angle = _angle_between(-upper_arm, forearm)
        elbow_flexion = clamp(pi - elbow_angle, 0.0, pi)

        return {
            f"{side}_shoulder_pitch": float(shoulder_pitch),
            f"{side}_shoulder_roll": float(shoulder_roll),
            f"{side}_elbow": float(elbow_flexion),
        }

    def compute_torso_targets(self, human_pose: HumanUpperBodyPose) -> dict[str, float]:
        points = human_pose.points
        shoulder_center = 0.5 * (points["left_shoulder"] + points["right_shoulder"])
        hip_center = 0.5 * (points["left_hip"] + points["right_hip"])
        torso = _normalize(shoulder_center - hip_center, np.array([0.0, -1.0, 0.0]))
        shoulder_axis = _normalize(
            points["right_shoulder"] - points["left_shoulder"],
            np.array([1.0, 0.0, 0.0]),
        )

        # Camera coordinates are approximately x=right, y=down, z=forward.
        # These are intentionally small, visual torso targets, not balance control.
        waist_roll = atan2(float(torso[0]), float(-torso[1]))
        waist_pitch = atan2(float(torso[2]), float(-torso[1]))
        waist_yaw = atan2(float(shoulder_axis[2]), float(shoulder_axis[0]))
        return {
            "waist_yaw": float(waist_yaw),
            "waist_roll": float(waist_roll),
            "waist_pitch": float(waist_pitch),
        }

    def compute_leg_targets(
        self,
        human_pose: HumanUpperBodyPose,
        torso_frame: TorsoFrame,
    ) -> dict[str, float]:
        points = human_pose.points
        targets: dict[str, float] = {}
        for side in ("left", "right"):
            hip = points[f"{side}_hip"]
            knee = points[f"{side}_knee"]
            ankle = points[f"{side}_ankle"]
            thigh = knee - hip
            shin = ankle - knee
            thigh_unit = _normalize(thigh, -torso_frame.up)

            down_component = float(np.dot(thigh_unit, -torso_frame.up))
            forward_component = float(np.dot(thigh_unit, torso_frame.forward))
            side_component = float(np.dot(thigh_unit, torso_frame.right))

            hip_pitch = atan2(forward_component, down_component)
            hip_roll = atan2(side_component, down_component)
            knee_angle = _angle_between(-thigh, shin)
            knee_flexion = clamp(pi - knee_angle, 0.0, pi)
            targets[f"{side}_hip_pitch"] = float(hip_pitch)
            targets[f"{side}_hip_roll"] = float(hip_roll)
            targets[f"{side}_knee"] = float(knee_flexion)
        return targets

    def compute_locomotion_targets(self, human_pose: HumanUpperBodyPose) -> dict[str, float]:
        points = human_pose.points
        pelvis = 0.5 * (points["left_hip"] + points["right_hip"])
        shoulder_axis = _normalize(
            points["right_shoulder"] - points["left_shoulder"],
            np.array([1.0, 0.0, 0.0]),
        )
        base_yaw = atan2(float(shoulder_axis[2]), float(shoulder_axis[0]))

        # Stereo coordinates are roughly x=right, y=down, z=forward from the
        # left camera. The MuJoCo controller interprets these as small relative
        # root offsets for a visual locomotion demo, not physical walking.
        return {
            "base_x": float(pelvis[2]),
            "base_y": float(pelvis[0]),
            "base_z": float(-pelvis[1]),
            "base_yaw": float(base_yaw),
        }

    def _compute_body_metrics(self, human_pose: HumanUpperBodyPose) -> dict[str, float]:
        points = human_pose.points
        pelvis = 0.5 * (points["left_hip"] + points["right_hip"])
        shoulder_center = 0.5 * (points["left_shoulder"] + points["right_shoulder"])
        torso_height = float(np.linalg.norm(shoulder_center - pelvis))
        return {
            "pelvis_y": float(pelvis[1]),
            "torso_height": max(torso_height, 1e-6),
        }

    def _apply_squat_assist(
        self,
        human_pose: HumanUpperBodyPose,
        targets: Mapping[str, float],
        include_locomotion: bool,
    ) -> dict[str, float]:
        if not bool(self.squat_assist.get("enabled", True)):
            return dict(targets)
        if self.neutral_metrics is None:
            return dict(targets)

        metrics = self._compute_body_metrics(human_pose)
        pelvis_drop = metrics["pelvis_y"] - self.neutral_metrics["pelvis_y"]
        min_drop = float(self.squat_assist.get("min_pelvis_drop", 0.04))
        full_drop = float(self.squat_assist.get("full_pelvis_drop", 0.35))
        if full_drop <= min_drop:
            full_drop = min_drop + 1e-6
        amount = clamp((pelvis_drop - min_drop) / (full_drop - min_drop), 0.0, 1.0)
        if amount <= 0.0:
            return dict(targets)

        adjusted = dict(targets)
        knee_add = float(self.squat_assist.get("knee_add", 0.75)) * amount
        hip_pitch_add = float(self.squat_assist.get("hip_pitch_add", -0.45)) * amount
        waist_pitch_add = float(self.squat_assist.get("waist_pitch_add", 0.05)) * amount
        base_z_add = float(self.squat_assist.get("base_z_add", -0.10)) * amount
        hip_roll_damping = clamp(float(self.squat_assist.get("hip_roll_damping", 0.0)), 0.0, 1.0)

        # The lower-body landmarks are noisier than arms. This visual assist makes
        # crouching obvious even when knee/ankle MediaPipe landmarks wobble.
        for side in ("left", "right"):
            knee_name = f"{side}_knee"
            hip_name = f"{side}_hip_pitch"
            roll_name = f"{side}_hip_roll"
            low, high = self.joint_limits[knee_name]
            adjusted[knee_name] = clamp(
                adjusted.get(knee_name, 0.0) + knee_add,
                low,
                high,
            )
            low, high = self.joint_limits[hip_name]
            adjusted[hip_name] = clamp(
                adjusted.get(hip_name, 0.0) + hip_pitch_add,
                low,
                high,
            )
            if roll_name in adjusted and hip_roll_damping > 0.0:
                low, high = self.joint_limits[roll_name]
                adjusted[roll_name] = clamp(
                    adjusted[roll_name] * (1.0 - hip_roll_damping * amount),
                    low,
                    high,
                )

        if "waist_pitch" in adjusted:
            low, high = self.joint_limits["waist_pitch"]
            adjusted["waist_pitch"] = clamp(adjusted["waist_pitch"] + waist_pitch_add, low, high)
        if include_locomotion and "base_z" in adjusted:
            low, high = self.joint_limits["base_z"]
            adjusted["base_z"] = clamp(adjusted["base_z"] + base_z_add, low, high)
        return adjusted

    def _smooth_targets(self, new_targets: Mapping[str, float]) -> dict[str, float]:
        alpha = clamp(self.alpha, 0.0, 1.0)
        smoothed: dict[str, float] = {}
        for name in new_targets:
            previous = self.previous_targets.get(name, 0.0)
            value = float(new_targets.get(name, previous))
            low, high = self.joint_limits[name]
            smoothed[name] = clamp(alpha * value + (1.0 - alpha) * previous, low, high)
        for name in TARGET_NAMES:
            if name not in smoothed:
                smoothed[name] = self.previous_targets.get(name, 0.0)
        return smoothed
