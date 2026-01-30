"""Platform-specific utilities for Blink!."""

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs


@dataclass
class AppPaths:
    """Container for application paths."""

    config_dir: Path
    data_dir: Path
    log_dir: Path
    config_file: Path


def get_app_paths() -> AppPaths:
    """Get OS-appropriate application directories.

    Returns:
        AppPaths: Container with directory paths.
    """
    dirs = PlatformDirs(appname="Blink", appauthor=False, ensure_exists=True)

    config_dir = Path(dirs.user_config_dir)
    log_dir = config_dir / "logs"
    data_dir = Path(dirs.user_data_dir)

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.json"

    return AppPaths(
        config_dir=config_dir,
        data_dir=data_dir,
        log_dir=log_dir,
        config_file=config_file,
    )
