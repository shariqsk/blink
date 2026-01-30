"""Default settings for Blink!."""

from blink.config.settings import AlertMode, CameraResolution, Settings

DEFAULT_SETTINGS = Settings(
    # Alert settings
    alert_interval_minutes=15,
    min_blinks_per_minute=15,
    alert_mode=AlertMode.BLINK,
    animation_duration_ms=1000,
    # Camera settings
    camera_resolution=CameraResolution.DEFAULT,
    target_fps=15,
    camera_enabled=True,
    # UI settings
    start_minimized=False,
    show_tray_icon=True,
    enable_notifications=True,
    # Privacy settings
    privacy_acknowledged=False,
    show_privacy_notice=True,
)
