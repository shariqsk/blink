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

    # File handler with rotation
    log_file = Path(log_dir) / "blink.log" if log_dir else Path("blink.log")
    logger.add(
        log_file,
        format=log_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
    )

    logger.info("Blink! logging initialized")
