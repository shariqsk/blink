"""Input validation utilities for Blink!."""


def validate_alert_interval(minutes: int) -> int:
    """Validate alert interval in minutes.

    Args:
        minutes: Alert interval in minutes.

    Returns:
        Validated and clamped interval.

    Raises:
        ValueError: If interval is out of bounds.
    """
    if minutes < 1:
        raise ValueError("Alert interval must be at least 1 minute")
    if minutes > 60:
        raise ValueError("Alert interval cannot exceed 60 minutes")
    return minutes


def validate_blink_rate(blinks_per_minute: int) -> int:
    """Validate blink rate threshold.

    Args:
        blinks_per_minute: Minimum blinks per minute.

    Returns:
        Validated and clamped blink rate.

    Raises:
        ValueError: If blink rate is out of bounds.
    """
    if blinks_per_minute < 5:
        raise ValueError("Blink rate must be at least 5 blinks per minute")
    if blinks_per_minute > 30:
        raise ValueError("Blink rate cannot exceed 30 blinks per minute")
    return blinks_per_minute


def validate_resolution(resolution: str) -> str:
    """Validate camera resolution string.

    Args:
        resolution: Resolution string like "640x480".

    Returns:
        Validated resolution string.

    Raises:
        ValueError: If resolution is invalid.
    """
    valid = {"320x240", "640x480"}
    if resolution not in valid:
        raise ValueError(f"Invalid resolution. Must be one of: {', '.join(valid)}")
    return resolution


def validate_alert_mode(mode: str) -> str:
    """Validate alert mode.

    Args:
        mode: Alert mode string.

    Returns:
        Validated mode string.

    Raises:
        ValueError: If mode is invalid.
    """
    valid = {"blink", "irritation"}
    if mode not in valid:
        raise ValueError(f"Invalid mode. Must be one of: {', '.join(valid)}")
    return mode
