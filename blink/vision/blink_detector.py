"""Blink detection from eye metrics."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


@dataclass
class BlinkEvent:
    """Represents a detected blink event."""

    timestamp: datetime
    duration_ms: int


@dataclass
class BlinkMetrics:
    """Comprehensive blink metrics."""

    blink_detected: bool
    both_eyes_closed: bool
    current_ear: float
    blink_rate_per_minute: float
    blinks_last_minute: int
    time_since_last_blink_seconds: float
    consecutive_open_seconds: float


class BlinkDetector:
    """Detects blinks and tracks blink patterns."""

    def __init__(
        self,
        blink_consecutive_frames: int = 2,
        min_blink_duration_ms: int = 50,
        max_blink_duration_ms: int = 500,
    ):
        """Initialize blink detector.

        Args:
            blink_consecutive_frames: Consecutive closed frames to count as blink.
            min_blink_duration_ms: Minimum duration to qualify as blink.
            max_blink_duration_ms: Maximum duration to count as blink (longer = eyes closed).
        """
        self.blink_consecutive_frames = blink_consecutive_frames
        self.min_blink_duration_ms = min_blink_duration_ms
        self.max_blink_duration_ms = max_blink_duration_ms

        # State tracking
        self._both_closed_counter = 0
        self._both_closed_start_time: Optional[datetime] = None

        # Blink history (sliding window of last 60 seconds)
        self._blink_history: deque[datetime] = deque(maxlen=300)

        # Last blink tracking
        self._last_blink_time: Optional[datetime] = None
        self._last_open_time = datetime.now()

        # Metrics
        self._total_blinks = 0

    def process_frame(
        self,
        eye_metrics,
        frame_timestamp: Optional[datetime] = None,
    ) -> BlinkMetrics:
        """Process frame eye metrics and detect blinks.

        Args:
            eye_metrics: EyeMetrics from EyeAnalyzer.
            frame_timestamp: Timestamp of this frame.

        Returns:
            BlinkMetrics with detection results.
        """
        if frame_timestamp is None:
            frame_timestamp = datetime.now()

        # Check if both eyes are closed
        both_closed = not eye_metrics.both_open

        # Detect blink event
        blink_detected = self._detect_blink(both_closed, frame_timestamp)

        # Update blink history
        if blink_detected:
            self._blink_history.append(frame_timestamp)
            self._last_blink_time = frame_timestamp

        # Track consecutive open time
        if eye_metrics.both_open:
            self._last_open_time = frame_timestamp

        # Calculate metrics
        blink_rate = self._calculate_blink_rate()
        blinks_last_minute = self._count_blinks_last_minute()
        time_since_last_blink = self._get_time_since_last_blink(frame_timestamp)
        consecutive_open_seconds = (frame_timestamp - self._last_open_time).total_seconds()

        return BlinkMetrics(
            blink_detected=blink_detected,
            both_eyes_closed=both_closed,
            current_ear=eye_metrics.avg_ear,
            blink_rate_per_minute=blink_rate,
            blinks_last_minute=blinks_last_minute,
            time_since_last_blink_seconds=time_since_last_blink,
            consecutive_open_seconds=consecutive_open_seconds,
        )

    def _detect_blink(self, both_closed: bool, timestamp: datetime) -> bool:
        """Detect if current state represents a blink.

        Args:
            both_closed: Whether both eyes are currently closed.
            timestamp: Current frame timestamp.

        Returns:
            True if a blink is detected.
        """
        if both_closed:
            # Start or continue closure tracking
            if self._both_closed_start_time is None:
                self._both_closed_start_time = timestamp
                self._both_closed_counter = 1
            else:
                self._both_closed_counter += 1
            return False

        # Eyes are open - check if we just completed a blink
        if self._both_closed_counter >= self.blink_consecutive_frames:
            # Calculate duration
            if self._both_closed_start_time:
                duration = int((timestamp - self._both_closed_start_time).total_seconds() * 1000)

                # Check if within blink duration bounds
                if (
                    self.min_blink_duration_ms
                    <= duration
                    <= self.max_blink_duration_ms
                ):
                    self._total_blinks += 1
                    logger.debug(f"Blink detected (duration: {duration}ms)")
                    return True

        # Reset counters
        self._both_closed_counter = 0
        self._both_closed_start_time = None

        return False

    def _calculate_blink_rate(self) -> float:
        """Calculate current blink rate (blinks per minute).

        Returns:
            Blink rate per minute.
        """
        if not self._blink_history:
            return 0.0

        # Count blinks in last minute
        now = datetime.now()
        one_minute_ago = now - timedelta(seconds=60)
        recent_blinks = sum(1 for ts in self._blink_history if ts > one_minute_ago)

        return float(recent_blinks)

    def _count_blinks_last_minute(self) -> int:
        """Count blinks in last minute.

        Returns:
            Number of blinks in last minute.
        """
        if not self._blink_history:
            return 0

        now = datetime.now()
        one_minute_ago = now - timedelta(seconds=60)
        return sum(1 for ts in self._blink_history if ts > one_minute_ago)

    def _get_time_since_last_blink(self, timestamp: datetime) -> float:
        """Get time since last blink in seconds.

        Args:
            timestamp: Current timestamp.

        Returns:
            Seconds since last blink, or 0 if no blinks yet.
        """
        if self._last_blink_time is None:
            return 0.0

        return (timestamp - self._last_blink_time).total_seconds()

    def get_total_blinks(self) -> int:
        """Get total blink count.

        Returns:
            Total number of blinks detected.
        """
        return self._total_blinks

    def reset(self) -> None:
        """Reset all blink tracking state."""
        self._both_closed_counter = 0
        self._both_closed_start_time = None
        self._blink_history.clear()
        self._last_blink_time = None
        self._last_open_time = datetime.now()
        self._total_blinks = 0
        logger.info("Blink detector reset")

    def is_eyes_open_too_long(self, threshold_seconds: float) -> bool:
        """Check if eyes have been open too long without blinking.

        Args:
            threshold_seconds: Maximum allowed open duration.

        Returns:
            True if eyes have been open longer than threshold.
        """
        if self._last_blink_time is None:
            return False

        consecutive_open = (datetime.now() - self._last_blink_time).total_seconds()
        return consecutive_open > threshold_seconds

    def is_low_blink_rate(
        self,
        min_blinks_per_minute: int,
        duration_minutes: int,
    ) -> bool:
        """Check if blink rate has been low for a duration.

        Args:
            min_blinks_per_minute: Minimum acceptable blinks per minute.
            duration_minutes: How long to check (in minutes).

        Returns:
            True if low blink rate detected for specified duration.
        """
        if not self._blink_history:
            return False

        now = datetime.now()
        check_duration = timedelta(minutes=duration_minutes)

        # Count blinks in the last duration_minutes
        blinks_in_window = sum(1 for ts in self._blink_history if ts > now - check_duration)

        return blinks_in_window < (min_blinks_per_minute * duration_minutes)
