"""Main application window for Blink!."""

from loguru import logger

from blink.config.settings import Settings
from blink.config.config_manager import ConfigManager
from blink.threading.signal_bus import SignalBus
from blink.ui.settings_dialog import SettingsDialog
from blink.utils.diagnostics import export_diagnostics
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut, QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
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
        available_cameras: list[tuple[int, str]] | None = None,
    ):
        """Initialize main window.

        Args:
            settings: Application settings.
            signal_bus: Shared signal bus.
            config_manager: Config persistence manager.
            app_paths: Runtime paths for diagnostics export.
            camera_manager: Camera manager for listing devices.
            available_cameras: Optional pre-enumerated camera list from app start.
        """
        super().__init__()
        self.settings = settings
        self.signal_bus = signal_bus
        self.config_manager = config_manager
        self.app_paths = app_paths
        self.camera_manager = camera_manager
        self._available_cameras = available_cameras or self.camera_manager.get_camera_info()
        self._monitoring = False
        self._camera_active = False
        self._face_detected = False
        self._calibrating = False
        self._preview_frame = None
        self._preview_enabled = False

        # Current metrics
        self._current_ear = 0.0
        self._blinks_per_minute = 0.0
        self._blinks_last_minute = 0
        self._time_since_last_blink = 0.0

        # Statistics update timer
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_statistics_display)
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._capture_preview_frame)

        self._shortcuts: list[QShortcut] = []
        self._camera_combo: QComboBox | None = None
        self._init_ui()
        self._init_hotkeys()
        self._update_status_display()
        self._clear_preview()

    def _clear_preview(self) -> None:
        """Blank the preview area."""
        self._preview_label.clear()
        self._preview_label.setText("Preview not available")

    def _populate_camera_combo(self) -> None:
        """Fill the camera combo box with available devices."""
        if not self._camera_combo:
            return
        self._camera_combo.clear()
        # Prefer the cached list from app startup (same one Settings dialog sees)
        cameras = self._available_cameras or []
        if not cameras:
            cameras = self.camera_manager.get_camera_info()
        logger.info(f"Main window camera enumerate -> {cameras}")
        if cameras:
            self._available_cameras = cameras
        else:
            # Fall back to generic IDs so user can still select a device
            cameras = [(i, f"Camera {i}") for i in range(0, 3)]
        self._camera_combo.setEnabled(True)
        self._camera_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for cam_id, cam_name in cameras:
            display = cam_name or f"Camera {cam_id}"
            self._camera_combo.addItem(display, cam_id)
        # Set current selection
        idx = self._camera_combo.findData(self.settings.camera_id)
        if idx >= 0:
            self._camera_combo.setCurrentIndex(idx)
        else:
            self._camera_combo.setCurrentIndex(0)
            self.settings.camera_id = self._camera_combo.currentData()
            self.config_manager.save(self.settings)
        self._camera_combo.setMinimumWidth(200)
    def _init_ui(self) -> None:
        """Initialize UI components with a high-contrast, non-overlapping layout."""
        self.setWindowTitle("Blink! - Eye Health Monitor")
        self.setMinimumSize(1040, 760)
        self.resize(1180, 820)
        self.setStyleSheet(
            """
            QMainWindow { background: #0b1220; }
            QLabel { color: #e5e7eb; }
            QLabel#Title { font-size: 28px; font-weight: 800; color: #e8edf5; letter-spacing: 0.3px; }
            QLabel#Subtitle { color: #94a3b8; font-size: 13px; }
            QLabel#SectionTitle { color: #e5e7eb; font-size: 14px; font-weight: 700; }
            QLabel#StatLabel { color: #94a3b8; font-size: 12px; }
            QLabel#StatValue { color: #e8edf5; font-size: 26px; font-weight: 750; }
            QLabel#Chip { background: #1e293b; color: #e2e8f0; padding: 6px 12px; border-radius: 16px; font-weight: 700; }
            QWidget#Card { background: #111a2f; border: 1px solid #1f2c46; border-radius: 14px; }
            QPushButton { font-size: 14px; padding: 12px; border-radius: 10px; border: none; font-weight: 700; }
            QPushButton#Primary { background: #22c55e; color: #0b1220; }
            QPushButton#Accent { background: #0ea5e9; color: #0b1220; }
            QPushButton#Neutral { background: #1e293b; color: #e2e8f0; }
            QPushButton#Warning { background: #f59e0b; color: #0b1220; }
            QPushButton:disabled { background: #1f2f46; color: #7c879e; }
            QProgressBar { background: #0f172a; color: #e5e7eb; border: 1px solid #1f2c46; border-radius: 8px; text-align: center; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #22d3ee); border-radius: 8px; }
            """
        )

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(18)
        root.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("Blink!")
        title.setObjectName("Title")
        subtitle = QLabel("Eye health monitor & gentle reminders")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self._monitoring_chip = QLabel("Idle")
        self._monitoring_chip.setObjectName("Chip")
        self._monitoring_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._monitoring_chip.setMinimumWidth(120)
        header.addWidget(self._monitoring_chip, alignment=Qt.AlignmentFlag.AlignRight)

        root.addLayout(header)

        # Metric row
        metrics = QHBoxLayout()
        metrics.setSpacing(12)

        self._ear_value_label = QLabel("--")
        self._ear_value_label.setObjectName("StatValue")
        metrics.addWidget(
            self._build_stat_card("Current EAR", self._ear_value_label, "Target ~0.25-0.30")
        )

        self._blink_rate_label = QLabel("--/min")
        self._blink_rate_label.setObjectName("StatValue")
        metrics.addWidget(self._build_stat_card("Blink rate", self._blink_rate_label, "Per minute"))

        self._last_min_label = QLabel("--")
        self._last_min_label.setObjectName("StatValue")
        metrics.addWidget(self._build_stat_card("Last minute", self._last_min_label, "Blinks counted"))

        self._since_last_label = QLabel("--s")
        self._since_last_label.setObjectName("StatValue")
        metrics.addWidget(self._build_stat_card("Since last blink", self._since_last_label, "Seconds"))

        root.addLayout(metrics)

        # Body content
        body = QHBoxLayout()
        body.setSpacing(16)

        # Left column: preview + status
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        self._preview_label = QLabel("Preview not available")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumHeight(260)
        self._preview_label.setStyleSheet(
            "color: #cbd5e1; border: 1px dashed #1f2c46; background: #0d1424; border-radius: 10px;"
        )
        preview_card = self._wrap_card("Camera preview", self._preview_label)
        left_col.addWidget(preview_card)

        status_body = QWidget()
        status_layout = QVBoxLayout(status_body)
        status_layout.setSpacing(6)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self._camera_status_label = QLabel("Camera: Inactive")
        self._camera_status_label.setObjectName("SectionTitle")
        self._face_status_label = QLabel("Face: Not detected")
        self._face_status_label.setObjectName("SectionTitle")
        status_layout.addWidget(self._camera_status_label)
        status_layout.addWidget(self._face_status_label)

        self._status_note = QLabel("Waiting to start monitoring")
        self._status_note.setStyleSheet("color: #94a3b8; font-size: 12px;")
        status_layout.addWidget(self._status_note)

        status_card = QWidget(objectName="Card")
        status_card_layout = QVBoxLayout(status_card)
        status_card_layout.setContentsMargins(14, 12, 14, 12)
        status_card_layout.setSpacing(4)
        status_card_layout.addWidget(QLabel("Status overview", objectName="SectionTitle"))
        status_card_layout.addWidget(status_body)
        left_col.addWidget(status_card)

        body.addLayout(left_col, 3)

        # Right column: controls
        controls_card = QWidget(objectName="Card")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(14, 14, 14, 14)
        controls_layout.setSpacing(10)

        # Camera quick picker
        camera_row = QHBoxLayout()
        camera_row.setSpacing(8)
        camera_label = QLabel("Camera")
        camera_label.setObjectName("SectionTitle")
        self._camera_combo = QComboBox()
        self._populate_camera_combo()
        self._camera_combo.currentIndexChanged.connect(self._on_camera_selected)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("Neutral")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self._refresh_camera_list)
        camera_row.addWidget(camera_label)
        camera_row.addWidget(self._camera_combo, stretch=1)
        camera_row.addWidget(refresh_btn)
        controls_layout.addLayout(camera_row)

        self._start_button = QPushButton("Start monitoring")
        self._start_button.setObjectName("Primary")
        self._start_button.setMinimumHeight(46)
        self._start_button.clicked.connect(self._toggle_monitoring)
        controls_layout.addWidget(self._start_button)

        self._calibrate_button = QPushButton("Calibrate threshold")
        self._calibrate_button.setObjectName("Warning")
        self._calibrate_button.setMinimumHeight(42)
        self._calibrate_button.clicked.connect(self._start_calibration)
        self._calibrate_button.setEnabled(False)
        controls_layout.addWidget(self._calibrate_button)

        self._calibration_progress = QProgressBar()
        self._calibration_progress.setRange(0, 100)
        self._calibration_progress.setValue(0)
        self._calibration_progress.setVisible(False)
        controls_layout.addWidget(self._calibration_progress)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(8)
        action_grid.setVerticalSpacing(8)

        self._preview_button = QPushButton("Preview camera")
        self._preview_button.setObjectName("Accent")
        self._preview_button.setMinimumHeight(40)
        self._preview_button.clicked.connect(self._toggle_preview)

        self._camera_enable_check = QCheckBox("Enable camera")
        self._camera_enable_check.setChecked(self.settings.camera_enabled)
        self._camera_enable_check.stateChanged.connect(self._toggle_camera_enabled)

        self._settings_button = QPushButton("Settings")
        self._settings_button.setObjectName("Neutral")
        self._settings_button.setMinimumHeight(40)
        self._settings_button.clicked.connect(self._open_settings)

        self._test_animation_button = QPushButton("Test animation")
        self._test_animation_button.setObjectName("Neutral")
        self._test_animation_button.setMinimumHeight(40)
        self._test_animation_button.clicked.connect(self._trigger_test_animation)

        self._export_button = QPushButton("Export diagnostics")
        self._export_button.setObjectName("Neutral")
        self._export_button.setMinimumHeight(40)
        self._export_button.clicked.connect(self._export_diagnostics)

        action_grid.addWidget(self._preview_button, 0, 0)
        action_grid.addWidget(self._settings_button, 0, 1)
        action_grid.addWidget(self._test_animation_button, 1, 0)
        action_grid.addWidget(self._export_button, 1, 1)
        action_grid.addWidget(self._camera_enable_check, 2, 0, 1, 2)

        controls_layout.addLayout(action_grid)

        helper = QLabel("Run monitoring to see live stats. Preview uses your selected camera and resolution.")
        helper.setStyleSheet("color: #94a3b8; font-size: 12px;")
        helper.setWordWrap(True)
        controls_layout.addWidget(helper)

        body.addWidget(controls_card, 2)

        root.addLayout(body)
        root.addStretch()

        self._set_status_chip("Idle", "#1e293b", "#e2e8f0")

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

    def _build_stat_card(self, title: str, value_label: QLabel, helper_text: str = "") -> QWidget:
        """Create a compact stat card with label + value + helper copy."""
        card = QWidget(objectName="Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("StatLabel")
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(label)
        layout.addWidget(value_label)

        if helper_text:
            helper = QLabel(helper_text)
            helper.setStyleSheet("color: #94a3b8; font-size: 12px;")
            layout.addWidget(helper)

        return card

    def _wrap_card(self, title: str, inner_widget: QWidget) -> QWidget:
        """Wrap a widget in a styled card with a title."""
        card = QWidget(objectName="Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        layout.addWidget(inner_widget)
        return card

    def _set_status_chip(self, text: str, bg: str, fg: str) -> None:
        """Update the status chip text and colors."""
        self._monitoring_chip.setText(text)
        self._monitoring_chip.setStyleSheet(
            f"background: {bg}; color: {fg}; padding: 6px 12px; border-radius: 16px; "
            "font-weight: 700;"
        )

    def _toggle_monitoring(self, force_stop: bool = False) -> None:
        """Toggle monitoring state."""
        if self._preview_timer.isActive():
            self._preview_timer.stop()
            self._preview_button.setText("Preview camera")

        # Auto-enable camera when starting
        if not force_stop and not self._monitoring and not self.settings.camera_enabled:
            self.settings.camera_enabled = True
            self._camera_enable_check.setChecked(True)
            self.config_manager.save(self.settings)
            self.signal_bus.camera_enabled_changed.emit(True)

        self._monitoring = not force_stop and not self._monitoring

        if self._monitoring:
            self._start_button.setText("Stop monitoring")
            self._start_button.setStyleSheet(
                "background: #ef4444; color: #0b1220; font-weight: 700; border-radius: 10px; padding: 12px;"
            )
            self._calibrate_button.setEnabled(True)
            self._stats_timer.start(1000)
            self._status_note.setText("Monitoring in progress")
            self._set_status_chip("Monitoring", "#14532d", "#d1fae5")
            logger.info("Monitoring started from UI")
            self.signal_bus.start_monitoring.emit()
        else:
            self._start_button.setText("Start monitoring")
            self._start_button.setStyleSheet(
                "background: #22c55e; color: #0b1220; font-weight: 700; border-radius: 10px; padding: 12px;"
            )
            self._calibrate_button.setEnabled(False)
            self._calibration_progress.setVisible(False)
            self._calibrating = False
            self._stats_timer.stop()
            self._reset_status()
            self._set_status_chip("Idle", "#1e293b", "#e2e8f0")
            if not self._preview_enabled:
                self._clear_preview()
            logger.info("Monitoring stopped from UI")
            self.signal_bus.stop_monitoring.emit()

    def _start_calibration(self) -> None:
        """Start calibration process."""
        self._calibrating = True
        self._calibration_progress.setValue(0)
        self._calibration_progress.setVisible(True)
        self._calibrate_button.setEnabled(False)
        self._start_button.setEnabled(False)
        self._status_note.setText("Calibrating eye aspect ratio baseline...")
        self._set_status_chip("Calibrating", "#854d0e", "#fef9c3")

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
        self._status_note.setText("Calibration complete. Resume monitoring to apply.")
        self._set_status_chip("Ready", "#1e293b", "#e2e8f0")

        logger.info("Calibration complete")

    def _open_settings(self) -> None:
        """Open settings dialog."""
        was_monitoring = self._monitoring
        was_preview = self._preview_timer.isActive()
        if was_monitoring:
            self._toggle_monitoring()
        elif was_preview:
            self._toggle_preview()

        dialog = SettingsDialog(
            self.settings,
            parent=self,
            available_cameras=self._refresh_available_cameras(),
        )
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.config_manager.save(self.settings)
            self.signal_bus.settings_changed.emit(self.settings)
            self._init_hotkeys()  # refresh shortcuts
            logger.info("Settings updated from dialog")

        # Restore previous run state
        if was_monitoring and not self._monitoring:
            self._toggle_monitoring()
        elif was_preview and not self._preview_timer.isActive():
            self._toggle_preview()

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
        self._status_note.setText("Waiting to start monitoring")
        self._update_status_display()

    def _update_status_display(self) -> None:
        if self._camera_active:
            self._camera_status_label.setText("Camera: Active")
            self._camera_status_label.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: 700;")
        else:
            self._camera_status_label.setText("Camera: Inactive")
            self._camera_status_label.setStyleSheet("color: #f87171; font-size: 13px; font-weight: 700;")

        if self._face_detected:
            self._face_status_label.setText("Face: Detected")
            self._face_status_label.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: 700;")
            self._status_note.setText("Face detected. Tracking blinks.")
        else:
            self._face_status_label.setText("Face: Not detected")
            self._face_status_label.setStyleSheet("color: #e5e7eb; font-size: 13px; font-weight: 700;")
            if self._monitoring:
                self._status_note.setText("Looking for your face... please center in frame.")

        ear_text = f"{self._current_ear:.3f}" if self._current_ear > 0 else "--"
        self._ear_value_label.setText(ear_text)

        blink_rate_text = f"{self._blinks_per_minute:.1f}/min" if self._blinks_per_minute > 0 else "--/min"
        self._blink_rate_label.setText(blink_rate_text)

        last_min_text = str(self._blinks_last_minute) if self._blinks_last_minute > 0 else "--"
        self._last_min_label.setText(last_min_text)

        since_text = f"{self._time_since_last_blink:.1f}s" if self._time_since_last_blink > 0 else "--s"
        self._since_last_label.setText(since_text)


    def _update_statistics_display(self, *args) -> None:
        """Update statistics display (called with args for signal connection)."""
        if not self._monitoring:
            return
        self._update_status_display()

    def _toggle_preview(self) -> None:
        """Toggle lightweight preview without full monitoring."""
        if self._preview_enabled:
            self._preview_enabled = False
            self._preview_button.setText("Preview camera")
            if self._preview_timer.isActive():
                self._preview_timer.stop()
            if not self._monitoring:
                self.signal_bus.stop_preview.emit()
            self._clear_preview()
            return

        # Enable preview
        self._preview_enabled = True
        self._preview_button.setText("Stop preview")

        # Auto-enable camera for preview
        if not self.settings.camera_enabled:
            self.settings.camera_enabled = True
            self._camera_enable_check.setChecked(True)
            self.config_manager.save(self.settings)
            self.signal_bus.camera_enabled_changed.emit(True)

        if self._monitoring:
            # When monitoring is running, we reuse worker-emitted preview frames.
            return

        # Preview-only mode: ask worker to capture on its thread
        self.signal_bus.start_preview.emit()
        self._preview_timer.start(150)  # poll display refresh cadence

    def _capture_preview_frame(self) -> None:
        """Capture single frame for preview."""
        if not self._preview_enabled:
            return
        # In preview-only mode, we rely on worker emitting preview frames.
        # This timer simply ensures the label updates if frames arrive.
        pass

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        logger.info("Main window closed (will continue running in tray)")
        self._clear_preview()
        self.hide()
        event.ignore()

    def update_settings(self, settings: Settings) -> None:
        """Update settings.

        Args:
            settings: New settings.
        """
        self.settings = settings
        self._init_hotkeys()
        self._camera_enable_check.setChecked(self.settings.camera_enabled)
        self._populate_camera_combo()
        logger.info("Settings updated and hotkeys refreshed")

    def _toggle_camera_enabled(self) -> None:
        """Enable/disable camera from the main window toggle."""
        enabled = self._camera_enable_check.isChecked()
        self.settings.camera_enabled = enabled
        self.config_manager.save(self.settings)
        self.signal_bus.camera_enabled_changed.emit(enabled)
        # If camera was disabled while monitoring, stop to release resources
        if not enabled and self._monitoring:
            self._toggle_monitoring(force_stop=True)
        status = "enabled" if enabled else "disabled"
        logger.info(f"Camera {status} via main window toggle")

    def _refresh_available_cameras(self) -> list[tuple[int, str]]:
        """Refresh and cache camera list."""
        self._available_cameras = self.camera_manager.get_camera_info()
        return self._available_cameras

    def _refresh_camera_list(self) -> None:
        """Force re-enumeration of cameras and repopulate dropdown."""
        self._available_cameras = self.camera_manager.get_camera_info()
        logger.info(f"Camera list refreshed: {self._available_cameras}")
        self._populate_camera_combo()

    def _on_camera_selected(self) -> None:
        """Handle camera selection change from the main screen."""
        if not self._camera_combo:
            return
        cam_id = self._camera_combo.currentData()
        if cam_id is None or cam_id == -1:
            return

        if self.settings.camera_id == cam_id:
            return

        self.settings.camera_id = cam_id
        self.config_manager.save(self.settings)
        logger.info(f"Camera changed from main window to ID {cam_id}")
        # Propagate to worker and other components
        self.signal_bus.settings_changed.emit(self.settings)

        # If preview/monitoring is active, give user instant feedback
        if self._monitoring:
            self.signal_bus.stop_monitoring.emit()
            self.signal_bus.start_monitoring.emit()
        elif self._preview_enabled:
            self.signal_bus.stop_preview.emit()
            self.signal_bus.start_preview.emit()

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

    def show_preview(self, frame) -> None:
        """Update camera preview with incoming frame."""
        try:
            if frame is None:
                self._preview_label.clear()
                self._preview_label.setText("No camera frame")
                return
            rgb = frame[:, :, ::-1].copy()  # make contiguous RGB copy
            h, w, _ = rgb.shape
            bytes_per_line = 3 * w
            qimg = QImage(rgb.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(
                480,
                270,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Only display when preview is enabled or monitoring is active
            if self._preview_enabled or self._monitoring:
                self._preview_label.setPixmap(pix)
                self._preview_label.setText("")
        except Exception as exc:
            logger.debug(f"Preview update failed: {exc}")
