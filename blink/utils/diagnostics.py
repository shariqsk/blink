"""Diagnostics export helper."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from loguru import logger

from blink.utils.platform import AppPaths


def export_diagnostics(paths: AppPaths) -> Path:
    """Zip logs and config into a diagnostics bundle.

    Images/video are intentionally excluded.

    Returns:
        Path to the created zip file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = paths.data_dir / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"blink_diagnostics_{timestamp}.zip"

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zf:
        # Config
        if paths.config_file.exists():
            zf.write(paths.config_file, arcname="config/config.json")

        # Aggregated stats (if present)
        stats_file = paths.data_dir / "aggregated_stats.json"
        if stats_file.exists():
            zf.write(stats_file, arcname="data/aggregated_stats.json")

        # Logs (exclude large media; only textual logs are expected here)
        if paths.log_dir.exists():
            for log_file in paths.log_dir.glob("*.log*"):
                if log_file.suffix.lower() in {".jpg", ".png", ".mp4"}:
                    continue
                zf.write(log_file, arcname=f"logs/{log_file.name}")

    logger.info(f"Diagnostics exported to {archive_path}")
    return archive_path
