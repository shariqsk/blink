"""Vision processing worker thread with real MediaPipe detection."""

from datetime import datetime
from time import time, sleep
from typing import Optional

import cv2
import numpy as np

from blink.camera.camera_manager import CameraManager
from blink.camera.capture_thread import CaptureThread
from blink.camera.frame_queue import FrameQueue
from blink.vision.blink_detector import BlinkDetector, BlinkMetrics
from blink.vision.eye_analyzer import EyeAnalyzer, EyeMetrics
from blink.vision.face_detector import FaceDetector
from loguru import logger
from PyQt6.QtCore import QObject, QThread, QMutex, QTimer, pyqtSignal


class VisionWorker(QObject):
    """Vision processing worker with real eye detection."""

    # Status signals
    blink_detected = pyqtSignal()
    statistics_updated = pyqtSignal(dict)
    face_detected = pyqtSignal(bool)
    camera_status_changed = pyqtSignal(bool)
    frame_preview = pyqtSignal(object)  # Emits small BGR frame for UI preview
    calibration_progress = pyqtSignal(int)  # Emits percentage
    calibration_complete = pyqtSignal(float)

    # Error signals
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        camera_manager: CameraManager,
        target_fps: int = 15,
        camera_id: int = 0,
        resolution: tuple[int, int] = (640, 480),
    ):
        """Initialize vision worker.

        Args:
            camera_manager: Camera manager instance.
            target_fps: Target frames per second.
            camera_id: Preferred camera ID.
            resolution: Preferred resolution (width, height).
        """
        super().__init__()
        self.camera_manager = camera_manager
        self.target_fps = target_fps
        self.camera_id = camera_id
        self.resolution = resolution

        # Processing components
        self._face_detector: Optional[FaceDetector] = None
        self._eye_analyzer: Optional[EyeAnalyzer] = None
        self._blink_detector: Optional[BlinkDetector] = None

        # Threads and queues
        self._capture_thread: Optional[CaptureThread] = None
        # Keep only the freshest frame to reduce latency
        self._frame_queue = FrameQueue(max_size=1)

        # State
        self._running = False
        self._calibrating = False
        self._mutex = QMutex()

        # Calibration data
        self._calibration_samples: list[float] = []
        self._calibration_duration = 5  # seconds

        # Current metrics
        self._current_ear = 0.0
        self._last_face_detected = False
        self._last_stats_time = time()
        self._binks_in_last_minute = 0
        self._preview_skip = 0

    def initialize(self) -> None:
        """Initialize vision components."""
        logger.info("Initializing vision components")

        self._face_detector = FaceDetector(max_faces=1, refine_landmarks=True)
        self._face_detector.initialize()

        self._eye_analyzer = EyeAnalyzer(ear_threshold=0.21, consecutive_frames=2)

        self._blink_detector = BlinkDetector(
            blink_consecutive_frames=2,
            min_blink_duration_ms=50,
            max_blink_duration_ms=500,
        )

        # Initialize capture thread
        self._capture_thread = CaptureThread(self.camera_manager, self.target_fps)
        # Cross-thread signals will be queued automatically because CaptureThread lives on its own thread
        self._capture_thread.frame_ready.connect(self._process_frame)
        self._capture_thread.camera_status_changed.connect(self.camera_status_changed)
        self._capture_thread.camera_error.connect(self.error_occurred)

        logger.info("Vision components initialized")

    def warm_start(self) -> None:
        """Eagerly initialize heavy components without starting monitoring."""
        if self._face_detector is None:
            try:
                self.initialize()
            except Exception as exc:
                logger.error(f"Warm start failed: {exc}")

    def start_monitoring(self) -> None:
        """Start vision monitoring."""
        self._mutex.lock()
        try:
            if self._running:
                return

            if not self.camera_manager.is_open():
                # Try to open camera
                if not self.camera_manager.open_camera(
                    camera_id=self.camera_id,
                    resolution=self.resolution,
                ):
                    self.error_occurred.emit("Failed to open camera")
                    return

            # Initialize if not already
            if self._face_detector is None:
                try:
                    self.initialize()
                except Exception as exc:
                    self.error_occurred.emit(str(exc))
                    logger.error(f"Initialization failed: {exc}")
                    return

            # Start capture thread
            if self._capture_thread:
                self._capture_thread.start_capture()
                if not self._capture_thread.isRunning():
                    self._capture_thread.start()

            self._running = True
            self._calibrating = False
            logger.info("Vision monitoring started")

        finally:
            self._mutex.unlock()

    def stop_monitoring(self) -> None:
        """Stop vision monitoring."""
        self._mutex.lock()
        try:
            if not self._running:
                return

            self._running = False
            self._calibrating = False

            # Stop capture thread
            if self._capture_thread:
                self._capture_thread.stop_capture()

            # Clear frame queue
            self._frame_queue.clear()

            # Keep camera open to allow instant restart; only emit inactive status
            self.camera_status_changed.emit(False)
            self.face_detected.emit(False)
            logger.info("Vision monitoring stopped")

        finally:
            self._mutex.unlock()

    def start_calibration(self) -> None:
        """Start calibration phase."""
        self._mutex.lock()
        try:
            if not self._running:
                logger.warning("Cannot calibrate: monitoring not active")
                return

            self._calibrating = True
            self._calibration_samples = []
            logger.info("Calibration started")
            self.calibration_progress.emit(0)

        finally:
            self._mutex.unlock()

    def _process_frame(self, frame: np.ndarray) -> None:
        """Process a captured frame.

        Args:
            frame: Captured frame (BGR).
        """
        if not self._running:
            return

        try:
            # Process frame with face detector
            face_result = self._face_detector.process_frame(frame)

            if face_result is None:
                # No face detected
                if self._last_face_detected:
                    self.face_detected.emit(False)
                    self._last_face_detected = False
                return

            # Face detected
            if not self._last_face_detected:
                self.face_detected.emit(True)
                self._last_face_detected = True

            # Analyze eyes
            eye_metrics = self._eye_analyzer.analyze_eyes(
                face_result["left_eye"],
                face_result["right_eye"],
            )

            # Emit preview every ~3 frames to reduce UI load
            self._preview_skip = (self._preview_skip + 1) % 3
            if self._preview_skip == 0:
                self.frame_preview.emit(frame)

            # Calibrate if in calibration mode
            if self._calibrating:
                self._process_calibration(eye_metrics.avg_ear)
                return

            # Detect blinks
            blink_metrics = self._blink_detector.process_frame(eye_metrics)

            # Update current EAR
            self._current_ear = blink_metrics.current_ear

            # Emit blink event if detected
            if blink_metrics.blink_detected:
                self.blink_detected.emit()

            # Update statistics periodically (every second)
            current_time = time()
            if current_time - self._last_stats_time >= 1.0:
                self._update_statistics(blink_metrics)
                self._last_stats_time = current_time

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            self.error_occurred.emit(f"Frame processing error: {str(e)}")

    def _process_calibration(self, ear: float) -> None:
        """Process calibration frame.

        Args:
            ear: Current Eye Aspect Ratio.
        """
        self._calibration_samples.append(ear)

        # Calculate progress (we need ~5 seconds at 15 FPS = ~75 samples)
        progress = min(100, len(self._calibration_samples) * 100 // (self.target_fps * self._calibration_duration))
        self.calibration_progress.emit(progress)

        # Check if calibration complete
        if len(self._calibration_samples) >= self.target_fps * self._calibration_duration:
            self._complete_calibration()

    def _complete_calibration(self) -> None:
        """Complete calibration and apply threshold."""
        if not self._calibration_samples:
            logger.warning("No calibration samples collected")
            return

        # Calculate and set threshold
        threshold = self._eye_analyzer.calibrate_threshold(self._calibration_samples)

        self._calibrating = False
        logger.info(f"Calibration complete, threshold: {threshold:.3f}")

        self.calibration_complete.emit(threshold)

    def _update_statistics(self, blink_metrics: BlinkMetrics) -> None:
        """Update and emit statistics.

        Args:
            blink_metrics: Current blink metrics.
        """
        stats = {
            "total_blinks": self._blink_detector.get_total_blinks(),
            "current_ear": round(self._current_ear, 3),
            "blinks_per_minute": round(blink_metrics.blink_rate_per_minute, 1),
            "blinks_last_minute": blink_metrics.blinks_last_minute,
            "time_since_last_blink_seconds": round(
                blink_metrics.time_since_last_blink_seconds, 1
            ),
            "consecutive_open_seconds": round(blink_metrics.consecutive_open_seconds, 1),
        }

        self.statistics_updated.emit(stats)

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up vision worker")

        self.stop_monitoring()

        if self._capture_thread:
            self._capture_thread.shutdown()
            self._capture_thread.wait(2000)
            self._capture_thread = None

        if self._face_detector:
            self._face_detector.cleanup()
            self._face_detector = None

        self.camera_manager.close_camera()
        self._frame_queue.clear()

        logger.info("Vision worker cleanup complete")

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        self._mutex.lock()
        result = self._running
        self._mutex.unlock()
        return result

    @property
    def is_calibrating(self) -> bool:
        """Check if calibration is in progress."""
        return self._calibrating

    @property
    def current_ear(self) -> float:
        """Get current Eye Aspect Ratio."""
        return self._current_ear

    def get_ear_threshold(self) -> float:
        """Get current EAR threshold."""
        if self._eye_analyzer:
            return self._eye_analyzer.get_threshold()
        return 0.21

    def set_ear_threshold(self, threshold: float) -> None:
        """Set EAR threshold.

        Args:
            threshold: New EAR threshold.
        """
        if self._eye_analyzer:
            self._eye_analyzer.set_threshold(threshold)
            logger.info(f"EAR threshold set to {threshold:.3f}")

    def set_target_fps(self, fps: int) -> None:
        """Set target FPS.

        Args:
            fps: New target FPS.
        """
        self.target_fps = fps
        if self._capture_thread:
            self._capture_thread.set_target_fps(fps)
        logger.info(f"Target FPS set to {fps}")

    def set_camera_resolution(self, resolution: tuple[int, int]) -> None:
        """Set camera resolution.

        Args:
            resolution: Resolution tuple (width, height).
        """
        if self.camera_manager.is_open():
            # Need to restart camera with new resolution
            self.stop_monitoring()
            self.camera_manager.open_camera(
                camera_id=self.camera_id,
                resolution=resolution,
            )
            self.start_monitoring()
        else:
            self.camera_manager.open_camera(
                camera_id=self.camera_id,
                resolution=resolution,
            )

        logger.info(f"Camera resolution set to {resolution}")

    def set_camera_id(self, camera_id: int) -> None:
        """Set camera device ID."""
        self.camera_id = camera_id
        logger.info(f"Camera ID set to {camera_id}")
