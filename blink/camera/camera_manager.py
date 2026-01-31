"""Camera capture and management."""

from collections import deque
from typing import Optional, Tuple, List

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
        return [cid for cid, _ in self.get_camera_info()]

    def get_camera_info(self) -> List[Tuple[int, str]]:
        """Enumerate camera IDs with friendly names on Windows (DirectShow); fallback to numeric IDs."""
        names: List[Tuple[int, str]] = []

        try:
            import ctypes
            from ctypes import wintypes

            ole32 = ctypes.OleDLL("ole32")
            ole32.CoInitialize(None)

            CLSCTX_INPROC_SERVER = 1
            IID_ICreateDevEnum = ctypes.c_char_p(b"\x2c\x00\x1f\x3c\x4b\x3f\x11\xd2\x9e\xe1\x00\xc0\x4f\xb6\x8d\x60")
            CLSID_SystemDeviceEnum = ctypes.c_char_p(b"\x62\x7b\x93\xa0\x7c\x10\x11\xd0\xa5\x49\x00\xa0\xc9\x22\x31\x96")
            CLSID_VideoInputDeviceCategory = ctypes.c_char_p(b"\x86\xd4\xe2\x80\x2d\xe8\x11\xd0\xac\x9d\x00\xaa\x00\x64\x8f\xb5")

            class ICreateDevEnum(ctypes.Structure):
                pass

            class IEnumMoniker(ctypes.Structure):
                pass

            class IMoniker(ctypes.Structure):
                pass

            ICreateDevEnum._fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]
            IEnumMoniker._fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]
            IMoniker._fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]

            # CoCreateInstance
            p_dev_enum = ctypes.POINTER(ICreateDevEnum)()
            ole32.CoCreateInstance.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ]
            res = ole32.CoCreateInstance(
                CLSID_SystemDeviceEnum,
                None,
                CLSCTX_INPROC_SERVER,
                IID_ICreateDevEnum,
                ctypes.byref(p_dev_enum),
            )
            if res != 0 or not p_dev_enum:
                raise RuntimeError("CoCreateInstance failed")

            # CreateClassEnumerator
            enum_moniker = ctypes.POINTER(IEnumMoniker)()
            create_enum = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)(
                p_dev_enum.contents.lpVtbl[3]
            )
            if create_enum(p_dev_enum, CLSID_VideoInputDeviceCategory, ctypes.byref(enum_moniker), 0) != 0:
                raise RuntimeError("CreateClassEnumerator failed")

            fetch = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.POINTER(IMoniker)), ctypes.POINTER(ctypes.c_ulong))(enum_moniker.contents.lpVtbl[3])
            prop_bag_clsid = ctypes.c_char_p(b"\x55\x12\xd0\x70\xaf\x9b\x11\xd0\x8c\xf1\x00\xc0\x4f\xc2\x8c\x0a")
            id_count = 0
            while True:
                moniker = ctypes.POINTER(IMoniker)()
                fetched = ctypes.c_ulong()
                if fetch(enum_moniker, 1, ctypes.byref(moniker), ctypes.byref(fetched)) != 0 or not fetched.value:
                    break
                name = f"Camera {id_count}"
                try:
                    bind_ctx = ctypes.c_void_p()
                    ole32.CreateBindCtx(0, ctypes.byref(bind_ctx))
                    display_name = ctypes.c_wchar_p()
                    moniker.contents.lpVtbl[5](moniker, bind_ctx, None, ctypes.byref(display_name))
                    if display_name and display_name.value:
                        name = display_name.value
                except Exception:
                    pass
                names.append((id_count, name))
                id_count += 1
            logger.info(f"Available cameras: {names}")
            ole32.CoUninitialize()
            if names:
                return names
        except Exception as exc:
            logger.debug(f"Camera name enumeration failed, using numeric IDs. ({exc})")

        # Fallback numeric check
        available: List[int] = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    available.append(i)
                    cap.release()
            except Exception:
                pass
        return [(cid, f"Camera {cid}") for cid in available]
