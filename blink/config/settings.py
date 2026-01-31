"""Settings data model for Blink!."""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AlertMode(str, Enum):
    """Alert animation modes."""

    BLINK = "blink"
    IRRITATION = "irritation"
    POPUP = "popup"


class AnimationIntensity(str, Enum):
    """Animation intensity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CameraResolution(str, Enum):
    """Camera resolution presets."""

    ECO = "320x240"
    DEFAULT = "640x480"


class TriggerLogic(str, Enum):
    """How triggers are evaluated."""

    NO_BLINK = "no_blink"
    LOW_RATE = "low_rate"
    BOTH = "both"


class Settings(BaseModel):
    """Application settings model."""

    # Alert settings
    alert_interval_minutes: int = Field(default=15, ge=1, le=60)
    min_blinks_per_minute: int = Field(default=15, ge=5, le=30)
    alert_mode: AlertMode = Field(default=AlertMode.BLINK)
    animation_duration_ms: int = Field(default=1000, ge=500, le=5000)
    animation_intensity: AnimationIntensity = Field(default=AnimationIntensity.MEDIUM)

    # Camera settings
    camera_resolution: CameraResolution = Field(default=CameraResolution.DEFAULT)
    target_fps: int = Field(default=15, ge=5, le=30)
    camera_enabled: bool = Field(default=True)
    camera_id: int = Field(default=0, ge=0, le=9)

    # Eye detection settings
    ear_threshold: float = Field(default=0.21, ge=0.1, le=0.4)
    auto_calibrate: bool = Field(default=True)

    # Blink detection settings
    blink_consecutive_frames: int = Field(default=2, ge=1, le=5)
    min_blink_duration_ms: int = Field(default=50, ge=20, le=200)
    max_blink_duration_ms: int = Field(default=500, ge=200, le=1000)

    # Trigger logic
    trigger_logic: TriggerLogic = Field(default=TriggerLogic.BOTH)
    no_blink_seconds: int = Field(default=20, ge=5, le=120)
    low_rate_threshold: int = Field(default=12, ge=5, le=30)
    low_rate_duration_minutes: int = Field(default=3, ge=1, le=15)

    # Quiet hours
    quiet_hours_enabled: bool = Field(default=False)
    quiet_hours_start: str = Field(default="23:00")
    quiet_hours_end: str = Field(default="07:00")

    # Aggregated stats & diagnostics
    collect_aggregated_stats: bool = Field(default=True)

    # UI settings
    start_minimized: bool = Field(default=False)
    show_tray_icon: bool = Field(default=True)
    enable_notifications: bool = Field(default=True)
    show_status_panel: bool = Field(default=True)
    hotkey_start_stop: str = Field(default="Ctrl+Shift+B")
    hotkey_pause: str = Field(default="Ctrl+Shift+P")
    hotkey_test: str = Field(default="Ctrl+Shift+T")

    # Privacy settings
    privacy_acknowledged: bool = Field(default=False)
    show_privacy_notice: bool = Field(default=True)

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @field_validator("animation_duration_ms")
    @classmethod
    def validate_animation_duration(cls, v: int) -> int:
        """Validate animation duration."""
        if v < 500 or v > 5000:
            raise ValueError("Animation duration must be between 500 and 5000ms")
        return v

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_quiet_hour_format(cls, v: str) -> str:
        """Ensure quiet hour strings are HH:MM."""
        from datetime import datetime

        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as exc:
            raise ValueError("Quiet hours must use HH:MM 24h format") from exc
        return v

    @field_validator("low_rate_duration_minutes")
    @classmethod
    def validate_low_rate_duration(cls, v: int) -> int:
        """Validate low rate duration."""
        if v < 1 or v > 15:
            raise ValueError("Low-rate duration must be between 1 and 15 minutes")
        return v

    @field_validator("hotkey_start_stop", "hotkey_pause", "hotkey_test")
    @classmethod
    def validate_hotkey_format(cls, v: str) -> str:
        """Basic validation for hotkey strings."""
        if not v or "+" not in v:
            raise ValueError("Hotkeys must include a modifier, e.g., Ctrl+Shift+B")
        return v

    def get_resolution_tuple(self) -> tuple[int, int]:
        """Get camera resolution as tuple (width, height).

        Returns:
            Tuple of (width, height).
        """
        res_map = {
            CameraResolution.ECO: (320, 240),
            CameraResolution.DEFAULT: (640, 480),
        }
        return res_map[self.camera_resolution]

    def is_quiet_hours(self, now=None) -> bool:
        """Check if current time falls within quiet hours."""
        from datetime import datetime, time as dtime

        if not self.quiet_hours_enabled:
            return False

        now = now or datetime.now()
        start_h, start_m = map(int, self.quiet_hours_start.split(":"))
        end_h, end_m = map(int, self.quiet_hours_end.split(":"))

        start_t = dtime(hour=start_h, minute=start_m)
        end_t = dtime(hour=end_h, minute=end_m)
        current_t = now.time()

        if start_t < end_t:
            return start_t <= current_t < end_t

        # Overnight window (e.g., 23:00–07:00)
        return current_t >= start_t or current_t < end_t
