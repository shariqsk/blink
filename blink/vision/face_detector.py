"""Face detection using MediaPipe Tasks FaceLandmarker (>=0.10)."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Optional, Any

import cv2
import mediapipe as mp
import numpy as np
from loguru import logger

from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.components.containers import landmark as mp_landmark


@dataclass
class FaceResult:
    """Normalized landmark containers for a single face."""

    landmarks: list[mp_landmark.NormalizedLandmark]
    left_eye: list[tuple[float, float]]
    right_eye: list[tuple[float, float]]
    frame_shape: tuple[int, int, int]


class FaceDetector:
    """Detects faces and eye landmarks via MediaPipe Tasks FaceLandmarker."""

    LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

    def __init__(self, max_faces: int = 1, refine_landmarks: bool = True):
        self.max_faces = max_faces
        self.refine_landmarks = refine_landmarks
        self._landmarker: Optional[mp_vision.FaceLandmarker] = None

    def initialize(self) -> None:
        """Initialize FaceLandmarker using the packaged task asset."""
        if self._landmarker:
            return

        try:
            model_asset_path = self._get_packaged_model_path()
            base_opts = mp_tasks.BaseOptions(model_asset_path=model_asset_path)
            opts = mp_vision.FaceLandmarkerOptions(
                base_options=base_opts,
                num_faces=self.max_faces,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
            logger.info("MediaPipe Tasks FaceLandmarker initialized")
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                f"Failed to initialize MediaPipe FaceLandmarker: {exc}. "
                "Ensure mediapipe>=0.10.30 is installed."
            ) from exc

    def _get_packaged_model_path(self) -> str:
        """Locate the face_landmarker.task asset inside the mediapipe package."""
        try:
            with resources.path("mediapipe.modules.face_landmarker", "face_landmarker.task") as p:
                return str(p)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Could not find bundled face_landmarker.task inside the mediapipe package."
            ) from exc

    def process_frame(self, frame: np.ndarray) -> Optional[dict]:
        """Process a frame and return landmarks for the largest face."""
        if not self._landmarker:
            raise RuntimeError("FaceDetector not initialized. Call initialize() first.")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None

        # Select largest face
        face = self._select_largest_face(frame, result.face_landmarks)
        if face is None:
            return None

        left_eye = self._extract_eye(face, self.LEFT_EYE_INDICES)
        right_eye = self._extract_eye(face, self.RIGHT_EYE_INDICES)

        return FaceResult(
            landmarks=face,
            left_eye=left_eye,
            right_eye=right_eye,
            frame_shape=frame.shape,
        ).__dict__

    def _select_largest_face(
        self,
        frame: np.ndarray,
        faces: list[list[mp_landmark.NormalizedLandmark]],
    ) -> Optional[list[mp_landmark.NormalizedLandmark]]:
        """Pick the face with the largest bounding box area."""
        if len(faces) == 1:
            return faces[0]

        h, w = frame.shape[:2]
        areas: list[tuple[float, int]] = []
        for idx, lm_list in enumerate(faces):
            xs = [lm.x * w for lm in lm_list]
            ys = [lm.y * h for lm in lm_list]
            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
            areas.append((area, idx))
        areas.sort(reverse=True, key=lambda t: t[0])
        return faces[areas[0][1]] if areas else None

    def _extract_eye(
        self, landmarks: list[mp_landmark.NormalizedLandmark], indices: list[int]
    ) -> list[tuple[float, float]]:
        return [(landmarks[i].x, landmarks[i].y) for i in indices]

    def cleanup(self) -> None:
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
            logger.info("FaceLandmarker cleaned up")
