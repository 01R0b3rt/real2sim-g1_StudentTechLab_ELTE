from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.camera_pose import (
    FULL_BODY_LANDMARKS,
    HumanUpperBodyPose,
    LOWER_BODY_LANDMARKS,
    REQUIRED_LANDMARKS,
    CameraPoseEstimator,
)
from src.utils import load_yaml, resolve_path

try:
    import numpy as np
except ImportError as exc:
    from src.utils import print_dependency_help

    print_dependency_help("numpy")
    raise exc


@dataclass
class StereoCalibration:
    left_camera_matrix: np.ndarray
    left_distortion: np.ndarray
    right_camera_matrix: np.ndarray
    right_distortion: np.ndarray
    rotation_left_to_right: np.ndarray
    translation_left_to_right: np.ndarray
    left_projection: np.ndarray
    right_projection: np.ndarray


class StereoPoseEstimator:
    """Triangulate MediaPipe upper-body landmarks from two calibrated cameras."""

    def __init__(
        self,
        calibration_path: str | Path,
        left_source: int = 0,
        right_source: int = 1,
        width: int | None = None,
        height: int | None = None,
        backend: str = "dshow",
        left_rotation: str = "none",
        right_rotation: str = "none",
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.calibration_path = resolve_path(calibration_path)
        self.calibration = self._load_calibration(self.calibration_path)
        self.left = None
        self.right = None
        try:
            self.left = CameraPoseEstimator(
                source=left_source,
                width=width,
                height=height,
                backend=backend,
                rotation=left_rotation,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self.right = CameraPoseEstimator(
                source=right_source,
                width=width,
                height=height,
                backend=backend,
                rotation=right_rotation,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        except Exception:
            if self.left is not None:
                self.left.close()
            if self.right is not None:
                self.right.close()
            raise
        self.cv2 = self.left.cv2
        self.capture = self.left.capture
        self.previous_lower_points_3d: dict[str, np.ndarray] = {}
        self.previous_lower_visibility: dict[str, float] = {}

    def _load_calibration(self, path: Path) -> StereoCalibration:
        config = load_yaml(path)
        left_k = np.asarray(config["left"]["camera_matrix"], dtype=np.float64)
        left_d = np.asarray(config["left"]["distortion"], dtype=np.float64).reshape(-1, 1)
        right_k = np.asarray(config["right"]["camera_matrix"], dtype=np.float64)
        right_d = np.asarray(config["right"]["distortion"], dtype=np.float64).reshape(-1, 1)
        rotation = np.asarray(config["stereo"]["rotation_left_to_right"], dtype=np.float64)
        translation = np.asarray(config["stereo"]["translation_left_to_right_m"], dtype=np.float64).reshape(3, 1)

        left_projection = left_k @ np.hstack([np.eye(3), np.zeros((3, 1))])
        right_projection = right_k @ np.hstack([rotation, translation])
        return StereoCalibration(
            left_camera_matrix=left_k,
            left_distortion=left_d,
            right_camera_matrix=right_k,
            right_distortion=right_d,
            rotation_left_to_right=rotation,
            translation_left_to_right=translation,
            left_projection=left_projection,
            right_projection=right_projection,
        )

    def read_frames(self) -> tuple[Any, Any] | None:
        frame_l = self.left.read_frame()
        frame_r = self.right.read_frame()
        if frame_l is None or frame_r is None:
            return None
        return frame_l, frame_r

    def estimate_pose(
        self,
        frames: tuple[Any, Any],
        confidence_threshold: float = 0.5,
        include_lower_body: bool = False,
        lower_body_confidence_threshold: float | None = None,
    ) -> tuple[HumanUpperBodyPose | None, Any]:
        frame_l, frame_r = frames
        landmarks_l, debug_l = self.left.detect_pose(frame_l)
        landmarks_r, debug_r = self.right.detect_pose(frame_r)
        debug_frame = self._combine_debug_frames(debug_l, debug_r)

        if landmarks_l is None or landmarks_r is None:
            return None, debug_frame

        pose_l = self._extract_pixel_landmarks(
            self.left,
            landmarks_l,
            frame_l,
            confidence_threshold,
            include_lower_body=include_lower_body,
            lower_body_confidence_threshold=lower_body_confidence_threshold,
        )
        pose_r = self._extract_pixel_landmarks(
            self.right,
            landmarks_r,
            frame_r,
            confidence_threshold,
            include_lower_body=include_lower_body,
            lower_body_confidence_threshold=lower_body_confidence_threshold,
        )
        if pose_l is None or pose_r is None:
            return None, debug_frame

        points_3d: dict[str, np.ndarray] = {}
        visibility: dict[str, float] = {}
        for name in REQUIRED_LANDMARKS:
            point = self._triangulate_point(pose_l[name], pose_r[name])
            if point is None:
                return None, debug_frame
            points_3d[name] = point
            visibility[name] = min(pose_l[f"{name}_visibility"], pose_r[f"{name}_visibility"])

        if include_lower_body:
            for name in LOWER_BODY_LANDMARKS:
                point = None
                if name in pose_l and name in pose_r:
                    point = self._triangulate_point(pose_l[name], pose_r[name])
                if point is not None:
                    points_3d[name] = point
                    visibility[name] = min(pose_l[f"{name}_visibility"], pose_r[f"{name}_visibility"])
                    self.previous_lower_points_3d[name] = point
                    self.previous_lower_visibility[name] = visibility[name]
                elif name in self.previous_lower_points_3d:
                    # Lower-body landmarks blink out frequently with two webcams.
                    # Reusing the last good knee/ankle keeps the robot from freezing;
                    # the retargeter can still rely on pelvis drop for squat motion.
                    points_3d[name] = self.previous_lower_points_3d[name].copy()
                    visibility[name] = self.previous_lower_visibility.get(name, 0.0)

        self._draw_depth_overlay(debug_frame, points_3d)
        return HumanUpperBodyPose(points=points_3d, visibility=visibility), debug_frame

    def _extract_pixel_landmarks(
        self,
        estimator: CameraPoseEstimator,
        landmarks: Any,
        frame: Any,
        confidence_threshold: float,
        include_lower_body: bool = False,
        lower_body_confidence_threshold: float | None = None,
    ) -> dict[str, np.ndarray | float] | None:
        pose_enum = estimator.mp_pose.PoseLandmark
        mapping = {
            "left_shoulder": pose_enum.LEFT_SHOULDER,
            "left_elbow": pose_enum.LEFT_ELBOW,
            "left_wrist": pose_enum.LEFT_WRIST,
            "right_shoulder": pose_enum.RIGHT_SHOULDER,
            "right_elbow": pose_enum.RIGHT_ELBOW,
            "right_wrist": pose_enum.RIGHT_WRIST,
            "left_hip": pose_enum.LEFT_HIP,
            "right_hip": pose_enum.RIGHT_HIP,
            "left_knee": pose_enum.LEFT_KNEE,
            "left_ankle": pose_enum.LEFT_ANKLE,
            "right_knee": pose_enum.RIGHT_KNEE,
            "right_ankle": pose_enum.RIGHT_ANKLE,
        }
        lower_threshold = (
            min(confidence_threshold, 0.25)
            if lower_body_confidence_threshold is None
            else lower_body_confidence_threshold
        )
        height, width = frame.shape[:2]
        output: dict[str, np.ndarray | float] = {}
        for name in REQUIRED_LANDMARKS:
            enum_value = mapping[name]
            landmark = landmarks[int(enum_value)]
            visibility = float(getattr(landmark, "visibility", 0.0))
            if visibility < confidence_threshold:
                return None
            output[name] = np.array(
                [float(landmark.x) * width, float(landmark.y) * height],
                dtype=np.float64,
            )
            output[f"{name}_visibility"] = visibility
        if include_lower_body:
            for name in LOWER_BODY_LANDMARKS:
                enum_value = mapping[name]
                landmark = landmarks[int(enum_value)]
                visibility = float(getattr(landmark, "visibility", 0.0))
                output[f"{name}_visibility"] = visibility
                if visibility < lower_threshold:
                    continue
                output[name] = np.array(
                    [float(landmark.x) * width, float(landmark.y) * height],
                    dtype=np.float64,
                )
        return output

    def _triangulate_point(self, left_pixel: np.ndarray, right_pixel: np.ndarray) -> np.ndarray | None:
        cv2 = self.cv2
        cal = self.calibration
        left = np.asarray(left_pixel, dtype=np.float64).reshape(1, 1, 2)
        right = np.asarray(right_pixel, dtype=np.float64).reshape(1, 1, 2)

        left_undistorted = cv2.undistortPoints(
            left,
            cal.left_camera_matrix,
            cal.left_distortion,
            P=cal.left_camera_matrix,
        ).reshape(2, 1)
        right_undistorted = cv2.undistortPoints(
            right,
            cal.right_camera_matrix,
            cal.right_distortion,
            P=cal.right_camera_matrix,
        ).reshape(2, 1)

        homogeneous = cv2.triangulatePoints(
            cal.left_projection,
            cal.right_projection,
            left_undistorted,
            right_undistorted,
        )
        w = float(homogeneous[3, 0])
        if abs(w) < 1e-9:
            return None
        point = (homogeneous[:3, 0] / w).astype(np.float64)
        if not np.all(np.isfinite(point)):
            return None
        return point

    def _combine_debug_frames(self, left_frame: Any, right_frame: Any) -> Any:
        height = min(left_frame.shape[0], right_frame.shape[0])
        if left_frame.shape[0] != height:
            left_frame = self.cv2.resize(
                left_frame,
                (int(left_frame.shape[1] * height / left_frame.shape[0]), height),
            )
        if right_frame.shape[0] != height:
            right_frame = self.cv2.resize(
                right_frame,
                (int(right_frame.shape[1] * height / right_frame.shape[0]), height),
            )
        return np.hstack([left_frame, right_frame])

    def _draw_depth_overlay(self, frame: Any, points_3d: dict[str, np.ndarray]) -> None:
        left_wrist = points_3d.get("left_wrist")
        right_wrist = points_3d.get("right_wrist")
        if left_wrist is None or right_wrist is None:
            return
        text = f"3D wrists z: L={left_wrist[2]:+.2f}m R={right_wrist[2]:+.2f}m"
        self.cv2.putText(
            frame,
            text,
            (24, frame.shape[0] - 24),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (40, 240, 40),
            2,
            self.cv2.LINE_AA,
        )

    def annotate_status(self, frame: Any, text: str) -> Any:
        return self.left.annotate_status(frame, text)

    def close(self) -> None:
        if self.left is not None:
            self.left.close()
        if self.right is not None:
            self.right.close()
