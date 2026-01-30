"""Full-screen overlay animations for Blink! alerts."""

from enum import Enum
from typing import Literal

from loguru import logger
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QScreen
from PyQt6.QtWidgets import QApplication, QWidget


class AnimationIntensity(str, Enum):
    """Animation intensity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnimationMode(str, Enum):
    """Animation modes."""

    BLINK = "blink"
    IRRITATION = "irritation"


class ScreenOverlay(QWidget):
    """Frameless full-screen overlay for animations."""

    _opacity = 1.0
    _red_tint = 0.0
    _shake_offset_x = 0
    _shake_offset_y = 0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )

        self._setup_geometry()
        self._setup_animations()
        self._setup_timers()

        self._current_mode: AnimationMode | None = None
        self._intensity = AnimationIntensity.MEDIUM
        self._animation_active = False
        self._blink_count = 0
        self._irritation_ended = False

        self.setStyleSheet("background: transparent;")

    def _setup_geometry(self):
        """Setup fullscreen geometry."""
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.setGeometry(geo)

    def _setup_animations(self):
        """Setup animation objects."""
        self._opacity_anim = QPropertyAnimation(self, b"opacity")
        self._opacity_anim.setDuration(300)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._tint_anim = QPropertyAnimation(self, b"redTint")
        self._tint_anim.setDuration(500)
        self._tint_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Shake animation disabled for stability in sandboxed environments
        self._shake_anim = None

    def _setup_timers(self):
        """Setup animation timers."""
        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._next_blink)

        self._irritation_timer = QTimer(self)
        self._irritation_timer.setSingleShot(True)
        self._irritation_timer.timeout.connect(self._end_irritation)

    @pyqtProperty(float)
    def opacity(self) -> float:
        """Current opacity value."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        self._opacity = value
        self.update()

    @pyqtProperty(float)
    def redTint(self) -> float:
        """Current red tint value (0.0-1.0)."""
        return self._red_tint

    @redTint.setter
    def redTint(self, value: float):
        self._red_tint = max(0.0, min(1.0, value))
        self.update()

    @pyqtProperty(object)
    def shakeOffset(self) -> tuple[int, int]:
        """Current shake offset as (x, y) tuple."""
        return (self._shake_offset_x, self._shake_offset_y)

    @shakeOffset.setter
    def shakeOffset(self, value: tuple[int, int]):
        self._shake_offset_x, self._shake_offset_y = value
        self.move(self.pos().x() - self._shake_offset_x, self.pos().y() - self._shake_offset_y)

    def paintEvent(self, event):
        """Paint overlay with current opacity and tint."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._red_tint > 0:
            red = int(255 * self._red_tint)
            color = QColor(red, 0, 0, int(80 * self._red_tint))
            painter.fillRect(self.rect(), color)

        if self._opacity < 1.0:
            dim_color = QColor(0, 0, 0, int(50 * (1.0 - self._opacity)))
            painter.fillRect(self.rect(), dim_color)

    def set_intensity(self, intensity: AnimationIntensity):
        """Set animation intensity.

        Args:
            intensity: Intensity level (low/medium/high).
        """
        self._intensity = intensity
        logger.debug(f"Animation intensity set to {intensity}")

    def play_blink(self):
        """Play blink animation."""
        if self._animation_active:
            self.stop_animation()

        self._current_mode = AnimationMode.BLINK
        self._animation_active = True
        self._blink_count = 0
        self._irritation_ended = False

        self.show()
        self._next_blink()
        logger.debug("Blink animation started")

    def play_irritation(self):
        """Play irritation animation."""
        if self._animation_active:
            self.stop_animation()

        self._current_mode = AnimationMode.IRRITATION
        self._animation_active = True
        self._irritation_ended = False

        self.show()
        self._start_irritation()
        logger.debug("Irritation animation started")

    def _next_blink(self):
        """Play next blink cycle."""
        if not self._animation_active or self._current_mode != AnimationMode.BLINK:
            return

        if self._blink_count >= self._get_blink_cycles():
            self.stop_animation()
            return

        self._blink_count += 1

        fade_out, hold, fade_in = self._get_blink_timings()
        current_opacity = self._opacity

        self._opacity_anim.stop()
        self._opacity_anim.setDuration(fade_out)
        self._opacity_anim.setStartValue(current_opacity)
        self._opacity_anim.setEndValue(self._get_blink_dim_level())
        self._opacity_anim.start()

        QTimer.singleShot(fade_out + hold, lambda: self._fade_back_in(fade_in))

    def _fade_back_in(self, duration: int):
        """Fade back to normal after blink."""
        if not self._animation_active:
            return

        self._opacity_anim.stop()
        self._opacity_anim.setDuration(duration)
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        QTimer.singleShot(duration, lambda: self._blink_timer.start(self._get_blink_interval()))

    def _start_irritation(self):
        """Start irritation animation."""
        shake_strength, tint_strength = self._get_irritation_strength()

        self._tint_anim.stop()
        self._tint_anim.setDuration(500)
        self._tint_anim.setStartValue(0.0)
        self._tint_anim.setEndValue(tint_strength)
        self._tint_anim.start()

        self._start_shake_sequence()

        duration = self._get_irritation_duration()
        self._irritation_timer.start(duration)

    def _start_shake_sequence(self):
        """Start screen shake sequence."""
        if not self._animation_active or self._current_mode != AnimationMode.IRRITATION:
            return

        if self._shake_anim is None:
            logger.debug("Shake animation skipped (not available)")
            return

        shake_strength = self._get_irritation_strength()[0]

        self._shake_anim.stop()
        self._shake_anim.setDuration(50)

        import random

        offset_x = random.randint(-shake_strength, shake_strength)
        offset_y = random.randint(-shake_strength, shake_strength)

        self._shake_anim.setStartValue((self._shake_offset_x, self._shake_offset_y))
        self._shake_anim.setEndValue((offset_x, offset_y))
        self._shake_anim.start()

    def _on_shake_step(self):
        """Handle shake animation step completion."""
        if not self._animation_active or self._current_mode != AnimationMode.IRRITATION:
            return

        if not self._irritation_ended:
            QTimer.singleShot(50, self._start_shake_sequence)

    def _end_irritation(self):
        """End irritation animation smoothly."""
        if not self._animation_active or self._current_mode != AnimationMode.IRRITATION:
            return

        self._irritation_ended = True

        self._tint_anim.stop()
        self._tint_anim.setDuration(300)
        self._tint_anim.setStartValue(self._red_tint)
        self._tint_anim.setEndValue(0.0)
        self._tint_anim.finished.connect(lambda: self.stop_animation())
        self._tint_anim.start()

    def stop_animation(self):
        """Stop current animation and hide overlay."""
        if not self._animation_active:
            return

        logger.debug("Animation stopped")

        self._animation_active = False
        self._blink_timer.stop()
        self._irritation_timer.stop()
        self._opacity_anim.stop()
        self._tint_anim.stop()
        if self._shake_anim:
            self._shake_anim.stop()

        self._opacity = 1.0
        self._red_tint = 0.0
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        self.hide()

    def _get_blink_cycles(self) -> int:
        """Get number of blink cycles based on intensity."""
        return {AnimationIntensity.LOW: 2, AnimationIntensity.MEDIUM: 3, AnimationIntensity.HIGH: 3}[
            self._intensity
        ]

    def _get_blink_timings(self) -> tuple[int, int, int]:
        """Get blink timing tuple (fade_out, hold, fade_in) in ms."""
        if self._intensity == AnimationIntensity.LOW:
            return 250, 100, 250
        elif self._intensity == AnimationIntensity.MEDIUM:
            return 200, 50, 200
        else:
            return 150, 30, 150

    def _get_blink_interval(self) -> int:
        """Get interval between blinks in ms."""
        return {AnimationIntensity.LOW: 400, AnimationIntensity.MEDIUM: 300, AnimationIntensity.HIGH: 250}[
            self._intensity
        ]

    def _get_blink_dim_level(self) -> float:
        """Get dim level for blink (0.0-1.0)."""
        return {AnimationIntensity.LOW: 0.3, AnimationIntensity.MEDIUM: 0.4, AnimationIntensity.HIGH: 0.5}[
            self._intensity
        ]

    def _get_irritation_duration(self) -> int:
        """Get total duration of irritation in ms."""
        return {
            AnimationIntensity.LOW: 800,
            AnimationIntensity.MEDIUM: 1000,
            AnimationIntensity.HIGH: 1200,
        }[self._intensity]

    def _get_irritation_strength(self) -> tuple[int, float]:
        """Get irritation strength tuple (shake_pixels, tint_level)."""
        return {
            AnimationIntensity.LOW: (3, 0.2),
            AnimationIntensity.MEDIUM: (5, 0.3),
            AnimationIntensity.HIGH: (7, 0.4),
        }[self._intensity]

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.stop_animation()
        else:
            super().keyPressEvent(event)

    @property
    def is_active(self) -> bool:
        """Check if animation is currently active."""
        return self._animation_active

    @property
    def current_mode(self) -> AnimationMode | None:
        """Get current animation mode."""
        return self._current_mode
