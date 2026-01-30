"""Main application orchestrator for Blink!."""

import sys
from pathlib import Path

from blink.camera.camera_manager import CameraManager
from blink.config.config_manager import ConfigManager
from blink.config.settings import AnimationIntensity, Settings
from blink.threading.signal_bus import SignalBus
from blink.threading.vision_worker import VisionWorker
from blink.ui.main_window import MainWindow
from blink.ui.screen_overlay import ScreenOverlay
from blink.ui.tray_icon import TrayIcon
from blink.utils.logger import setup_logging
from blink.utils.platform import get_app_paths
from loguru import logger
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon


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
        self._init_camera()
        self._init_vision_worker()
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

    def _init_camera(self) -> None:
        """Initialize camera manager."""
        self.camera_manager = CameraManager()
        logger.info("Camera manager initialized")

    def _init_vision_worker(self) -> None:
        """Initialize vision worker thread."""
        resolution = self.settings.get_resolution_tuple()
        target_fps = self.settings.target_fps

        self.vision_worker = VisionWorker(
            camera_manager=self.camera_manager,
            target_fps=target_fps,
        )

        # Connect vision worker signals
        self.vision_worker.blink_detected.connect(self._on_blink_detected)
        self.vision_worker.statistics_updated.connect(self._on_statistics_updated)
        self.vision_worker.face_detected.connect(self._on_face_detected)
        self.vision_worker.camera_status_changed.connect(self._on_camera_status_changed)
        self.vision_worker.calibration_progress.connect(self._on_calibration_progress)
        self.vision_worker.calibration_complete.connect(self._on_calibration_complete)
        self.vision_worker.error_occurred.connect(self._on_error)

        # Connect signal bus to vision worker
        self.signal_bus.start_monitoring.connect(self.vision_worker.start_monitoring)
        self.signal_bus.stop_monitoring.connect(self.vision_worker.stop_monitoring)

        logger.info("Vision worker initialized")

    def _init_ui(self) -> None:
        """Initialize UI components."""
        logger.info("Initializing UI components")

        try:
            # Main window
            self.main_window = MainWindow(self.settings)
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
                self.tray_icon = TrayIcon(self.main_window, self.screen_overlay)
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
        if self.vision_worker.is_running:
            self.vision_worker.stop_monitoring()

        # Clean up vision worker
        self.vision_worker.cleanup()

        # Close camera
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
