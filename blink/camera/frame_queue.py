"""Thread-safe frame queue for camera frames."""

from collections import deque
from threading import Lock
from typing import Optional

import numpy as np


class FrameQueue:
    """Thread-safe bounded queue for camera frames."""

    def __init__(self, max_size: int = 3):
        """Initialize frame queue.

        Args:
            max_size: Maximum number of frames to queue.
        """
        self._queue: deque[np.ndarray] = deque(maxlen=max_size)
        self._lock = Lock()
        self._max_size = max_size
        self._dropped_frames = 0

    def put(self, frame: np.ndarray) -> bool:
        """Add frame to queue.

        Args:
            frame: Frame to add.

        Returns:
            True if frame was added, False if queue was full.
        """
        with self._lock:
            if len(self._queue) >= self._max_size:
                # Drop oldest frame
                self._queue.popleft()
                self._dropped_frames += 1

            self._queue.append(frame)
            return True

    def get(self) -> Optional[np.ndarray]:
        """Get next frame from queue.

        Returns:
            Frame or None if queue is empty.
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def clear(self) -> None:
        """Clear all frames from queue."""
        with self._lock:
            self._queue.clear()
            self._dropped_frames = 0

    def size(self) -> int:
        """Get current queue size.

        Returns:
            Number of frames in queue.
        """
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue is empty.
        """
        with self._lock:
            return len(self._queue) == 0

    def get_dropped_count(self) -> int:
        """Get number of dropped frames.

        Returns:
            Number of frames dropped due to full queue.
        """
        with self._lock:
            return self._dropped_frames
