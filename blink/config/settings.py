"""Settings data model for Blink!."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AlertMode(str, Enum):
    """Alert animation modes."""

    BLINK = "blink"
    IRRITATION = "irritation"


class CameraResolution(str, Enum):
    """Camera resolution presets."""

    ECO = "320x240"
    DEFAULT = "640x480"


class Settings(BaseModel):
    """Application settings model."""

    # Alert settings
    alert_interval_minutes: int = Field(default=15, ge=1, le=60)
    min_blinks_per_minute: int = Field(default=15, ge=5, le=30)
    alert_mode: AlertMode = Field(default=AlertMode.BLINK)
    animation_duration_ms: int = Field(default=1000, ge=500, le=5000)

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

    # UI settings
    start_minimized: bool = Field(default=False)
    show_tray_icon: bool = Field(default=True)
    enable_notifications: bool = Field(default=True)
    show_status_panel: bool = Field(default=True)

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
