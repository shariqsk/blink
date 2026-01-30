"""Alert engine for triggering animations."""

from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from blink.config.settings import Settings


class AlertEngine(QObject):
    """Manages alert triggering logic."""

    alert_triggered = pyqtSignal()  # Signal when alert should show
    alert_cleared = pyqtSignal()  # Signal when alert should hide

    def __init__(self, settings: Settings):
        """Initialize alert engine.

        Args:
            settings: Application settings.
        """
        super().__init__()
        self.settings = settings
        self._alert_active = False
        self._check_interval_seconds = 5

    def start(self) -> None:
        """Start alert engine."""
        self._alert_active = False
        logger.info("Alert engine started")

    def stop(self) -> None:
        """Stop alert engine."""
        self._alert_active = False
        self.alert_cleared.emit()
        logger.info("Alert engine stopped")

    def check_condition(self, should_alert: bool) -> None:
        """Check if alert should be triggered.

        Args:
            should_alert: Whether blink condition warrants an alert.
        """
        if should_alert and not self._alert_active:
            self._alert_active = True
            logger.info("Alert triggered")
            self.alert_triggered.emit()
        elif not should_alert and self._alert_active:
            self._alert_active = False
            logger.info("Alert cleared")
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
