"""Centralized signal routing for Blink!."""

from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """Central signal bus for inter-component communication."""

    # Vision signals
    blink_detected = pyqtSignal()
    statistics_updated = pyqtSignal(dict)
    face_detected = pyqtSignal(bool)
    camera_status_changed = pyqtSignal(bool)

    # Alert signals
    alert_triggered = pyqtSignal()
    alert_cleared = pyqtSignal()
    animation_requested = pyqtSignal(str)

    # Control signals
    start_monitoring = pyqtSignal()
    stop_monitoring = pyqtSignal()
    settings_changed = pyqtSignal(object)

    # Error signals
    error_occurred = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize QObject base."""
        super().__init__()
