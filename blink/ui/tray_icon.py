"""System tray icon for Blink!."""

from loguru import logger

from PyQt6.QtGui import QAction, QIcon, QPalette
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


class TrayIcon(QSystemTrayIcon):
    """System tray icon with menu."""

    def __init__(self, parent: QWidget):
        """Initialize tray icon.

        Args:
            parent: Parent widget (main window).
        """
        super().__init__(parent)
        self.parent_window = parent

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
        if hasattr(self.parent_window, "set_monitoring_state"):
            self.parent_window.set_monitoring_state(True)
        logger.info("Monitoring started from tray")

    def _stop_monitoring(self) -> None:
        """Stop monitoring via tray."""
        if hasattr(self.parent_window, "set_monitoring_state"):
            self.parent_window.set_monitoring_state(False)
        logger.info("Monitoring stopped from tray")

    def _quit_app(self) -> None:
        """Quit application."""
        from PyQt6.QtWidgets import QApplication

        logger.info("Quit requested from tray")
        QApplication.instance().quit()

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
