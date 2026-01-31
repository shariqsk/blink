"""Main application window for Blink!."""

from loguru import logger

from blink.config.settings import Settings
from blink.config.config_manager import ConfigManager
from blink.threading.signal_bus import SignalBus
from blink.ui.settings_dialog import SettingsDialog
from blink.utils.diagnostics import export_diagnostics
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        settings: Settings,
        signal_bus: SignalBus,
        config_manager: ConfigManager,
        app_paths,
        camera_manager,
    ):
        """Initialize main window.

        Args:
            settings: Application settings.
            signal_bus: Shared signal bus.
            config_manager: Config persistence manager.
            app_paths: Runtime paths for diagnostics export.
            camera_manager: Camera manager for listing devices.
        """
        super().__init__()
        self.settings = settings
        self.signal_bus = signal_bus
        self.config_manager = config_manager
        self.app_paths = app_paths
        self.camera_manager = camera_manager
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

        self._shortcuts: list[QShortcut] = []
        self._init_ui()
        self._init_hotkeys()
        self._update_status_display()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("Blink! - Eye Health Monitor")
        self.setMinimumSize(600, 550)
        self.resize(650, 600)
        self.setStyleSheet(
            """
            QMainWindow { background: #0f172a; }
            QLabel { color: #e5e7eb; }
            QPushButton { font-size: 14px; padding: 12px; border-radius: 8px; color: #0f172a; background: #38bdf8; border: none; font-weight: 600; }
            QPushButton:hover { background: #0ea5e9; }
            QPushButton:pressed { background: #0284c7; }
            QGroupBox { border: 1px solid #1f2937; border-radius: 10px; margin-top: 12px; color: #e5e7eb; }
            QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QWidget#Card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; }
            QProgressBar { background: #111827; color: #e5e7eb; border: 1px solid #1f2937; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background: #38bdf8; border-radius: 6px; }
            """
        )

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
        self._start_button.setStyleSheet("background-color: #22c55e; color: #0f172a; font-weight: bold;")
        self._start_button.clicked.connect(self._toggle_monitoring)
        button_layout.addWidget(self._start_button)

        self._calibrate_button = QPushButton("Calibrate Threshold")
        self._calibrate_button.setStyleSheet("background-color: #f59e0b; color: #0f172a;")
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

        action_row = QVBoxLayout()

        self._settings_button = QPushButton("Settings")
        self._settings_button.setStyleSheet("background-color: #3498db; color: white;")
        self._settings_button.setMinimumHeight(42)
        self._settings_button.clicked.connect(self._open_settings)
        action_row.addWidget(self._settings_button)

        self._test_animation_button = QPushButton("Test Animation")
        self._test_animation_button.setStyleSheet("background-color: #9b59b6; color: white;")
        self._test_animation_button.setMinimumHeight(42)
        self._test_animation_button.clicked.connect(self._trigger_test_animation)
        action_row.addWidget(self._test_animation_button)

        self._export_button = QPushButton("Export Diagnostics")
        self._export_button.setStyleSheet("background-color: #34495e; color: white;")
        self._export_button.setMinimumHeight(42)
        self._export_button.clicked.connect(self._export_diagnostics)
        action_row.addWidget(self._export_button)

        button_layout.addLayout(action_row)

        layout.addLayout(button_layout)
        layout.addStretch()

    def _init_hotkeys(self) -> None:
        """Register global-ish shortcuts within the window."""
        for sc in self._shortcuts:
            sc.setParent(None)
        self._shortcuts = []

        shortcut_start = QShortcut(QKeySequence(self.settings.hotkey_start_stop), self)
        shortcut_start.activated.connect(self._toggle_monitoring)

        shortcut_pause = QShortcut(QKeySequence(self.settings.hotkey_pause), self)
        shortcut_pause.activated.connect(lambda: self.signal_bus.pause_for_duration.emit(30))

        shortcut_test = QShortcut(QKeySequence(self.settings.hotkey_test), self)
        shortcut_test.activated.connect(self._trigger_test_animation)

        self._shortcuts.extend([shortcut_start, shortcut_pause, shortcut_test])

    def _create_status_panel(self, layout: QVBoxLayout) -> None:
        """Create status information panel.

        Args:
            layout: Layout to add panel to.
        """
        panel = QWidget(objectName="Card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(8)
        panel_layout.setContentsMargins(12, 12, 12, 12)

        # Camera status
        self._camera_status_label = QLabel("Camera: Inactive")
        self._camera_status_label.setStyleSheet("font-size: 13px; color: #a5b4fc;")
        self._camera_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        panel_layout.addWidget(self._camera_status_label)

        # Face status
        self._face_status_label = QLabel("Face: Not detected")
        self._face_status_label.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        self._face_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        panel_layout.addWidget(self._face_status_label)

        # Current EAR
        self._ear_label = QLabel("Current EAR: --")
        self._ear_label.setStyleSheet("font-size: 13px; color: #e5e7eb;")
        self._ear_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        panel_layout.addWidget(self._ear_label)

        # Blink statistics
        self._stats_label = QLabel(
            "Blinks/Min: -- | Last Min: -- | Since Last Blink: --s"
        )
        self._stats_label.setStyleSheet("font-size: 13px; color: #e5e7eb;")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        panel_layout.addWidget(self._stats_label)

        layout.addWidget(panel)

    def _toggle_monitoring(self) -> None:
        """Toggle monitoring state."""
        self._monitoring = not self._monitoring

        if self._monitoring:
            self._start_button.setText("Stop Monitoring")
            self._start_button.setStyleSheet(
                "background-color: #e74c3c; color: white; font-weight: bold;"
            )
            self._calibrate_button.setEnabled(True)
            self._stats_timer.start(1000)
            logger.info("Monitoring started from UI")
            self.signal_bus.start_monitoring.emit()
        else:
            self._start_button.setText("Start Monitoring")
            self._start_button.setStyleSheet(
                "background-color: #27ae60; color: white; font-weight: bold;"
            )
            self._calibrate_button.setEnabled(False)
            self._calibration_progress.setVisible(False)
            self._calibrating = False
            self._stats_timer.stop()
            self._reset_status()
            logger.info("Monitoring stopped from UI")
            self.signal_bus.stop_monitoring.emit()

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
        dialog = SettingsDialog(
            self.settings,
            parent=self,
            available_cameras=self.camera_manager.get_available_cameras(),
        )
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.config_manager.save(self.settings)
            self.signal_bus.settings_changed.emit(self.settings)
            self._init_hotkeys()  # refresh shortcuts
            logger.info("Settings updated from dialog")

    def _trigger_test_animation(self) -> None:
        """Request a test animation."""
        self.signal_bus.test_animation.emit()

    def _export_diagnostics(self) -> None:
        """Export logs + config bundle."""
        archive_path = export_diagnostics(self.app_paths)
        QMessageBox.information(self, "Diagnostics exported", f"Saved to:\n{archive_path}")

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
        self._init_hotkeys()

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
