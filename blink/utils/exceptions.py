"""Custom exception classes for Blink!."""


class BlinkError(Exception):
    """Base exception for Blink! application."""

    pass


class CameraError(BlinkError):
    """Exception raised for camera-related errors."""

    pass


class ConfigError(BlinkError):
    """Exception raised for configuration-related errors."""

    pass


class VisionError(BlinkError):
    """Exception raised for vision processing errors."""

    pass
