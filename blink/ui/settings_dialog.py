"""Settings dialog for Blink!."""

from loguru import logger

from blink.config.settings import (
    AlertMode,
    AnimationIntensity,
    CameraResolution,
    Settings,
    TriggerLogic,
)
from blink.utils.validators import (
    validate_alert_interval,
    validate_blink_rate,
    validate_hotkey,
    validate_quiet_hours,
)
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, settings: Settings, parent=None, available_cameras: list[tuple[int, str]] | None = None):
        super().__init__(parent)
        self.settings = settings
        self._temp_settings: Settings = settings.model_copy()
        self.available_cameras = available_cameras or []

        self.setStyleSheet(
            """
            QDialog { background: #f7f9fb; }
            QLabel { color: #2c3e50; }
            QGroupBox { border: 1px solid #e1e8ed; border-radius: 6px; margin-top: 10px; }
            QGroupBox:title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QPushButton { padding: 8px 14px; border-radius: 6px; background: #3498db; color: white; }
            """
        )
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("Blink! Settings")
        self.setMinimumSize(720, 620)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_detection_tab(), "Detection")
        tabs.addTab(self._create_animations_tab(), "Animations")
        tabs.addTab(self._create_privacy_tab(), "Privacy")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------------- Tabs ----------------
    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._start_minimized_check = QCheckBox()
        self._start_minimized_check.setChecked(self._temp_settings.start_minimized)
        layout.addRow("Start minimized:", self._start_minimized_check)

        self._tray_icon_check = QCheckBox()
        self._tray_icon_check.setChecked(self._temp_settings.show_tray_icon)
        layout.addRow("Show tray icon:", self._tray_icon_check)

        self._notifications_check = QCheckBox()
        self._notifications_check.setChecked(self._temp_settings.enable_notifications)
        layout.addRow("Enable notifications:", self._notifications_check)

        self._status_panel_check = QCheckBox()
        self._status_panel_check.setChecked(self._temp_settings.show_status_panel)
        layout.addRow("Show status panel:", self._status_panel_check)

        # Quiet hours
        self._quiet_hours_check = QCheckBox("Silence animations during quiet hours")
        self._quiet_hours_check.setChecked(self._temp_settings.quiet_hours_enabled)
        quiet_box = QHBoxLayout()
        self._quiet_start = QTimeEdit()
        self._quiet_start.setDisplayFormat("HH:mm")
        start_h, start_m = map(int, self._temp_settings.quiet_hours_start.split(":"))
        self._quiet_start.setTime(QTime(start_h, start_m))
        self._quiet_end = QTimeEdit()
        self._quiet_end.setDisplayFormat("HH:mm")
        end_h, end_m = map(int, self._temp_settings.quiet_hours_end.split(":"))
        self._quiet_end.setTime(QTime(end_h, end_m))
        quiet_box.addWidget(QLabel("From"))
        quiet_box.addWidget(self._quiet_start)
        quiet_box.addWidget(QLabel("to"))
        quiet_box.addWidget(self._quiet_end)
        quiet_row = QVBoxLayout()
        quiet_row.addWidget(self._quiet_hours_check)
        quiet_row.addLayout(quiet_box)
        quiet_widget = QWidget()
        quiet_widget.setLayout(quiet_row)
        layout.addRow("Quiet hours:", quiet_widget)

        # Aggregated stats
        self._stats_toggle = QCheckBox("Store daily blink counts + last trigger time (no images/video)")
        self._stats_toggle.setChecked(self._temp_settings.collect_aggregated_stats)
        layout.addRow("Aggregated stats:", self._stats_toggle)

        # Hotkeys
        self._hotkey_start = QLineEdit(self._temp_settings.hotkey_start_stop)
        self._hotkey_pause = QLineEdit(self._temp_settings.hotkey_pause)
        self._hotkey_test = QLineEdit(self._temp_settings.hotkey_test)
        layout.addRow("Hotkey: start/stop", self._hotkey_start)
        layout.addRow("Hotkey: pause", self._hotkey_pause)
        layout.addRow("Hotkey: test animation", self._hotkey_test)

        return widget

    def _create_detection_tab(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setSpacing(12)

        trigger_group = QGroupBox("Time-based triggers")
        trigger_layout = QFormLayout(trigger_group)

        self._trigger_logic_combo = QComboBox()
        self._trigger_logic_combo.addItem("If no blink for N seconds", TriggerLogic.NO_BLINK)
        self._trigger_logic_combo.addItem("If blink rate below R blinks/min for X minutes", TriggerLogic.LOW_RATE)
        self._trigger_logic_combo.addItem("Both (prioritize no-blink gap)", TriggerLogic.BOTH)
        current_logic = self._temp_settings.trigger_logic
        if isinstance(current_logic, str):
            current_logic = TriggerLogic(current_logic)
        trigger_logic_index = self._trigger_logic_combo.findData(current_logic)
        if trigger_logic_index >= 0:
            self._trigger_logic_combo.setCurrentIndex(trigger_logic_index)
        trigger_layout.addRow("Trigger logic:", self._trigger_logic_combo)

        self._no_blink_spin = QSpinBox()
        self._no_blink_spin.setRange(5, 120)
        self._no_blink_spin.setSuffix(" seconds")
        self._no_blink_spin.setValue(self._temp_settings.no_blink_seconds)
        trigger_layout.addRow("No blink for:", self._no_blink_spin)

        self._low_rate_spin = QSpinBox()
        self._low_rate_spin.setRange(5, 30)
        self._low_rate_spin.setSuffix(" blinks/min")
        self._low_rate_spin.setValue(self._temp_settings.low_rate_threshold)
        trigger_layout.addRow("Blink rate below:", self._low_rate_spin)

        self._low_rate_duration = QSpinBox()
        self._low_rate_duration.setRange(1, 15)
        self._low_rate_duration.setSuffix(" minutes")
        self._low_rate_duration.setValue(self._temp_settings.low_rate_duration_minutes)
        trigger_layout.addRow("For duration:", self._low_rate_duration)

        self._alert_interval_spin = QSpinBox()
        self._alert_interval_spin.setRange(1, 60)
        self._alert_interval_spin.setSuffix(" minutes")
        self._alert_interval_spin.setValue(self._temp_settings.alert_interval_minutes)
        trigger_layout.addRow("Cooldown between alerts:", self._alert_interval_spin)

        vbox.addWidget(trigger_group)

        detect_group = QGroupBox("Detection tuning")
        detect_layout = QFormLayout(detect_group)

        self._ear_threshold_spin = QDoubleSpinBox()
        self._ear_threshold_spin.setRange(0.1, 0.4)
        self._ear_threshold_spin.setSingleStep(0.01)
        self._ear_threshold_spin.setDecimals(3)
        self._ear_threshold_spin.setValue(self._temp_settings.ear_threshold)
        detect_layout.addRow("EAR threshold:", self._ear_threshold_spin)

        self._auto_calibrate_check = QCheckBox()
        self._auto_calibrate_check.setChecked(self._temp_settings.auto_calibrate)
        detect_layout.addRow("Auto-calibrate on start:", self._auto_calibrate_check)

        self._blink_frames_spin = QSpinBox()
        self._blink_frames_spin.setRange(1, 5)
        self._blink_frames_spin.setValue(self._temp_settings.blink_consecutive_frames)
        detect_layout.addRow("Closed frames to count blink:", self._blink_frames_spin)

        self._min_blink_spin = QSpinBox()
        self._min_blink_spin.setRange(20, 200)
        self._min_blink_spin.setSuffix(" ms")
        self._min_blink_spin.setValue(self._temp_settings.min_blink_duration_ms)
        detect_layout.addRow("Min blink duration:", self._min_blink_spin)

        self._max_blink_spin = QSpinBox()
        self._max_blink_spin.setRange(200, 1000)
        self._max_blink_spin.setSuffix(" ms")
        self._max_blink_spin.setValue(self._temp_settings.max_blink_duration_ms)
        detect_layout.addRow("Max blink duration:", self._max_blink_spin)

        vbox.addWidget(detect_group)

        camera_group = QGroupBox("Camera")
        camera_layout = QGridLayout(camera_group)

        # Camera selector
        self._camera_combo = QComboBox()
        if not self.available_cameras:
            self.available_cameras = [(i, f"Camera {i}") for i in range(0, 3)]
        for cam_id, cam_name in self.available_cameras:
            self._camera_combo.addItem(cam_name, cam_id)
        current_cam = self._temp_settings.camera_id
        cam_index = self._camera_combo.findData(current_cam)
        if cam_index >= 0:
            self._camera_combo.setCurrentIndex(cam_index)
        camera_layout.addWidget(QLabel("Camera device:"), 0, 0)
        camera_layout.addWidget(self._camera_combo, 0, 1)

        self._resolution_combo = QComboBox()
        self._resolution_combo.addItem("Default (640x480)", CameraResolution.DEFAULT)
        self._resolution_combo.addItem("Eco (320x240)", CameraResolution.ECO)
        current_res = self._temp_settings.camera_resolution
        if isinstance(current_res, str):
            try:
                current_res = CameraResolution(current_res)
            except ValueError:
                current_res = CameraResolution.DEFAULT
        res_index = self._resolution_combo.findData(current_res)
        if res_index >= 0:
            self._resolution_combo.setCurrentIndex(res_index)
        camera_layout.addWidget(QLabel("Resolution:"), 1, 0)
        camera_layout.addWidget(self._resolution_combo, 1, 1)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(5, 30)
        self._fps_spin.setValue(self._temp_settings.target_fps)
        camera_layout.addWidget(QLabel("Target FPS:"), 2, 0)
        camera_layout.addWidget(self._fps_spin, 2, 1)

        self._camera_id_spin = QSpinBox()
        self._camera_id_spin.setRange(0, 9)
        self._camera_id_spin.setValue(self._temp_settings.camera_id)
        camera_layout.addWidget(QLabel("Camera ID (fallback):"), 3, 0)
        camera_layout.addWidget(self._camera_id_spin, 3, 1)

        self._camera_enabled_check = QCheckBox("Enable camera")
        self._camera_enabled_check.setChecked(self._temp_settings.camera_enabled)
        camera_layout.addWidget(self._camera_enabled_check, 4, 0, 1, 2)

        vbox.addWidget(camera_group)
        vbox.addStretch()
        return widget

    def _create_animations_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._alert_mode_combo = QComboBox()
        self._alert_mode_combo.addItem("Blink animation (gentle)", AlertMode.BLINK)
        self._alert_mode_combo.addItem("Irritation animation (attention)", AlertMode.IRRITATION)
        current_mode = self._temp_settings.alert_mode
        if isinstance(current_mode, str):
            try:
                current_mode = AlertMode(current_mode)
            except ValueError:
                current_mode = AlertMode.BLINK
        mode_index = self._alert_mode_combo.findData(current_mode)
        if mode_index >= 0:
            self._alert_mode_combo.setCurrentIndex(mode_index)
        layout.addRow("Animation mode:", self._alert_mode_combo)

        self._animation_intensity_combo = QComboBox()
        for label, value in [
            ("Low", AnimationIntensity.LOW),
            ("Medium", AnimationIntensity.MEDIUM),
            ("High", AnimationIntensity.HIGH),
        ]:
            self._animation_intensity_combo.addItem(label, value)
        current_intensity = self._temp_settings.animation_intensity
        if isinstance(current_intensity, str):
            try:
                current_intensity = AnimationIntensity(current_intensity)
            except ValueError:
                current_intensity = AnimationIntensity.MEDIUM
        intensity_index = self._animation_intensity_combo.findData(current_intensity)
        if intensity_index >= 0:
            self._animation_intensity_combo.setCurrentIndex(intensity_index)
        layout.addRow("Intensity:", self._animation_intensity_combo)

        self._animation_spin = QSpinBox()
        self._animation_spin.setRange(500, 5000)
        self._animation_spin.setSuffix(" ms")
        self._animation_spin.setValue(self._temp_settings.animation_duration_ms)
        layout.addRow("Base animation duration:", self._animation_spin)

        return widget

    def _create_privacy_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        notice = QLabel(
            "<b>Camera permission & privacy</b><br><br>"
            "Blink! uses your camera locally to detect blinks. Frames never leave your device, "
            "and no images or video are saved. If you revoke camera permission, monitoring stops "
            "immediately. You can pause or quit any time."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("padding: 12px; background-color: #ecf0f1; border-radius: 8px;")
        layout.addWidget(notice)

        self._privacy_ack_check = QCheckBox("I understand how Blink! uses the camera")
        self._privacy_ack_check.setChecked(self._temp_settings.privacy_acknowledged)
        layout.addWidget(self._privacy_ack_check)

        self._show_privacy_notice_check = QCheckBox("Show privacy reminder on start")
        self._show_privacy_notice_check.setChecked(self._temp_settings.show_privacy_notice)
        layout.addWidget(self._show_privacy_notice_check)

        layout.addStretch()
        return widget

    # ---------------- Validation ----------------
    def _accept_settings(self) -> None:
        try:
            alert_interval = self._alert_interval_spin.value()
            validate_alert_interval(alert_interval)

            blink_rate = self._low_rate_spin.value()
            validate_blink_rate(blink_rate)

            validate_quiet_hours(
                self._quiet_start.time().toString("HH:mm"),
                self._quiet_end.time().toString("HH:mm"),
            )

            validate_hotkey(self._hotkey_start.text().strip())
            validate_hotkey(self._hotkey_pause.text().strip())
            validate_hotkey(self._hotkey_test.text().strip())

            self._temp_settings.alert_interval_minutes = alert_interval
            self._temp_settings.min_blinks_per_minute = blink_rate
            self._temp_settings.low_rate_threshold = blink_rate
            self._temp_settings.low_rate_duration_minutes = self._low_rate_duration.value()
            self._temp_settings.no_blink_seconds = self._no_blink_spin.value()
            self._temp_settings.trigger_logic = self._trigger_logic_combo.currentData()

            self._temp_settings.alert_mode = self._alert_mode_combo.currentData()
            self._temp_settings.animation_intensity = self._animation_intensity_combo.currentData()
            self._temp_settings.animation_duration_ms = self._animation_spin.value()

            self._temp_settings.camera_resolution = self._resolution_combo.currentData()
            self._temp_settings.target_fps = self._fps_spin.value()
            self._temp_settings.camera_id = self._camera_combo.currentData()
            self._temp_settings.camera_enabled = self._camera_enabled_check.isChecked()

            self._temp_settings.ear_threshold = self._ear_threshold_spin.value()
            self._temp_settings.auto_calibrate = self._auto_calibrate_check.isChecked()
            self._temp_settings.blink_consecutive_frames = self._blink_frames_spin.value()
            self._temp_settings.min_blink_duration_ms = self._min_blink_spin.value()
            self._temp_settings.max_blink_duration_ms = self._max_blink_spin.value()

            self._temp_settings.start_minimized = self._start_minimized_check.isChecked()
            self._temp_settings.show_tray_icon = self._tray_icon_check.isChecked()
            self._temp_settings.enable_notifications = self._notifications_check.isChecked()
            self._temp_settings.show_status_panel = self._status_panel_check.isChecked()

            self._temp_settings.quiet_hours_enabled = self._quiet_hours_check.isChecked()
            self._temp_settings.quiet_hours_start = self._quiet_start.time().toString("HH:mm")
            self._temp_settings.quiet_hours_end = self._quiet_end.time().toString("HH:mm")
            self._temp_settings.collect_aggregated_stats = self._stats_toggle.isChecked()

            self._temp_settings.hotkey_start_stop = self._hotkey_start.text().strip()
            self._temp_settings.hotkey_pause = self._hotkey_pause.text().strip()
            self._temp_settings.hotkey_test = self._hotkey_test.text().strip()

            self._temp_settings.privacy_acknowledged = self._privacy_ack_check.isChecked()
            self._temp_settings.show_privacy_notice = self._show_privacy_notice_check.isChecked()

            self.settings = self._temp_settings
            self.accept()
            logger.info("Settings accepted and validated")

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Setting", str(e))

    def get_settings(self) -> Settings:
        return self.settings
