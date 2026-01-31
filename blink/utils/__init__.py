"""Utility modules for Blink!."""

from blink.utils.exceptions import (
    BlinkError,
    CameraError,
    ConfigError,
    VisionError,
)
from blink.utils.logger import setup_logging
from blink.utils.platform import get_app_paths
from blink.utils.validators import validate_alert_interval, validate_blink_rate

__all__ = [
    "BlinkError",
    "CameraError",
    "ConfigError",
    "VisionError",
    "setup_logging",
    "get_app_paths",
    "validate_alert_interval",
    "validate_blink_rate",
]
