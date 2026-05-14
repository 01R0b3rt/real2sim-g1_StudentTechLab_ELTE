from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils import parse_camera_source, print_dependency_help

try:
    import numpy as np
except ImportError as exc:
    print_dependency_help("numpy")
    raise exc


REQUIRED_LANDMARKS = (
    "left_shoulder",
    "left_elbow",
    "left_wrist",
    "right_shoulder",
    "right_elbow",
    "right_wrist",
    "left_hip",
    "right_hip",
)

LOWER_BODY_LANDMARKS = (
    "left_knee",
    "left_ankle",
    "right_knee",
    "right_ankle",
)

FULL_BODY_LANDMARKS = REQUIRED_LANDMARKS + LOWER_BODY_LANDMARKS


@dataclass
class HumanUpperBodyPose:
    points: dict[str, np.ndarray]
    visibility: dict[str, float]

    @property
    def min_visibility(self) -> float:
        return min(self.visibility.values()) if self.visibility else 0.0


class CameraPoseEstimator:
    """OpenCV + MediaPipe Pose wrapper for upper-body landmark extraction."""

    def __init__(
        self,
        source: int | str = 0,
        width: int | None = None,
        height: int | None = None,
        backend: str = "auto",
        rotation: str = "none",
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
    ) -> None:
        try:
            import cv2  # noqa: F401
        except ImportError as exc:
            print_dependency_help("opencv-python")
            raise exc

        try:
            import mediapipe as mp
        except ImportError as exc:
            print_dependency_help("mediapipe")
            raise exc

        self.cv2 = __import__("cv2")
        self.mp = mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.source = parse_camera_source(source)
        self.rotation = rotation
        self.capture = self._open_capture(self.source, backend)

        if width:
            self.capture.set(self.cv2.CAP_PROP_FRAME_WIDTH, int(width))
        if height:
            self.capture.set(self.cv2.CAP_PROP_FRAME_HEIGHT, int(height))

        if not self.capture.isOpened():
            raise RuntimeError(
                f"Could not open camera/video source '{self.source}'. "
                "Check the webcam permission, camera index, or video path."
            )

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def _open_capture(self, source: int | str, backend: str):
        if isinstance(source, str) and not source.isdigit():
            return self.cv2.VideoCapture(source)
        backend_id = {
            "auto": self.cv2.CAP_ANY,
            "dshow": self.cv2.CAP_DSHOW,
            "msmf": self.cv2.CAP_MSMF,
        }.get(backend, self.cv2.CAP_ANY)
        return self.cv2.VideoCapture(source, backend_id)

    def read_frame(self) -> Any | None:
        ok, frame = self.capture.read()
        if not ok:
            return None
        return rotate_frame(self.cv2, frame, self.rotation)

    def detect_pose(self, frame: Any) -> tuple[Any | None, Any]:
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self.pose.process(rgb)
        debug_frame = frame.copy()

        if not result.pose_landmarks:
            return None, debug_frame

        self.mp_drawing.draw_landmarks(
            debug_frame,
            result.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
        )
        return result.pose_landmarks.landmark, debug_frame

    def extract_upper_body_landmarks(
        self,
        landmarks: Any,
        confidence_threshold: float = 0.5,
    ) -> HumanUpperBodyPose | None:
        return self.extract_body_landmarks(
            landmarks,
            confidence_threshold=confidence_threshold,
            include_lower_body=False,
        )

    def extract_body_landmarks(
        self,
        landmarks: Any,
        confidence_threshold: float = 0.5,
        include_lower_body: bool = False,
        lower_body_confidence_threshold: float | None = None,
    ) -> HumanUpperBodyPose | None:
        if landmarks is None:
            return None

        pose_enum = self.mp_pose.PoseLandmark
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

        points: dict[str, np.ndarray] = {}
        visibility: dict[str, float] = {}
        for name in REQUIRED_LANDMARKS:
            enum_value = mapping[name]
            landmark = landmarks[int(enum_value)]
            vis = float(getattr(landmark, "visibility", 0.0))
            visibility[name] = vis
            if vis < confidence_threshold:
                return None
            points[name] = np.array(
                [float(landmark.x), float(landmark.y), float(landmark.z)],
                dtype=np.float64,
            )

        if include_lower_body:
            for name in LOWER_BODY_LANDMARKS:
                enum_value = mapping[name]
                landmark = landmarks[int(enum_value)]
                vis = float(getattr(landmark, "visibility", 0.0))
                visibility[name] = vis
                if vis < lower_threshold:
                    continue
                points[name] = np.array(
                    [float(landmark.x), float(landmark.y), float(landmark.z)],
                    dtype=np.float64,
                )

        return HumanUpperBodyPose(points=points, visibility=visibility)

    def annotate_status(self, frame: Any, text: str) -> Any:
        self.cv2.putText(
            frame,
            text,
            (24, 40),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (40, 240, 40),
            2,
            self.cv2.LINE_AA,
        )
        return frame

    def close(self) -> None:
        self.capture.release()
        self.pose.close()


def extract_upper_body_landmarks(
    estimator: CameraPoseEstimator,
    landmarks: Any,
    confidence_threshold: float,
) -> HumanUpperBodyPose | None:
    """Convenience function matching the task pseudocode wording."""
    return estimator.extract_upper_body_landmarks(landmarks, confidence_threshold)


def rotate_frame(cv2: Any, frame: Any, rotation: str = "none") -> Any:
    if rotation in (None, "none", "0"):
        return frame
    if rotation in ("cw", "90", "clockwise"):
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation in ("ccw", "-90", "counterclockwise"):
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation in ("180", "flip"):
        return cv2.rotate(frame, cv2.ROTATE_180)
    raise ValueError(f"Unsupported camera rotation '{rotation}'. Use none, cw, ccw, or 180.")
