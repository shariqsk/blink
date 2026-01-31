"""Main application orchestrator for Blink!."""

import os
import sys

# Quiet noisy backends (MediaPipe / TF Lite) so users don't see warning spam.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")

from blink.camera.camera_manager import CameraManager
from blink.config.config_manager import ConfigManager
from blink.config.settings import Settings
from blink.core.aggregated_store import AggregatedStatsStore
from blink.core.time_trigger import TimeTriggerEngine
from blink.threading.signal_bus import SignalBus
from blink.threading.vision_worker import VisionWorker
from blink.ui.main_window import MainWindow
from blink.ui.screen_overlay import AnimationIntensity, ScreenOverlay
from blink.ui.tray_icon import TrayIcon
from blink.utils.logger import setup_logging
from blink.utils.platform import get_app_paths
from loguru import logger
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QThread, Qt


class BlinkApplication(QApplication):
    """Main application class."""

    def __init__(self, debug: bool = False):
        """Initialize application.

        Args:
            debug: Enable debug mode.
        """
        super().__init__(sys.argv)

        self._debug = debug
        self._init_logging()
        self._init_paths()
        self._init_config()
        self._init_signal_bus()
        self._init_stats_store()
        self._init_trigger_engine()
        self._wire_status_signals()
        self._init_camera()
        self._init_vision_worker_thread()
        self._init_ui()

        logger.info("Blink! application initialized")

    def _init_logging(self) -> None:
        """Initialize logging."""
        paths = get_app_paths()
        setup_logging(paths.log_dir, debug=self._debug)

    def _init_paths(self) -> None:
        """Initialize application paths."""
        self.paths = get_app_paths()
        logger.info(f"Config directory: {self.paths.config_dir}")
        logger.info(f"Log directory: {self.paths.log_dir}")

    def _init_config(self) -> None:
        """Initialize configuration."""
        self.config_manager = ConfigManager(self.paths.config_file)
        self.settings = self.config_manager.load()
        logger.info("Configuration loaded")

    def _init_signal_bus(self) -> None:
        """Initialize signal bus."""
        self.signal_bus = SignalBus()
        logger.info("Signal bus initialized")

    def _init_stats_store(self) -> None:
        """Initialize aggregated stats store."""
        self.stats_store = AggregatedStatsStore(
            self.paths.data_dir,
            enabled=self.settings.collect_aggregated_stats,
        )
        logger.info("Aggregated stats store ready")

    def _init_trigger_engine(self) -> None:
        """Initialize time-based trigger engine."""
        self.trigger_engine = TimeTriggerEngine(
            self.settings,
            self.signal_bus,
            stats_store=self.stats_store,
        )

    def _wire_status_signals(self) -> None:
        """Wire status-related signals for tray/status updates."""
        self.signal_bus.start_monitoring.connect(lambda: self._set_tray_status("Monitoring"))
        self.signal_bus.stop_monitoring.connect(lambda: self._set_tray_status("Idle"))
        self.signal_bus.pause_for_duration.connect(
            lambda minutes: self._set_tray_status(f"Paused {minutes}m")
        )
        self.signal_bus.pause_until_tomorrow.connect(
            lambda: self._set_tray_status("Paused until tomorrow")
        )
        self.signal_bus.resume_requested.connect(lambda: self._set_tray_status("Monitoring"))

    def _init_camera(self) -> None:
        """Initialize camera manager."""
        self.camera_manager = CameraManager()
        logger.info("Camera manager initialized")

    def _init_vision_worker_thread(self) -> None:
        """Spin up the vision worker in its own thread to avoid UI freezes."""
        resolution = self.settings.get_resolution_tuple()
        target_fps = self.settings.target_fps

        self.vision_thread = QThread(self)
        self.vision_thread.setObjectName("VisionThread")
        self.vision_thread.setPriority(QThread.Priority.NormalPriority)

        self.vision_worker = VisionWorker(
            camera_manager=self.camera_manager,
            target_fps=target_fps,
            camera_id=self.settings.camera_id,
            resolution=resolution,
        )
        self.vision_worker.moveToThread(self.vision_thread)

        # Connect vision worker signals (queued across threads automatically)
        self.vision_worker.blink_detected.connect(self._on_blink_detected)
        self.vision_worker.statistics_updated.connect(self._on_statistics_updated)
        self.vision_worker.face_detected.connect(self._on_face_detected)
        self.vision_worker.camera_status_changed.connect(self._on_camera_status_changed)
        self.vision_worker.calibration_progress.connect(self._on_calibration_progress)
        self.vision_worker.calibration_complete.connect(self._on_calibration_complete)
        self.vision_worker.error_occurred.connect(self._on_error)
        self.vision_worker.frame_preview.connect(self._on_frame_preview)

        # Connect signal bus to vision worker
        self.signal_bus.start_monitoring.connect(self.vision_worker.start_monitoring, Qt.ConnectionType.QueuedConnection)
        self.signal_bus.stop_monitoring.connect(self.vision_worker.stop_monitoring, Qt.ConnectionType.QueuedConnection)
        self.signal_bus.test_animation.connect(self._on_test_animation)
        self.signal_bus.settings_changed.connect(self._on_settings_changed)

        # Ensure worker cleans up when thread finishes
        self.vision_thread.finished.connect(self.vision_worker.cleanup)
        self.vision_thread.start()

        logger.info("Vision worker thread started")

    def _init_ui(self) -> None:
        """Initialize UI components."""
        logger.info("Initializing UI components")

        try:
            # Main window
            self.main_window = MainWindow(
                self.settings,
                self.signal_bus,
                self.config_manager,
                self.paths,
                self.camera_manager,
            )
            logger.info("Main window created")

            # Show or hide based on settings
            if self.settings.start_minimized:
                self.main_window.hide()
            else:
                self.main_window.show()

            # Screen overlay for animations
            self.screen_overlay = ScreenOverlay(self.main_window)
            intensity = AnimationIntensity(self.settings.animation_intensity)
            self.screen_overlay.set_intensity(intensity)
            logger.info("Screen overlay ready")

            # Connect animation request signals
            self.signal_bus.animation_requested.connect(self._on_animation_requested)

            # System tray icon
            if self.settings.show_tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = TrayIcon(self.main_window, self.signal_bus, self.screen_overlay)
                self._set_tray_status("Idle")
                logger.info("Tray icon initialized")
            elif self.settings.show_tray_icon:
                logger.warning("System tray not available; tray icon disabled")

            logger.info("UI initialization complete")
        except Exception:
            logger.exception("UI initialization failed")
            raise

    def _on_blink_detected(self) -> None:
        """Handle blink detected signal.

        This is called from the vision worker thread via Qt signal.
        """
        logger.debug("Blink detected")
        self.signal_bus.blink_detected.emit()

    def _on_statistics_updated(self, stats: dict) -> None:
        """Handle statistics update signal.

        Args:
            stats: Statistics dictionary from vision worker.
        """
        self.main_window.update_statistics(stats)
        self.signal_bus.statistics_updated.emit(stats)

    def _on_face_detected(self, detected: bool) -> None:
        """Handle face detection signal.

        Args:
            detected: Whether face is detected.
        """
        self.main_window.set_face_detected(detected)
        self.signal_bus.face_detected.emit(detected)

    def _on_camera_status_changed(self, active: bool) -> None:
        """Handle camera status change signal.

        Args:
            active: Whether camera is active.
        """
        self.main_window.set_camera_status(active)
        self.signal_bus.camera_status_changed.emit(active)

    def _on_frame_preview(self, frame) -> None:
        """Send preview frame to UI."""
        self.main_window.show_preview(frame)

    def _on_calibration_progress(self, progress: int) -> None:
        """Handle calibration progress signal.

        Args:
            progress: Progress percentage (0-100).
        """
        self.main_window.update_calibration_progress(progress)

    def _on_calibration_complete(self, threshold: float) -> None:
        """Handle calibration complete signal.

        Args:
            threshold: Calibrated EAR threshold.
        """
        # Update settings with new threshold
        self.config_manager.update(ear_threshold=threshold)
        self.settings.ear_threshold = threshold

        # Notify main window
        self.main_window.on_calibration_complete(threshold)

        logger.info(f"Calibration complete, threshold saved: {threshold:.3f}")

    def _on_error(self, error_message: str) -> None:
        """Handle error signal.

        Args:
            error_message: Error message.
        """
        logger.error(f"Vision worker error: {error_message}")
        self.signal_bus.error_occurred.emit(error_message)
        try:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self.main_window, "Blink error", error_message)
        except Exception:
            pass

    def _on_animation_requested(self, mode: str) -> None:
        """Handle animation request signal.

        Args:
            mode: Animation mode ('blink' or 'irritation').
        """
        if not self.screen_overlay:
            return

        logger.info(f"Animation requested: {mode}")

        if mode == "blink":
            self.screen_overlay.play_blink()
        elif mode == "irritation":
            self.screen_overlay.play_irritation()
        else:
            logger.warning(f"Unknown animation mode: {mode}")

    def _on_test_animation(self) -> None:
        """Trigger a test animation using current mode."""
        if hasattr(self, "screen_overlay"):
            self._on_animation_requested(self.settings.alert_mode)

    def _on_settings_changed(self, new_settings: Settings) -> None:
        """Handle settings updates from UI."""
        self.settings = new_settings
        self.trigger_engine.update_settings(new_settings)

        if hasattr(self, "screen_overlay"):
            intensity = AnimationIntensity(new_settings.animation_intensity)
            self.screen_overlay.set_intensity(intensity)

        # Update vision worker parameters
        if hasattr(self, "vision_worker"):
            self.vision_worker.set_target_fps(new_settings.target_fps)
            self.vision_worker.set_camera_resolution(new_settings.get_resolution_tuple())
            self.vision_worker.set_camera_id(new_settings.camera_id)

    def _set_tray_status(self, text: str) -> None:
        """Update tray status text if tray is present."""
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.set_status_text(text)

    def run(self) -> int:
        """Run application event loop.

        Returns:
            Exit code.
        """
        logger.info("Starting application event loop")
        return self.exec()

    def cleanup(self) -> None:
        """Clean up resources before exit."""
        logger.info("Cleaning up resources")

        # Stop any active animations
        if hasattr(self, 'screen_overlay') and self.screen_overlay:
            self.screen_overlay.stop_animation()

        # Stop vision worker
        if hasattr(self, "vision_worker") and self.vision_worker.is_running:
            self.vision_worker.stop_monitoring()

        # Clean up vision worker + thread
        if hasattr(self, "vision_thread"):
            self.vision_thread.quit()
            self.vision_thread.wait(2000)

        # Final camera close (idempotent)
        self.camera_manager.close_camera()

        logger.info("Application cleanup complete")


def main(debug: bool = False) -> int:
    """Main entry point.

    Args:
        debug: Enable debug mode.

    Returns:
        Exit code.
    """
    app = BlinkApplication(debug=debug)

    # Handle cleanup on exit
    def on_exit() -> None:
        app.cleanup()

    app.aboutToQuit.connect(on_exit)

    return app.run()
