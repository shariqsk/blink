"""Main application window for Blink!."""

from loguru import logger

from blink.config.settings import Settings
from blink.ui.settings_dialog import SettingsDialog
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, settings: Settings):
        """Initialize main window.

        Args:
            settings: Application settings.
        """
        super().__init__()
        self.settings = settings
        self._monitoring = False

        # Statistics update timer
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_statistics_display)

        self._init_ui()
        self._update_camera_status()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("Blink! - Eye Health Monitor")
        self.setMinimumSize(500, 400)
        self.resize(600, 450)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QLabel("Blink!")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Eye Health Monitor")
        subtitle.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # Camera status
        self._status_label = QLabel("Camera: Inactive")
        self._status_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #7f8c8d;"
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Statistics
        self._stats_label = QLabel(
            "Blinks/Min: -- | Total: -- | Session: --:--"
        )
        self._stats_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #34495e;"
        )
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._stats_label)

        layout.addSpacing(30)

        # Control buttons
        button_layout = QVBoxLayout()

        self._start_button = QPushButton("Start Monitoring")
        self._start_button.setStyleSheet(
            "font-size: 14px; padding: 12px; background-color: #27ae60; "
            "color: white; border-radius: 5px; font-weight: bold;"
        )
        self._start_button.clicked.connect(self._toggle_monitoring)
        button_layout.addWidget(self._start_button)

        self._settings_button = QPushButton("Settings")
        self._settings_button.setStyleSheet(
            "font-size: 14px; padding: 12px; background-color: #3498db; "
            "color: white; border-radius: 5px;"
        )
        self._settings_button.clicked.connect(self._open_settings)
        button_layout.addWidget(self._settings_button)

        layout.addLayout(button_layout)
        layout.addStretch()

    def _toggle_monitoring(self) -> None:
        """Toggle monitoring state."""
        self._monitoring = not self._monitoring

        if self._monitoring:
            self._start_button.setText("Stop Monitoring")
            self._start_button.setStyleSheet(
                "font-size: 14px; padding: 12px; background-color: #e74c3c; "
                "color: white; border-radius: 5px; font-weight: bold;"
            )
            self._stats_timer.start(1000)
            logger.info("Monitoring started from UI")
        else:
            self._start_button.setText("Start Monitoring")
            self._start_button.setStyleSheet(
                "font-size: 14px; padding: 12px; background-color: #27ae60; "
                "color: white; border-radius: 5px; font-weight: bold;"
            )
            self._stats_timer.stop()
            logger.info("Monitoring stopped from UI")

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            logger.info("Settings updated from dialog")

    def _update_statistics_display(self, *args) -> None:
        """Update statistics display (called with args for signal connection)."""
        if not self._monitoring:
            return

        # Display fake statistics for now
        import random

        blinks_min = round(random.uniform(12.0, 18.0), 1)
        total = random.randint(100, 500)
        mins = random.randint(5, 30)
        secs = random.randint(0, 59)

        self._stats_label.setText(
            f"Blinks/Min: {blinks_min} | Total: {total} | Session: {mins:02d}:{secs:02d}"
        )

    def _update_camera_status(self) -> None:
        """Update camera status display."""
        # Camera is not wired yet, always show inactive
        self._status_label.setText("Camera: Inactive (Not Configured)")
        self._status_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #7f8c8d;"
        )

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        logger.info("Main window closed (will continue running in tray)")
        self.hide()
        event.ignore()

    def update_settings(self, settings: Settings) -> None:
        """Update settings.

        Args:
            settings: New settings.
        """
        self.settings = settings

    @pyqtSlot(bool)
    def set_monitoring_state(self, monitoring: bool) -> None:
        """Set monitoring state from external source.

        Args:
            monitoring: Whether monitoring is active.
        """
        if self._monitoring != monitoring:
            self._toggle_monitoring()

    @property
    def is_monitoring(self) -> bool:
        """Get current monitoring state."""
        return self._monitoring
