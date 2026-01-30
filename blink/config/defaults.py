"""Default settings for Blink!."""

from blink.config.settings import (
    AlertMode,
    AnimationIntensity,
    CameraResolution,
    Settings,
)

DEFAULT_SETTINGS = Settings(
    # Alert settings
    alert_interval_minutes=15,
    min_blinks_per_minute=15,
    alert_mode=AlertMode.BLINK,
    animation_duration_ms=1000,
    animation_intensity=AnimationIntensity.MEDIUM,
    # Camera settings
    camera_resolution=CameraResolution.DEFAULT,
    target_fps=15,
    camera_enabled=True,
    camera_id=0,
    # Eye detection settings
    ear_threshold=0.21,
    auto_calibrate=True,
    # Blink detection settings
    blink_consecutive_frames=2,
    min_blink_duration_ms=50,
    max_blink_duration_ms=500,
    # UI settings
    start_minimized=False,
    show_tray_icon=True,
    enable_notifications=True,
    show_status_panel=True,
    # Privacy settings
    privacy_acknowledged=False,
    show_privacy_notice=True,
)
