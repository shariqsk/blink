"""Blink statistics tracking."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque

from loguru import logger


@dataclass
class BlinkStatistics:
    """Tracks blink statistics over time."""

    total_blinks: int = 0
    session_start: datetime = field(default_factory=datetime.now)

    # Sliding window for recent blinks (timestamps)
    _blink_history: Deque[datetime] = field(default_factory=lambda: deque(maxlen=300))

    @property
    def session_duration_seconds(self) -> int:
        """Get session duration in seconds."""
        return int((datetime.now() - self.session_start).total_seconds())

    @property
    def blinks_per_minute(self) -> float:
        """Calculate current blink rate (blinks per minute)."""
        if not self._blink_history:
            return 0.0

        now = datetime.now()
        # Count blinks in last minute
        one_minute_ago = now.timestamp() - 60
        recent_blinks = sum(1 for ts in self._blink_history if ts.timestamp() > one_minute_ago)
        return float(recent_blinks)

    @property
    def blinks_last_minute(self) -> int:
        """Get blink count for last minute."""
        if not self._blink_history:
            return 0

        now = datetime.now()
        one_minute_ago = now.timestamp() - 60
        return sum(1 for ts in self._blink_history if ts.timestamp() > one_minute_ago)

    def record_blink(self) -> None:
        """Record a blink event."""
        self.total_blinks += 1
        self._blink_history.append(datetime.now())
        logger.debug(f"Blink recorded. Total: {self.total_blinks}, Rate: {self.blinks_per_minute:.1f}/min")

    def reset(self) -> None:
        """Reset statistics."""
        self.total_blinks = 0
        self.session_start = datetime.now()
        self._blink_history.clear()
        logger.info("Statistics reset")

    def get_summary(self) -> dict:
        """Get statistics summary.

        Returns:
            Dict with current statistics.
        """
        return {
            "total_blinks": self.total_blinks,
            "session_duration_seconds": self.session_duration_seconds,
            "blinks_per_minute": round(self.blinks_per_minute, 1),
            "blinks_last_minute": self.blinks_last_minute,
        }
