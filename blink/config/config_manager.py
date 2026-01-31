"""Configuration persistence manager for Blink!."""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from blink.config.defaults import DEFAULT_SETTINGS
from blink.config.settings import Settings
from blink.utils.exceptions import ConfigError


class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self, config_file: Path):
        """Initialize config manager.

        Args:
            config_file: Path to configuration file.
        """
        self.config_file = config_file
        self._settings: Optional[Settings] = None

    def load(self) -> Settings:
        """Load settings from file or create defaults.

        Returns:
            Loaded settings (or defaults if file doesn't exist).

        Raises:
            ConfigError: If file exists but is invalid.
        """
        if self._settings is not None:
            return self._settings

        if not self.config_file.exists():
            logger.info(f"No config file found at {self.config_file}, using defaults")
            self._settings = DEFAULT_SETTINGS
            self.save()
            return self._settings

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate with Pydantic
            self._settings = Settings(**data)
            logger.info(f"Loaded configuration from {self.config_file}")
            return self._settings

        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}") from e

    def save(self, settings: Optional[Settings] = None) -> None:
        """Save settings to file.

        Args:
            settings: Settings to save. If None, saves current settings.

        Raises:
            ConfigError: If save fails.
        """
        to_save = settings or self._settings

        if to_save is None:
            raise ConfigError("No settings to save")

        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(to_save.model_dump(), f, indent=2)

            self._settings = to_save
            logger.info(f"Saved configuration to {self.config_file}")

        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}") from e

    def update(self, **kwargs) -> Settings:
        """Update settings with new values and save.

        Args:
            **kwargs: Settings fields to update.

        Returns:
            Updated settings.

        Raises:
            ConfigError: If update fails.
        """
        current = self.load()
        updated_dict = current.model_copy(update=kwargs).model_dump()
        new_settings = Settings(**updated_dict)
        self.save(new_settings)
        return new_settings

    @property
    def settings(self) -> Settings:
        """Get current settings (lazy load)."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings
