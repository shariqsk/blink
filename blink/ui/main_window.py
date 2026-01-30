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
    QProgressBar,
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
        self._camera_active = False
        self._face_detected = False
        self._calibrating = False

        # Current metrics
        self._current_ear = 0.0
        self._blinks_per_minute = 0.0
        self._blinks_last_minute = 0
        self._time_since_last_blink = 0.0

        # Statistics update timer
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_statistics_display)

        self._init_ui()
        self._update_status_display()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("Blink! - Eye Health Monitor")
        self.setMinimumSize(600, 550)
        self.resize(650, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(15)
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

        layout.addSpacing(20)

        # Status panel
        self._create_status_panel(layout)

        layout.addSpacing(15)

        # Control buttons
        button_layout = QVBoxLayout()

        self._start_button = QPushButton("Start Monitoring")
        self._start_button.setStyleSheet(
            "font-size: 14px; padding: 12px; background-color: #27ae60; "
            "color: white; border-radius: 5px; font-weight: bold;"
        )
        self._start_button.clicked.connect(self._toggle_monitoring)
        button_layout.addWidget(self._start_button)

        self._calibrate_button = QPushButton("Calibrate Threshold")
        self._calibrate_button.setStyleSheet(
            "font-size: 14px; padding: 12px; background-color: #f39c12; "
            "color: white; border-radius: 5px;"
        )
        self._calibrate_button.clicked.connect(self._start_calibration)
        self._calibrate_button.setEnabled(False)
        button_layout.addWidget(self._calibrate_button)

        # Calibration progress
        self._calibration_progress = QProgressBar()
        self._calibration_progress.setRange(0, 100)
        self._calibration_progress.setValue(0)
        self._calibration_progress.setVisible(False)
        self._calibration_progress.setStyleSheet(
            "QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; } "
            "QProgressBar::chunk { background-color: #f39c12; }"
        )
        layout.addWidget(self._calibration_progress)

        layout.addSpacing(10)

        self._settings_button = QPushButton("Settings")
        self._settings_button.setStyleSheet(
            "font-size: 14px; padding: 12px; background-color: #3498db; "
            "color: white; border-radius: 5px;"
        )
        self._settings_button.clicked.connect(self._open_settings)
        button_layout.addWidget(self._settings_button)

        layout.addLayout(button_layout)
        layout.addStretch()

    def _create_status_panel(self, layout: QVBoxLayout) -> None:
        """Create status information panel.

        Args:
            layout: Layout to add panel to.
        """
        # Camera status
        self._camera_status_label = QLabel("Camera: Inactive")
        self._camera_status_label.setStyleSheet(
            "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #7f8c8d; font-weight: bold;"
        )
        self._camera_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._camera_status_label)

        # Face status
        self._face_status_label = QLabel("Face: Not detected")
        self._face_status_label.setStyleSheet(
            "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #7f8c8d;"
        )
        self._face_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._face_status_label)

        # Current EAR
        self._ear_label = QLabel("Current EAR: --")
        self._ear_label.setStyleSheet(
            "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #34495e;"
        )
        self._ear_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ear_label)

        # Blink statistics
        self._stats_label = QLabel(
            "Blinks/Min: -- | Last Min: -- | Since Last Blink: --s"
        )
        self._stats_label.setStyleSheet(
            "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
            "border-radius: 5px; color: #34495e;"
        )
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._stats_label)

    def _toggle_monitoring(self) -> None:
        """Toggle monitoring state."""
        self._monitoring = not self._monitoring

        if self._monitoring:
            self._start_button.setText("Stop Monitoring")
            self._start_button.setStyleSheet(
                "font-size: 14px; padding: 12px; background-color: #e74c3c; "
                "color: white; border-radius: 5px; font-weight: bold;"
            )
            self._calibrate_button.setEnabled(True)
            self._stats_timer.start(1000)
            logger.info("Monitoring started from UI")
        else:
            self._start_button.setText("Start Monitoring")
            self._start_button.setStyleSheet(
                "font-size: 14px; padding: 12px; background-color: #27ae60; "
                "color: white; border-radius: 5px; font-weight: bold;"
            )
            self._calibrate_button.setEnabled(False)
            self._calibration_progress.setVisible(False)
            self._calibrating = False
            self._stats_timer.stop()
            self._reset_status()
            logger.info("Monitoring stopped from UI")

    def _start_calibration(self) -> None:
        """Start calibration process."""
        self._calibrating = True
        self._calibration_progress.setValue(0)
        self._calibration_progress.setVisible(True)
        self._calibrate_button.setEnabled(False)
        self._start_button.setEnabled(False)

        logger.info("Calibration started from UI")

        # Signal to start calibration (would connect to vision worker in app.py)
        # For now, simulate calibration completion after 5 seconds
        QTimer.singleShot(5000, self._calibration_complete)

    def _calibration_complete(self) -> None:
        """Handle calibration completion."""
        self._calibrating = False
        self._calibration_progress.setVisible(False)
        self._calibrate_button.setEnabled(True)
        self._start_button.setEnabled(True)

        logger.info("Calibration complete")

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            logger.info("Settings updated from dialog")

    def _reset_status(self) -> None:
        """Reset status displays."""
        self._camera_active = False
        self._face_detected = False
        self._current_ear = 0.0
        self._blinks_per_minute = 0.0
        self._blinks_last_minute = 0
        self._time_since_last_blink = 0.0
        self._update_status_display()

    def _update_status_display(self) -> None:
        """Update status displays."""
        # Camera status
        if self._camera_active:
            self._camera_status_label.setText("Camera: Active")
            self._camera_status_label.setStyleSheet(
                "font-size: 13px; padding: 8px; background-color: #d4edda; "
                "border-radius: 5px; color: #155724; font-weight: bold;"
            )
        else:
            self._camera_status_label.setText("Camera: Inactive")
            self._camera_status_label.setStyleSheet(
                "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
                "border-radius: 5px; color: #7f8c8d; font-weight: bold;"
            )

        # Face status
        if self._face_detected:
            self._face_status_label.setText("Face: Detected")
            self._face_status_label.setStyleSheet(
                "font-size: 13px; padding: 8px; background-color: #d4edda; "
                "border-radius: 5px; color: #155724;"
            )
        else:
            self._face_status_label.setText("Face: Not detected")
            self._face_status_label.setStyleSheet(
                "font-size: 13px; padding: 8px; background-color: #ecf0f1; "
                "border-radius: 5px; color: #7f8c8d;"
            )

        # EAR
        ear_text = f"Current EAR: {self._current_ear:.3f}" if self._current_ear > 0 else "Current EAR: --"
        self._ear_label.setText(ear_text)

        # Statistics
        stats_text = (
            f"Blinks/Min: {self._blinks_per_minute:.1f} | "
            f"Last Min: {self._blinks_last_minute} | "
            f"Since Last Blink: {self._time_since_last_blink:.1f}s"
        )
        self._stats_label.setText(stats_text)

    def _update_statistics_display(self, *args) -> None:
        """Update statistics display (called with args for signal connection)."""
        if not self._monitoring:
            return
        self._update_status_display()

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
    def set_camera_status(self, active: bool) -> None:
        """Set camera status from vision worker.

        Args:
            active: Whether camera is active.
        """
        self._camera_active = active
        self._update_status_display()

    @pyqtSlot(bool)
    def set_face_detected(self, detected: bool) -> None:
        """Set face detection status.

        Args:
            detected: Whether face is detected.
        """
        self._face_detected = detected
        self._update_status_display()

    @pyqtSlot(dict)
    def update_statistics(self, stats: dict) -> None:
        """Update statistics from vision worker.

        Args:
            stats: Statistics dictionary.
        """
        self._current_ear = stats.get("current_ear", 0.0)
        self._blinks_per_minute = stats.get("blinks_per_minute", 0.0)
        self._blinks_last_minute = stats.get("blinks_last_minute", 0)
        self._time_since_last_blink = stats.get("time_since_last_blink_seconds", 0.0)
        self._update_status_display()

    @pyqtSlot(int)
    def update_calibration_progress(self, progress: int) -> None:
        """Update calibration progress bar.

        Args:
            progress: Progress percentage (0-100).
        """
        self._calibration_progress.setValue(progress)

    @pyqtSlot(float)
    def on_calibration_complete(self, threshold: float) -> None:
        """Handle calibration completion.

        Args:
            threshold: Calibrated EAR threshold.
        """
        self._calibrating = False
        self._calibration_progress.setVisible(False)
        self._calibrate_button.setEnabled(True)
        self._start_button.setEnabled(True)

        logger.info(f"Calibration complete with threshold: {threshold:.3f}")

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

    @property
    def is_calibrating(self) -> bool:
        """Get calibration state."""
        return self._calibrating
