"""Default settings for Blink!."""

from blink.config.settings import (
    AlertMode,
    AnimationIntensity,
    CameraResolution,
    Settings,
    TriggerLogic,
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
    # Trigger logic
    trigger_logic=TriggerLogic.BOTH,
    no_blink_seconds=20,
    low_rate_threshold=12,
    low_rate_duration_minutes=3,
    # Quiet hours
    quiet_hours_enabled=False,
    quiet_hours_start="23:00",
    quiet_hours_end="07:00",
    # Aggregated stats
    collect_aggregated_stats=True,
    # UI settings
    start_minimized=False,
    show_tray_icon=True,
    enable_notifications=True,
    show_status_panel=True,
    hotkey_start_stop="Ctrl+Shift+B",
    hotkey_pause="Ctrl+Shift+P",
    hotkey_test="Ctrl+Shift+T",
    # Privacy settings
    privacy_acknowledged=False,
    show_privacy_notice=True,
)
