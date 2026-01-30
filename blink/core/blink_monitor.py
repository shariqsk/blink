"""Blink monitoring logic and rules engine."""

from loguru import logger

from blink.config.settings import Settings
from blink.core.statistics import BlinkStatistics


class BlinkMonitor:
    """Monitors blink events and triggers alerts based on rules."""

    def __init__(self, settings: Settings):
        """Initialize blink monitor.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.stats = BlinkStatistics()
        self._last_blink_time = 0.0
        self._is_running = False
        self._should_alert = False

    def start(self) -> None:
        """Start monitoring."""
        self._is_running = True
        self.stats.reset()
        self._should_alert = False
        logger.info("Blink monitor started")

    def stop(self) -> None:
        """Stop monitoring."""
        self._is_running = False
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
        self._should_alert = False
        logger.debug(f"Blink recorded. Rate: {self.stats.blinks_per_minute:.1f}/min")

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

        current_rate = self.stats.blinks_per_minute
        threshold = self.settings.min_blinks_per_minute

        # Check if blink rate is below threshold
        should_alert = current_rate < threshold

        if should_alert and not self._should_alert:
            logger.warning(f"Low blink rate detected: {current_rate:.1f}/min < {threshold}/min")
            self._should_alert = True

        return should_alert

    def get_statistics(self) -> dict:
        """Get current statistics.

        Returns:
            Statistics dictionary.
        """
        return self.stats.get_summary()

    def update_settings(self, settings: Settings) -> None:
        """Update monitor settings.

        Args:
            settings: New settings.
        """
        self.settings = settings
        logger.info("Monitor settings updated")
