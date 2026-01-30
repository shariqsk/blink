"""Vision processing worker thread (stub implementation)."""

import random
from time import time

from loguru import logger
from PyQt6.QtCore import QThread, QTimer, pyqtSignal


class VisionWorker(QThread):
    """Stub vision worker that generates fake blink events for testing."""

    blink_detected = pyqtSignal()
    statistics_updated = pyqtSignal(dict)
    face_detected = pyqtSignal(bool)

    def __init__(self):
        """Initialize vision worker."""
        super().__init__()
        self._running = False
        self._face_visible = False

        # Fake blink timing
        self._last_blink_time = time()
        self._blink_interval_range = (3.0, 7.0)  # Seconds between fake blinks

    def start_monitoring(self) -> None:
        """Start monitoring."""
        self._running = True
        self._face_visible = True
        logger.info("Vision worker started (stub mode - generating fake blinks)")

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._running = False
        self._face_visible = False
        self.face_detected.emit(False)
        logger.info("Vision worker stopped")

    def run(self) -> None:
        """Main worker loop - generates fake blink events."""
        while True:
            if not self._running:
                self.msleep(100)
                continue

            # Simulate face detection
            if not self._face_visible:
                self._face_visible = True
                self.face_detected.emit(True)

            # Generate fake blink events
            current_time = time()
            time_since_blink = current_time - self._last_blink_time

            # Random interval for fake blinks (3-7 seconds)
            min_interval, max_interval = self._blink_interval_range
            if time_since_blink > random.uniform(min_interval, max_interval):
                self._last_blink_time = current_time
                self.blink_detected.emit()
                logger.debug("Fake blink event generated")

                # Update statistics (fake data)
                stats = {
                    "total_blinks": random.randint(100, 500),
                    "session_duration_seconds": int(time_since_blink * 100),
                    "blinks_per_minute": round(random.uniform(10.0, 20.0), 1),
                }
                self.statistics_updated.emit(stats)

            self.msleep(100)  # 10Hz check rate

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running
