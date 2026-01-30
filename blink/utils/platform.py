"""Platform-specific utilities for Blink!."""

import os
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
    def _try_create_paths(config_dir: Path, log_dir: Path, data_dir: Path) -> AppPaths | None:
        """Attempt to create and verify writable dirs; return paths on success."""
        try:
            for directory in (config_dir, log_dir, data_dir):
                directory.mkdir(parents=True, exist_ok=True)
                # Verify write access
                test_file = directory / ".write_test"
                test_file.write_text("ok", encoding="utf-8")
                test_file.unlink(missing_ok=True)

            return AppPaths(
                config_dir=config_dir,
                data_dir=data_dir,
                log_dir=log_dir,
                config_file=config_dir / "config.json",
            )
        except Exception:
            return None

    candidates: list[tuple[Path, Path, Path]] = []

    # 1) Explicit override for sandboxed/portable use
    env_root = os.environ.get("BLINK_DATA_DIR")
    if env_root:
        root = Path(env_root).expanduser()
        candidates.append((root / "config", root / "logs", root / "data"))

    # 2) System-appropriate locations
    dirs = PlatformDirs(appname="Blink", appauthor=False, ensure_exists=True)
    system_config = Path(dirs.user_config_dir)
    candidates.append((system_config, system_config / "logs", Path(dirs.user_data_dir)))

    # 3) Repo-local fallback (always writable inside sandbox)
    repo_root = Path.cwd() / ".blink_runtime"
    candidates.append((repo_root / "config", repo_root / "logs", repo_root / "data"))

    for config_dir, log_dir, data_dir in candidates:
        paths = _try_create_paths(config_dir, log_dir, data_dir)
        if paths:
            return paths

    # If all candidates fail, raise a clear error
    raise RuntimeError("Unable to create writable directories for Blink! runtime data")
