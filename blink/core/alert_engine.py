"""Alert engine for triggering animations."""

from datetime import datetime, timedelta
from typing import Optional

from blink.config.settings import Settings
from loguru import logger
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class AlertEngine(QObject):
    """Manages alert triggering logic."""

    alert_triggered = pyqtSignal()
    alert_cleared = pyqtSignal()
    animation_requested = pyqtSignal(str)

    def __init__(self, settings: Settings):
        """Initialize alert engine.

        Args:
            settings: Application settings.
        """
        super().__init__()
        self.settings = settings
        self._alert_active = False
        self._last_alert_time: Optional[datetime] = None
        self._check_interval_seconds = 5

        # Timer for periodic checks
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._periodic_check)
        self._check_timer.setInterval(self._check_interval_seconds * 1000)

    def start(self) -> None:
        """Start alert engine."""
        self._alert_active = False
        self._last_alert_time = None
        self._check_timer.start()
        logger.info("Alert engine started")

    def stop(self) -> None:
        """Stop alert engine."""
        self._check_timer.stop()
        self._alert_active = False
        self.alert_cleared.emit()
        logger.info("Alert engine stopped")

    def check_condition(self, should_alert: bool) -> None:
        """Check if alert should be triggered.

        Args:
            should_alert: Whether blink condition warrants an alert.
        """
        # Check alert cooldown
        if self._last_alert_time:
            time_since_alert = (datetime.now() - self._last_alert_time).total_seconds()
            cooldown = self.settings.alert_interval_minutes * 60

            if time_since_alert < cooldown:
                logger.debug(f"In alert cooldown: {time_since_alert:.0f}s < {cooldown}s")
                return

        if should_alert and not self._alert_active:
            self._alert_active = True
            self._last_alert_time = datetime.now()
            logger.info("Alert triggered")
            self.alert_triggered.emit()
            self.animation_requested.emit(self.settings.alert_mode.value)
        elif not should_alert and self._alert_active:
            self._alert_active = False
            logger.info("Alert cleared")
            self.alert_cleared.emit()

    def _periodic_check(self) -> None:
        """Periodic check (can be extended for additional alert logic)."""
        pass

    def trigger_alert(self) -> None:
        """Manually trigger an alert."""
        if not self._alert_active:
            self._alert_active = True
            self._last_alert_time = datetime.now()
            logger.info("Manual alert triggered")
            self.alert_triggered.emit()

    def clear_alert(self) -> None:
        """Manually clear an active alert."""
        if self._alert_active:
            self._alert_active = False
            logger.info("Manual alert cleared")
            self.alert_cleared.emit()

    @property
    def is_alert_active(self) -> bool:
        """Check if alert is currently active."""
        return self._alert_active

    def update_settings(self, settings: Settings) -> None:
        """Update engine settings.

        Args:
            settings: New settings.
        """
        self.settings = settings
        logger.info("Alert engine settings updated")
