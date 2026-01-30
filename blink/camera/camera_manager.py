"""Camera capture and management."""

from collections import deque
from typing import Optional

import cv2
from loguru import logger
from PyQt6.QtCore import QMutex, QObject, pyqtSignal


class CameraManager(QObject):
    """Manages camera capture with thread-safe frame queue."""

    frame_captured = pyqtSignal(object)  # Emits frame
    camera_error = pyqtSignal(str)

    def __init__(self):
        """Initialize camera manager."""
        super().__init__()
        self._capture: Optional[cv2.VideoCapture] = None
        self._camera_id = 0
        self._resolution = (640, 480)
        self._is_open = False
        self._mutex = QMutex()

    def open_camera(
        self,
        camera_id: int = 0,
        resolution: tuple[int, int] = (640, 480),
    ) -> bool:
        """Open camera device.

        Args:
            camera_id: Camera device ID (0 for default).
            resolution: Capture resolution (width, height).

        Returns:
            True if successful.
        """
        self._mutex.lock()

        try:
            # Close existing camera
            if self._capture is not None:
                self.close_camera()

            # Open camera
            self._capture = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)

            if not self._capture.isOpened():
                self.camera_error.emit(f"Failed to open camera {camera_id}")
                logger.error(f"Failed to open camera {camera_id}")
                return False

            # Set resolution
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

            # Verify resolution was set
            actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._resolution = (actual_width, actual_height)

            self._camera_id = camera_id
            self._is_open = True

            logger.info(f"Camera opened: ID={camera_id}, Resolution={self._resolution}")
            return True

        except Exception as e:
            self.camera_error.emit(f"Camera error: {str(e)}")
            logger.error(f"Camera error: {e}")
            return False

        finally:
            self._mutex.unlock()

    def capture_frame(self) -> Optional[cv2.typing.MatLike]:
        """Capture a single frame.

        Returns:
            Frame array or None if capture failed.
        """
        self._mutex.lock()

        try:
            if not self._is_open or self._capture is None:
                return None

            ret, frame = self._capture.read()

            if not ret or frame is None:
                logger.warning("Failed to capture frame")
                return None

            return frame

        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None

        finally:
            self._mutex.unlock()

    def close_camera(self) -> None:
        """Close camera device."""
        self._mutex.lock()

        try:
            if self._capture is not None:
                self._capture.release()
                self._capture = None
                self._is_open = False
                logger.info("Camera closed")

        except Exception as e:
            logger.error(f"Error closing camera: {e}")

        finally:
            self._mutex.unlock()

    def is_open(self) -> bool:
        """Check if camera is open.

        Returns:
            True if camera is open.
        """
        self._mutex.lock()
        result = self._is_open and self._capture is not None and self._capture.isOpened()
        self._mutex.unlock()
        return result

    @property
    def resolution(self) -> tuple[int, int]:
        """Get current resolution.

        Returns:
            Tuple of (width, height).
        """
        return self._resolution

    @property
    def camera_id(self) -> int:
        """Get camera ID.

        Returns:
            Camera device ID.
        """
        return self._camera_id

    def get_available_cameras(self) -> list[int]:
        """Get list of available camera IDs.

        Returns:
            List of available camera IDs.
        """
        available = []
        for i in range(10):  # Check first 10 cameras
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    available.append(i)
                    cap.release()
            except Exception:
                pass

        logger.info(f"Available cameras: {available}")
        return available
