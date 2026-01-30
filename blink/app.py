"""Main application orchestrator for Blink!."""

import sys
from pathlib import Path

from loguru import logger

from blink.config.config_manager import ConfigManager
from blink.config.settings import Settings
from blink.threading.signal_bus import SignalBus
from blink.threading.vision_worker import VisionWorker
from blink.ui.main_window import MainWindow
from blink.ui.tray_icon import TrayIcon
from blink.utils.logger import setup_logging
from blink.utils.platform import get_app_paths
from PyQt6.QtWidgets import QApplication


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

    def _init_vision_worker(self) -> None:
        """Initialize vision worker thread."""
        self.vision_worker = VisionWorker()
        # Don't start the worker thread yet - will be started when monitoring starts
        logger.info("Vision worker initialized (stub mode)")

    def _init_ui(self) -> None:
        """Initialize UI components."""
        # Main window
        self.main_window = MainWindow(self.settings)

        # Show or hide based on settings
        if self.settings.start_minimized:
            self.main_window.hide()
        else:
            self.main_window.show()

        # System tray icon
        if self.settings.show_tray_icon:
            self.tray_icon = TrayIcon(self.main_window)
            logger.info("Tray icon initialized")

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

        # Stop vision worker
        if self.vision_worker.isRunning():
            self.vision_worker.stop_monitoring()
            self.vision_worker.quit()
            self.vision_worker.wait()

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
