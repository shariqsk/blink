"""Blink monitoring logic and rules engine."""

from datetime import datetime, timedelta
from typing import Optional

from blink.config.settings import Settings
from blink.core.statistics import BlinkStatistics
from loguru import logger
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class BlinkMonitor(QObject):
    """Monitors blink events and triggers alerts based on rules."""

    alert_triggered = pyqtSignal()
    alert_cleared = pyqtSignal()

    def __init__(self, settings: Settings):
        """Initialize blink monitor.

        Args:
            settings: Application settings.
        """
        super().__init__()
        self.settings = settings
        self.stats = BlinkStatistics()
        self._last_blink_time: Optional[datetime] = None
        self._is_running = False
        self._should_alert = False
        self._last_alert_time: Optional[datetime] = None

        # Alert cooldown (minimum time between alerts)
        self._alert_cooldown_seconds = 60

        # Timer for periodic checks
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._periodic_check)

    def start(self) -> None:
        """Start monitoring."""
        self._is_running = True
        self.stats.reset()
        self._should_alert = False
        self._last_alert_time = None
        self._check_timer.start(5000)  # Check every 5 seconds
        logger.info("Blink monitor started")

    def stop(self) -> None:
        """Stop monitoring."""
        self._is_running = False
        self._check_timer.stop()
        if self._should_alert:
            self._should_alert = False
            self.alert_cleared.emit()
        logger.info("Blink monitor stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._is_running

    def record_blink(self) -> None:
        """Record a blink event and check rules."""
        if not self._is_running:
            return

        self.stats.record_blink()
        self._last_blink_time = datetime.now()

        # Clear alert if we're blinking again
        if self._should_alert:
            self._should_alert = False
            self.alert_cleared.emit()

        logger.debug(
            f"Blink recorded. Rate: {self.stats.blinks_per_minute:.1f}/min, "
            f"Total: {self.stats.total_blinks}"
        )

    def check_alert_condition(self) -> bool:
        """Check if alert should be triggered based on rules.

        Returns:
            True if alert should trigger.
        """
        if not self._is_running:
            return False

        # Need at least 1 minute of session
        if self.stats.session_duration_seconds < 60:
            return False

        # Check alert cooldown
        if self._last_alert_time:
            time_since_alert = (datetime.now() - self._last_alert_time).total_seconds()
            if time_since_alert < self._alert_cooldown_seconds:
                return False

        # Check blink rate threshold
        current_rate = self.stats.blinks_per_minute
        threshold = self.settings.min_blinks_per_minute

        # Check if blink rate is below threshold
        should_alert = current_rate < threshold

        if should_alert and not self._should_alert:
            logger.warning(
                f"Low blink rate detected: {current_rate:.1f}/min < {threshold}/min"
            )
            self._should_alert = True
            self._last_alert_time = datetime.now()
            return True

        return False

    def _periodic_check(self) -> None:
        """Periodic check for alert conditions."""
        if self.check_alert_condition():
            self.alert_triggered.emit()

    def check_eyes_open_too_long(self, threshold_seconds: float) -> bool:
        """Check if eyes have been open too long without blinking.

        Args:
            threshold_seconds: Maximum allowed open duration.

        Returns:
            True if eyes have been open longer than threshold.
        """
        if not self._is_running or self._last_blink_time is None:
            return False

        time_since_blink = (datetime.now() - self._last_blink_time).total_seconds()
        return time_since_blink > threshold_seconds

    def check_low_blink_rate(
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
        if not self._is_running:
            return False

        # Need at least duration_minutes of session
        if self.stats.session_duration_seconds < duration_minutes * 60:
            return False

        # Get blinks in last duration_minutes
        threshold_time = datetime.now() - timedelta(minutes=duration_minutes)
        blinks_in_window = sum(
            1 for ts in self.stats._blink_history if ts > threshold_time
        )

        expected_blinks = min_blinks_per_minute * duration_minutes
        return blinks_in_window < expected_blinks

    def get_statistics(self) -> dict:
        """Get current statistics.

        Returns:
            Statistics dictionary.
        """
        stats = self.stats.get_summary()

        # Add additional metrics
        time_since_last_blink = 0.0
        if self._last_blink_time:
            time_since_last_blink = (datetime.now() - self._last_blink_time).total_seconds()

        stats["time_since_last_blink_seconds"] = round(time_since_last_blink, 1)
        stats["consecutive_open_seconds"] = stats["time_since_last_blink_seconds"]

        return stats

    def update_settings(self, settings: Settings) -> None:
        """Update monitor settings.

        Args:
            settings: New settings.
        """
        self.settings = settings
        logger.info("Monitor settings updated")
