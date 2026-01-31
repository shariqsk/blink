"""System tray icon for Blink!."""

from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from blink.threading.signal_bus import SignalBus


class TrayIcon(QSystemTrayIcon):
    """System tray icon with menu."""

    def __init__(self, parent: QWidget, signal_bus: SignalBus, overlay=None):
        """Initialize tray icon.

        Args:
            parent: Parent widget (main window).
            signal_bus: Shared signal bus for actions.
            overlay: ScreenOverlay instance for animation control.
        """
        super().__init__(parent)
        self.parent_window = parent
        self.overlay = overlay
        self.signal_bus = signal_bus

        self._init_icon()
        self._init_menu()
        self.show()

    def _init_icon(self) -> None:
        """Initialize tray icon (simple color block for now)."""
        # Create simple icon (would use real icon file in production)
        from PyQt6.QtGui import QPixmap, QPainter, QColor

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setBrush(QColor("#3498db"))
        painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
        painter.end()

        self.setIcon(QIcon(pixmap))
        self.setToolTip("Blink! Eye Health Monitor")

    def _init_menu(self) -> None:
        """Initialize context menu."""
        menu = QMenu()

        # Status text
        self._status_action = QAction("Status: Idle", self)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)

        menu.addSeparator()

        # Show/Hide window
        self._show_action = QAction("Show Window", self)
        self._show_action.triggered.connect(self._show_window)
        menu.addAction(self._show_action)

        self._hide_action = QAction("Hide Window", self)
        self._hide_action.triggered.connect(self._hide_window)
        menu.addAction(self._hide_action)

        menu.addSeparator()

        # Start/Stop monitoring
        self._start_action = QAction("Start Monitoring", self)
        self._start_action.triggered.connect(self._start_monitoring)
        menu.addAction(self._start_action)

        self._stop_action = QAction("Stop Monitoring", self)
        self._stop_action.triggered.connect(self._stop_monitoring)
        menu.addAction(self._stop_action)

        menu.addSeparator()

        # Pause durations
        self._pause_15_action = QAction("Pause 15 min", self)
        self._pause_15_action.triggered.connect(lambda: self.signal_bus.pause_for_duration.emit(15))
        menu.addAction(self._pause_15_action)

        self._pause_30_action = QAction("Pause 30 min", self)
        self._pause_30_action.triggered.connect(lambda: self.signal_bus.pause_for_duration.emit(30))
        menu.addAction(self._pause_30_action)

        self._pause_60_action = QAction("Pause 60 min", self)
        self._pause_60_action.triggered.connect(lambda: self.signal_bus.pause_for_duration.emit(60))
        menu.addAction(self._pause_60_action)

        self._pause_tomorrow_action = QAction("Pause until tomorrow", self)
        self._pause_tomorrow_action.triggered.connect(lambda: self.signal_bus.pause_until_tomorrow.emit())
        menu.addAction(self._pause_tomorrow_action)

        self._resume_action = QAction("Resume now", self)
        self._resume_action.triggered.connect(lambda: self.signal_bus.resume_requested.emit())
        menu.addAction(self._resume_action)

        menu.addSeparator()

        # Animation control
        if self.overlay:
            self._stop_animation_action = QAction("Stop Animation", self)
            self._stop_animation_action.triggered.connect(self._stop_animation)
            menu.addAction(self._stop_animation_action)

        self._test_animation_action = QAction("Test animation", self)
        self._test_animation_action.triggered.connect(lambda: self.signal_bus.test_animation.emit())
        menu.addAction(self._test_animation_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _show_window(self) -> None:
        """Show main window."""
        self.parent_window.show()
        self.parent_window.raise_()
        self.parent_window.activateWindow()
        logger.info("Window shown from tray")

    def _hide_window(self) -> None:
        """Hide main window."""
        self.parent_window.hide()
        logger.info("Window hidden from tray")

    def _start_monitoring(self) -> None:
        """Start monitoring via tray."""
        self.signal_bus.start_monitoring.emit()
        if hasattr(self.parent_window, "set_monitoring_state"):
            self.parent_window.set_monitoring_state(True)
        logger.info("Monitoring started from tray")

    def _stop_monitoring(self) -> None:
        """Stop monitoring via tray."""
        self.signal_bus.stop_monitoring.emit()
        if hasattr(self.parent_window, "set_monitoring_state"):
            self.parent_window.set_monitoring_state(False)
        logger.info("Monitoring stopped from tray")

    def _stop_animation(self) -> None:
        """Stop active animation via tray."""
        if self.overlay and self.overlay.is_active:
            self.overlay.stop_animation()
            logger.info("Animation stopped from tray")

    def _quit_app(self) -> None:
        """Quit application."""
        from PyQt6.QtWidgets import QApplication

        logger.info("Quit requested from tray")
        QApplication.instance().quit()

    def set_status_text(self, text: str) -> None:
        """Update status line in menu."""
        self._status_action.setText(f"Status: {text}")

    def activated(self, reason) -> None:
        """Handle tray icon activation.

        Args:
            reason: Activation reason.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.parent_window.isVisible():
                self.parent_window.hide()
            else:
                self._show_window()
