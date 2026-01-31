"""Full-screen overlay animations for Blink! alerts."""

from enum import Enum
from typing import Literal

from loguru import logger
from PyQt6.QtCore import QPointF, QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QScreen,
)
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
    POPUP = "popup"


class ScreenOverlay(QWidget):
    """Frameless full-screen overlay for animations."""

    _opacity = 1.0
    _red_tint = 0.0
    _blink_level = 0.0
    _pulse_level = 0.0
    _card_only = False
    _shake_offset_x = 0
    _shake_offset_y = 0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
        self._card_only = False

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

        self._blink_anim = QPropertyAnimation(self, b"blinkLevel")
        self._blink_anim.setDuration(200)
        self._blink_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._pulse_anim = QPropertyAnimation(self, b"pulseLevel")
        self._pulse_anim.setDuration(1200)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

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

    @pyqtProperty(float)
    def blinkLevel(self) -> float:
        """How closed the stylized eyelid is (0 open, 1 closed)."""
        return self._blink_level

    @blinkLevel.setter
    def blinkLevel(self, value: float):
        self._blink_level = max(0.0, min(1.0, value))
        self.update()

    @pyqtProperty(float)
    def pulseLevel(self) -> float:
        """Soft breathing/pulse intensity (0-1)."""
        return self._pulse_level

    @pulseLevel.setter
    def pulseLevel(self, value: float):
        self._pulse_level = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        """Paint overlay with current opacity and tint."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._animation_active:
            return

        width = self.width()
        height = self.height()

        show_backdrop = not self._card_only

        # Gentle vignette that never blocks content
        backdrop_strength = max(0.0, 1.0 - self._opacity)
        if show_backdrop and backdrop_strength > 0:
            center_point = self.rect().center()
            vignette = QRadialGradient(QPointF(center_point), max(width, height) * 0.75)
            vignette.setColorAt(0.0, QColor(12, 16, 30, int(80 * backdrop_strength)))
            vignette.setColorAt(1.0, QColor(12, 16, 30, 0))
            painter.fillRect(self.rect(), vignette)

        # Soft red edge glow for irritation mode only; fades gently
        if show_backdrop and self._current_mode == AnimationMode.IRRITATION and self._red_tint > 0:
            tint_alpha = int(140 * self._red_tint)
            edge = QLinearGradient(0, 0, width, 0)
            edge.setColorAt(0.0, QColor(255, 82, 82, 0))
            edge.setColorAt(0.5, QColor(255, 82, 82, tint_alpha))
            edge.setColorAt(1.0, QColor(255, 82, 82, 0))
            painter.fillRect(self.rect(), edge)

        # Card-style prompt near the top of the screen
        card_width = min(int(width * 0.48), 520)
        card_height = 128
        card_rect = QRect(int((width - card_width) / 2), int(height * 0.08), card_width, card_height)

        card_bg = QLinearGradient(
            QPointF(card_rect.left(), card_rect.top()),
            QPointF(card_rect.left(), card_rect.bottom()),
        )
        # Slightly brighter for visibility
        card_bg.setColorAt(0.0, QColor(18, 27, 52, 240))
        card_bg.setColorAt(1.0, QColor(20, 30, 58, 225))

        painter.setPen(QColor(255, 255, 255, 35))
        painter.setBrush(card_bg)
        painter.drawRoundedRect(card_rect, 16, 16)

        # Eye graphic on the left
        inset = 18
        eye_center_x = card_rect.left() + 90
        eye_center_y = card_rect.center().y()
        eye_width = 150
        eye_height = 62

        eye_rect = QRect(
            int(eye_center_x - eye_width / 2),
            int(eye_center_y - eye_height / 2),
            eye_width,
            eye_height,
        )

        painter.setPen(QPen(QColor(180, 208, 255, 210), 2.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(eye_rect)

        # Iris
        iris_radius = int((eye_height * 0.30) * (0.8 + 0.2 * self._pulse_level))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(125, 211, 252, 230))
        painter.drawEllipse(
            eye_rect.center().x() - iris_radius,
            eye_rect.center().y() - iris_radius,
            iris_radius * 2,
            iris_radius * 2,
        )

        # Eyelid animation (curved lid following eye arc)
        if self._blink_level > 0:
            lid_height = eye_height * self._blink_level
            lid_top = eye_rect.top()
            lid_curve_y = lid_top - eye_height * 0.32
            lid_close_y = lid_top + lid_height

            lid_path = QPainterPath()
            # Upper arc following the eye ellipse
            lid_path.moveTo(eye_rect.left() + 6, lid_top)
            lid_path.quadTo(eye_rect.center().x(), lid_curve_y, eye_rect.right() - 6, lid_top)
            # Closing sweep down to the closing position
            lid_path.lineTo(eye_rect.right() - 6, lid_close_y)
            lid_path.quadTo(eye_rect.center().x(), lid_curve_y + eye_height * 0.45, eye_rect.left() + 6, lid_close_y)
            lid_path.closeSubpath()

            lid_color = QColor(25, 35, 54, 235)
            painter.setBrush(lid_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(lid_path)

        # Glow ring pulse
        ring_alpha = int(120 * (0.2 + 0.8 * (1 - self._blink_level)) * (0.4 + 0.6 * self._pulse_level))
        painter.setPen(QPen(QColor(94, 234, 212, ring_alpha), 3.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(eye_rect.adjusted(-6, -6, 6, 6))

        # Text block on the right
        text_left = card_rect.left() + eye_width + inset
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)

        body_font = QFont()
        body_font.setPointSize(10)

        painter.setPen(QColor(255, 255, 255, 235))
        painter.setFont(title_font)

        title = "Blink break"
        subtitle = "Close both eyes twice and stare at something 20 feet away."
        if self._current_mode == AnimationMode.IRRITATION:
            title = "Eyes need a pause"
            subtitle = "Look away 20 seconds and blink a few times to refresh."
        elif self._current_mode == AnimationMode.POPUP:
            title = "Quick blink"
            subtitle = "Blink 2–3 times now to keep your eyes comfortable."

        painter.drawText(
            QRect(text_left, card_rect.top() + inset + 2, card_rect.width() - eye_width - inset * 2, 26),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        painter.setPen(QColor(226, 232, 240, 210))
        painter.setFont(body_font)
        painter.drawText(
            QRect(
                text_left,
                card_rect.top() + inset + 28,
                card_rect.width() - eye_width - inset * 2,
                card_rect.height() - inset * 2 - 28,
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            subtitle,
        )

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
        self._card_only = False

        self.show()
        self._pulse_anim.stop()
        self._pulse_anim.start()
        self._next_blink()
        logger.debug("Blink animation started")

    def play_irritation(self):
        """Play irritation animation."""
        if self._animation_active:
            self.stop_animation()

        self._current_mode = AnimationMode.IRRITATION
        self._animation_active = True
        self._irritation_ended = False
        self._card_only = False

        self.show()
        self._pulse_anim.stop()
        self._pulse_anim.start()
        self._start_irritation()
        logger.debug("Irritation animation started")

    def play_popup(self):
        """Play card-only popup blink reminder (no dimming)."""
        if self._animation_active:
            self.stop_animation()

        self._current_mode = AnimationMode.POPUP
        self._animation_active = True
        self._blink_count = 0
        self._card_only = True
        self._irritation_ended = False

        self._opacity = 1.0  # ensure no backdrop dim
        self.show()
        self._pulse_anim.stop()
        self._pulse_anim.start()
        self._next_blink()
        logger.debug("Popup animation started")

    def _next_blink(self):
        """Play next blink cycle."""
        if not self._animation_active or self._current_mode not in (AnimationMode.BLINK, AnimationMode.POPUP):
            return

        if self._blink_count >= self._get_blink_cycles():
            self.stop_animation()
            return

        self._blink_count += 1

        fade_out, hold, fade_in = self._get_blink_timings()

        do_dim = not self._card_only
        if do_dim:
            self._opacity_anim.stop()
            self._opacity_anim.setDuration(fade_out)
            self._opacity_anim.setStartValue(self._opacity)
            self._opacity_anim.setEndValue(self._get_blink_dim_level())
            self._opacity_anim.start()
        else:
            self._opacity = 1.0

        self._blink_anim.stop()
        self._blink_anim.setDuration(fade_out)
        self._blink_anim.setStartValue(self._blink_level)
        self._blink_anim.setEndValue(1.0)
        self._blink_anim.start()

        QTimer.singleShot(fade_out + hold, lambda: self._start_blink_open(fade_in))

    def _start_blink_open(self, duration: int):
        """Re-open eyelid and schedule next gentle blink."""
        if not self._animation_active:
            return

        if not self._card_only:
            self._opacity_anim.stop()
            self._opacity_anim.setDuration(duration)
            self._opacity_anim.setStartValue(self._opacity)
            self._opacity_anim.setEndValue(1.0)
            self._opacity_anim.start()
        else:
            self._opacity = 1.0

        self._blink_anim.stop()
        self._blink_anim.setDuration(duration)
        self._blink_anim.setStartValue(self._blink_level)
        self._blink_anim.setEndValue(0.0)
        self._blink_anim.start()

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
        self._blink_anim.stop()
        self._pulse_anim.stop()
        if self._shake_anim:
            self._shake_anim.stop()

        self._opacity = 1.0
        self._red_tint = 0.0
        self._blink_level = 0.0
        self._pulse_level = 0.0
        self._card_only = False
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        self.hide()

    def _get_blink_cycles(self) -> int:
        """Get number of blink cycles based on intensity."""
        base = {AnimationIntensity.LOW: 3, AnimationIntensity.MEDIUM: 4, AnimationIntensity.HIGH: 5}[
            self._intensity
        ]
        # Popup stays brief by design
        if self._card_only:
            return 3
        return base

    def _get_blink_timings(self) -> tuple[int, int, int]:
        """Get blink timing tuple (fade_out, hold, fade_in) in ms."""
        if self._card_only:
            return 160, 80, 160
        if self._intensity == AnimationIntensity.LOW:
            return 200, 90, 200
        elif self._intensity == AnimationIntensity.MEDIUM:
            return 180, 90, 180
        else:
            return 150, 80, 150

    def _get_blink_interval(self) -> int:
        """Get interval between blinks in ms."""
        return {AnimationIntensity.LOW: 400, AnimationIntensity.MEDIUM: 300, AnimationIntensity.HIGH: 250}[
            self._intensity
        ]

    def _get_blink_dim_level(self) -> float:
        """Get dim level for blink (0.0-1.0)."""
        # Keep screen visible; gentle dim instead of black flash
        if self._card_only:
            return 1.0
        return {
            AnimationIntensity.LOW: 0.86,
            AnimationIntensity.MEDIUM: 0.82,
            AnimationIntensity.HIGH: 0.78,
        }[self._intensity]

    def _get_irritation_duration(self) -> int:
        """Get total duration of irritation in ms."""
        return {
            AnimationIntensity.LOW: 1400,
            AnimationIntensity.MEDIUM: 1700,
            AnimationIntensity.HIGH: 2000,
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
