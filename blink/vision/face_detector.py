"""Face detection using MediaPipe Face Mesh."""

from typing import Optional, Any

import cv2
import mediapipe as mp
from loguru import logger
import numpy as np


class FaceDetector:
    """Detects faces using MediaPipe Face Mesh."""

    # MediaPipe Face Mesh indices for eyes
    LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

    def __init__(self, max_faces: int = 1, refine_landmarks: bool = True):
        """Initialize face detector.

        Args:
            max_faces: Maximum number of faces to detect.
            refine_landmarks: Whether to refine landmarks for eye precision.
        """
        self.max_faces = max_faces
        self.refine_landmarks = refine_landmarks
        self._mp_face_mesh: Optional[Any] = None

    def initialize(self) -> None:
        """Initialize MediaPipe Face Mesh."""
        if self._mp_face_mesh is not None:
            return

        try:
            # Try new MediaPipe API first
            self._mp_face_mesh = mp.FaceMesh(
                max_num_faces=self.max_faces,
                refine_landmarks=self.refine_landmarks,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except AttributeError:
            # Fallback to older API
            self._mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=self.max_faces,
                refine_landmarks=self.refine_landmarks,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        logger.info("MediaPipe Face Mesh initialized")

    def process_frame(self, frame: np.ndarray) -> Optional[dict]:
        """Process a frame and detect face landmarks.

        Args:
            frame: Input frame (BGR format from OpenCV).

        Returns:
            Dict with face landmarks and eye coordinates, or None if no face.
        """
        if self._mp_face_mesh is None:
            raise RuntimeError("FaceDetector not initialized. Call initialize() first.")

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame
        results = self._mp_face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return None

        # Get the largest face (by bounding box area)
        face_landmarks = self._select_largest_face(
            frame, results.multi_face_landmarks
        )

        if face_landmarks is None:
            return None

        # Extract eye landmarks
        left_eye = self._extract_eye_landmarks(
            face_landmarks.landmark, self.LEFT_EYE_INDICES
        )
        right_eye = self._extract_eye_landmarks(
            face_landmarks.landmark, self.RIGHT_EYE_INDICES
        )

        return {
            "landmarks": face_landmarks.landmark,
            "left_eye": left_eye,
            "right_eye": right_eye,
            "frame_shape": frame.shape,
        }

    def _select_largest_face(
        self,
        frame: np.ndarray,
        face_landmarks_list: list,
    ) -> Optional[Any]:
        """Select the largest face by bounding box area.

        Args:
            frame: Input frame for sizing.
            face_landmarks_list: List of detected face landmarks.

        Returns:
            Largest face landmarks.
        """
        if not face_landmarks_list:
            return None

        if len(face_landmarks_list) == 1:
            return face_landmarks_list[0]

        height, width = frame.shape[:2]

        # Calculate bounding box for each face
        face_areas = []
        for i, face in enumerate(face_landmarks_list):
            # Get bounding box from landmarks
            x_coords = [lm.x * width for lm in face.landmark]
            y_coords = [lm.y * height for lm in face.landmark]
            area = (max(x_coords) - min(x_coords)) * (max(y_coords) - min(y_coords))
            face_areas.append((area, i))

        # Return face with largest area
        face_areas.sort(reverse=True, key=lambda x: x[0])
        return face_landmarks_list[face_areas[0][1]]

    def _extract_eye_landmarks(
        self,
        landmarks: list,
        eye_indices: list,
    ) -> list[tuple[float, float]]:
        """Extract normalized eye landmark coordinates.

        Args:
            landmarks: Face landmarks from MediaPipe.
            eye_indices: Indices of eye landmarks.

        Returns:
            List of (x, y) normalized coordinates.
        """
        return [(landmarks[i].x, landmarks[i].y) for i in eye_indices]

    def cleanup(self) -> None:
        """Clean up MediaPipe resources."""
        if self._mp_face_mesh is not None:
            self._mp_face_mesh.close()
            self._mp_face_mesh = None
            logger.info("MediaPipe Face Mesh cleaned up")
