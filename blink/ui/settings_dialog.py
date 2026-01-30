"""Settings dialog for Blink!."""

from loguru import logger

from blink.config.settings import AlertMode, CameraResolution, Settings
from blink.utils.validators import (
    validate_alert_interval,
    validate_blink_rate,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, settings: Settings, parent=None):
        """Initialize settings dialog.

        Args:
            settings: Current settings.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.settings = settings
        self._temp_settings: Settings = settings.model_copy()

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("Blink! Settings")
        self.setMinimumSize(600, 500)
        self.resize(650, 550)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_alert_tab(), "Alert Settings")
        tabs.addTab(self._create_camera_tab(), "Camera")
        tabs.addTab(self._create_ui_tab(), "Interface")
        tabs.addTab(self._create_privacy_tab(), "Privacy")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_alert_tab(self) -> QWidget:
        """Create alert settings tab.

        Returns:
            Widget with alert settings.
        """
        widget = QWidget()
        layout = QFormLayout(widget)

        # Alert interval
        self._alert_interval_spin = QSpinBox()
        self._alert_interval_spin.setRange(1, 60)
        self._alert_interval_spin.setSuffix(" minutes")
        self._alert_interval_spin.setValue(self._temp_settings.alert_interval_minutes)
        layout.addRow("Alert Interval:", self._alert_interval_spin)

        # Blink rate threshold
        self._blink_rate_spin = QSpinBox()
        self._blink_rate_spin.setRange(5, 30)
        self._blink_rate_spin.setSuffix(" blinks/min")
        self._blink_rate_spin.setValue(self._temp_settings.min_blinks_per_minute)
        layout.addRow("Minimum Blinks/Minute:", self._blink_rate_spin)

        # Alert mode
        self._alert_mode_combo = QComboBox()
        self._alert_mode_combo.addItem("Blink Screen (Gentle)", AlertMode.BLINK)
        self._alert_mode_combo.addItem("Irritation (Attention)", AlertMode.IRRITATION)
        mode_index = self._alert_mode_combo.findData(self._temp_settings.alert_mode)
        if mode_index >= 0:
            self._alert_mode_combo.setCurrentIndex(mode_index)
        layout.addRow("Alert Mode:", self._alert_mode_combo)

        # Animation duration
        self._animation_spin = QSpinBox()
        self._animation_spin.setRange(500, 5000)
        self._animation_spin.setSuffix(" ms")
        self._animation_spin.setValue(self._temp_settings.animation_duration_ms)
        layout.addRow("Animation Duration:", self._animation_spin)

        return widget

    def _create_camera_tab(self) -> QWidget:
        """Create camera settings tab.

        Returns:
            Widget with camera settings.
        """
        widget = QWidget()
        layout = QFormLayout(widget)

        # Resolution
        self._resolution_combo = QComboBox()
        self._resolution_combo.addItem("Default (640x480)", CameraResolution.DEFAULT)
        self._resolution_combo.addItem("Eco (320x240)", CameraResolution.ECO)
        res_index = self._resolution_combo.findData(self._temp_settings.camera_resolution)
        if res_index >= 0:
            self._resolution_combo.setCurrentIndex(res_index)
        layout.addRow("Camera Resolution:", self._resolution_combo)

        # Target FPS
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(5, 30)
        self._fps_spin.setValue(self._temp_settings.target_fps)
        layout.addRow("Target FPS:", self._fps_spin)

        # Enable camera
        self._camera_enabled_check = QCheckBox()
        self._camera_enabled_check.setChecked(self._temp_settings.camera_enabled)
        layout.addRow("Enable Camera:", self._camera_enabled_check)

        return widget

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab.

        Returns:
            Widget with UI settings.
        """
        widget = QWidget()
        layout = QFormLayout(widget)

        # Start minimized
        self._start_minimized_check = QCheckBox()
        self._start_minimized_check.setChecked(self._temp_settings.start_minimized)
        layout.addRow("Start Minimized:", self._start_minimized_check)

        # Show tray icon
        self._tray_icon_check = QCheckBox()
        self._tray_icon_check.setChecked(self._temp_settings.show_tray_icon)
        layout.addRow("Show Tray Icon:", self._tray_icon_check)

        # Notifications
        self._notifications_check = QCheckBox()
        self._notifications_check.setChecked(self._temp_settings.enable_notifications)
        layout.addRow("Enable Notifications:", self._notifications_check)

        return widget

    def _create_privacy_tab(self) -> QWidget:
        """Create privacy settings tab.

        Returns:
            Widget with privacy information.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Privacy notice
        notice = QLabel(
            "<b>Privacy Policy</b><br><br>"
            "Blink! is designed with your privacy in mind:<br><br>"
            "• All processing happens on your device<br>"
            "• No frames are stored or transmitted<br>"
            "• No network calls are made<br>"
            "• No telemetry or analytics<br>"
            "• You are always in control of your camera<br><br>"
            "Your eye health data never leaves your computer."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        layout.addWidget(notice)

        layout.addSpacing(20)

        # Acknowledgement
        self._privacy_ack_check = QCheckBox("I understand and acknowledge the privacy policy")
        self._privacy_ack_check.setChecked(self._temp_settings.privacy_acknowledged)
        layout.addWidget(self._privacy_ack_check)

        layout.addStretch()

        return widget

    def _accept_settings(self) -> None:
        """Validate and accept settings."""
        try:
            # Validate alert interval
            alert_interval = self._alert_interval_spin.value()
            validate_alert_interval(alert_interval)

            # Validate blink rate
            blink_rate = self._blink_rate_spin.value()
            validate_blink_rate(blink_rate)

            # Create updated settings
            self._temp_settings.alert_interval_minutes = alert_interval
            self._temp_settings.min_blinks_per_minute = blink_rate
            self._temp_settings.alert_mode = self._alert_mode_combo.currentData()
            self._temp_settings.animation_duration_ms = self._animation_spin.value()
            self._temp_settings.camera_resolution = self._resolution_combo.currentData()
            self._temp_settings.target_fps = self._fps_spin.value()
            self._temp_settings.camera_enabled = self._camera_enabled_check.isChecked()
            self._temp_settings.start_minimized = self._start_minimized_check.isChecked()
            self._temp_settings.show_tray_icon = self._tray_icon_check.isChecked()
            self._temp_settings.enable_notifications = self._notifications_check.isChecked()
            self._temp_settings.privacy_acknowledged = self._privacy_ack_check.isChecked()

            self.settings = self._temp_settings
            self.accept()
            logger.info("Settings accepted and validated")

        except ValueError as e:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Invalid Setting", str(e))

    def get_settings(self) -> Settings:
        """Get updated settings.

        Returns:
            Settings object.
        """
        return self.settings
