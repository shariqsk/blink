"""Face detection using MediaPipe Tasks FaceLandmarker (>=0.10)."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Optional, Any
import urllib.request

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

    def __init__(
        self,
        max_faces: int = 1,
        refine_landmarks: bool = True,
        min_detection_confidence: float = 0.3,
        min_presence_confidence: float = 0.3,
        min_tracking_confidence: float = 0.3,
        use_fallback_mesh: bool = True,
    ):
        self.max_faces = max_faces
        self.refine_landmarks = refine_landmarks
        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.use_fallback_mesh = use_fallback_mesh

        self._landmarker: Optional[mp_vision.FaceLandmarker] = None
        self._fallback_mesh: Optional[Any] = None  # mp.solutions.face_mesh.FaceMesh, created lazily

    def initialize(self) -> None:
        """Initialize FaceLandmarker using the packaged task asset."""
        if self._landmarker:
            return

        try:
            model_asset_path = self._get_model_path()
            base_opts = mp_tasks.BaseOptions(model_asset_path=model_asset_path)
            opts = mp_vision.FaceLandmarkerOptions(
                base_options=base_opts,
                num_faces=self.max_faces,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                min_face_detection_confidence=self.min_detection_confidence,
                min_face_presence_confidence=self.min_presence_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
            logger.info("MediaPipe Tasks FaceLandmarker initialized")
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                f"Failed to initialize MediaPipe FaceLandmarker: {exc}. "
                "Ensure mediapipe>=0.10.30 is installed and model download is allowed."
            ) from exc

    def _get_model_path(self) -> str:
        """Locate or download the face_landmarker.task asset."""
        # 1) Try bundled path
        try:
            with resources.path("mediapipe.modules.face_landmarker", "face_landmarker.task") as p:
                if p.exists():
                    return str(p)
        except Exception:
            pass

        # 2) Local cache under user data
        cache_dir = Path.home() / ".blink_runtime" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)
        local_path = cache_dir / "face_landmarker.task"
        if local_path.exists():
            return str(local_path)

        # 3) Download from official CDN
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        try:
            logger.info("Downloading face_landmarker.task (first run only)...")
            urllib.request.urlretrieve(url, local_path)
            logger.info(f"Model downloaded to {local_path}")
            return str(local_path)
        except Exception as exc:
            raise RuntimeError(
                "face_landmarker.task not found and download failed. "
                "Check your network or place the file at ~/.blink_runtime/models/face_landmarker.task"
            ) from exc

    def process_frame(self, frame: np.ndarray) -> Optional[dict]:
        """Process a frame and return landmarks for the largest face."""
        if not self._landmarker:
            raise RuntimeError("FaceDetector not initialized. Call initialize() first.")

        enhanced_frame = self._preprocess_frame(frame)
        frame_rgb = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return self._process_with_fallback(enhanced_frame, frame)

        # Select largest face
        face = self._select_largest_face(frame, result.face_landmarks)
        if face is None:
            return self._process_with_fallback(enhanced_frame, frame)

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
        if self._fallback_mesh:
            # FaceMesh provides a close() for explicit resource release
            try:
                self._fallback_mesh.close()
            except Exception:
                pass
            self._fallback_mesh = None
            logger.info("Fallback FaceMesh cleaned up")

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Boost contrast on dark frames to help detection in low light."""
        gray_mean = float(frame.mean())
        if gray_mean >= 60.0:
            return frame

        # Apply CLAHE on the L channel for gentle brightening without blowing highlights
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_eq = clahe.apply(l)
        lab_eq = cv2.merge((l_eq, a, b))
        return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    def _ensure_fallback_mesh(self) -> None:
        """Lazily create a FaceMesh fallback when Tasks model misses faces."""
        if self._fallback_mesh or not self.use_fallback_mesh:
            return
        try:
            self._fallback_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=self.max_faces,
                refine_landmarks=True,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
            logger.info("Fallback MediaPipe FaceMesh initialized")
        except Exception as exc:
            logger.warning(f"Fallback FaceMesh init failed: {exc}")
            self._fallback_mesh = None

    def _process_with_fallback(self, enhanced_frame: np.ndarray, original_frame: np.ndarray) -> Optional[dict]:
        """Try a lighter-weight fallback detector when the Tasks model finds no face."""
        if not self.use_fallback_mesh:
            return None

        self._ensure_fallback_mesh()
        if self._fallback_mesh is None:
            return None

        frame_rgb = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        mesh_result = self._fallback_mesh.process(frame_rgb)
        if not mesh_result.multi_face_landmarks:
            return None

        faces = [lm.landmark for lm in mesh_result.multi_face_landmarks]
        face = self._select_largest_face(original_frame, faces)
        if face is None:
            return None

        left_eye = self._extract_eye(face, self.LEFT_EYE_INDICES)
        right_eye = self._extract_eye(face, self.RIGHT_EYE_INDICES)

        return FaceResult(
            landmarks=face,
            left_eye=left_eye,
            right_eye=right_eye,
            frame_shape=original_frame.shape,
        ).__dict__
