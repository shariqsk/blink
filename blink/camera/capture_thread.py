"""Camera capture worker thread."""

from time import time, sleep

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal

import cv2
import numpy as np

from blink.camera.camera_manager import CameraManager


class CaptureThread(QThread):
    """Worker thread for continuous camera capture."""

    frame_ready = pyqtSignal(object)  # Emits frame
    camera_error = pyqtSignal(str)
    camera_status_changed = pyqtSignal(bool)

    def __init__(
        self,
        camera_manager: CameraManager,
        target_fps: int = 15,
    ):
        """Initialize capture thread.

        Args:
            camera_manager: Camera manager instance.
            target_fps: Target frames per second.
        """
        super().__init__()
        self.camera_manager = camera_manager
        self.target_fps = target_fps
        self._running = False
        self._camera_enabled = True
        self._frame_interval = 1.0 / target_fps

    def start_capture(self) -> None:
        """Start camera capture."""
        self._running = True
        self._camera_enabled = True
        logger.info(f"Capture thread started (target FPS: {self.target_fps})")

    def stop_capture(self) -> None:
        """Stop camera capture (keeps thread alive but idle)."""
        self._running = False
        self._camera_enabled = False
        logger.info("Capture thread stopped")

    def shutdown(self) -> None:
        """Request the thread to exit its run loop."""
        self._running = False
        self._camera_enabled = False
        self.requestInterruption()
        logger.info("Capture thread shutdown requested")

    def run(self) -> None:
        """Main capture loop."""
        while not self.isInterruptionRequested():
            if not self._running:
                self.msleep(100)
                continue

            if not self._camera_enabled:
                self.camera_status_changed.emit(False)
                self.msleep(100)
                continue

            # Check if camera is open
            if not self.camera_manager.is_open():
                self.camera_status_changed.emit(False)
                self.msleep(500)
                continue

            # Emit status
            self.camera_status_changed.emit(True)

            # Capture frame
            frame = self.camera_manager.capture_frame()

            if frame is None:
                self.msleep(100)
                continue

            # Emit frame
            self.frame_ready.emit(frame)

            # Throttle to target FPS
            frame_time = time()
            sleep(max(0, self._frame_interval - (time() - frame_time)))

        logger.info("Capture thread exiting")

    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running

    @property
    def is_camera_enabled(self) -> bool:
        """Check if camera is enabled."""
        return self._camera_enabled

    def set_target_fps(self, fps: int) -> None:
        """Set target FPS.

        Args:
            fps: New target FPS.
        """
        self.target_fps = fps
        self._frame_interval = 1.0 / fps
        logger.info(f"Target FPS set to {fps}")
