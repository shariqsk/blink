"""Logging configuration for Blink!."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logging(log_dir: Optional[Path] = None, debug: bool = False) -> None:
    """Configure logging with rotation and formatting.

    Args:
        log_dir: Directory for log files. If None, uses current directory.
        debug: Enable debug mode with console output.
    """
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Remove default handler
    logger.remove()

    # Console handler (only in debug mode)
    if debug:
        logger.add(
            sys.stdout,
            format=log_format,
            level="DEBUG",
            colorize=True,
        )

    # File handler with rotation (falls back to console if unwritable)
    log_file = Path(log_dir) / "blink.log" if log_dir else Path("blink.log")

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Use async queue when allowed (may fail in restricted sandboxes)
            logger.add(
                log_file,
                format=log_format,
                level="INFO",
                rotation="10 MB",
                retention="30 days",
                compression="zip",
                enqueue=True,
            )
        except PermissionError:
            # Fall back to synchronous writes if pipe/queue creation is blocked
            logger.add(
                log_file,
                format=log_format,
                level="INFO",
                rotation="10 MB",
                retention="30 days",
                compression="zip",
                enqueue=False,
            )
    except Exception as exc:
        # Avoid crashing the app when the OS path isn't writable (e.g., sandboxed runs)
        logger.add(
            sys.stderr,
            format=log_format,
            level="INFO",
            colorize=True,
        )
        logger.warning(
            f"File logging disabled; cannot write to {log_file}. "
            f"Using console logging instead. ({exc})"
        )

    logger.info("Blink! logging initialized")
