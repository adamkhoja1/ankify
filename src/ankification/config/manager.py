"""Configuration management."""

import os
from pathlib import Path
from typing import Any

import yaml

from .schema import Config


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default.
        """
        self.config_path = config_path or self._default_config_path()
        self._config: Config | None = None

    @staticmethod
    def _default_config_path() -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".config" / "ankification"
        return config_dir / "config.yaml"

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Loaded configuration.
        """
        if not self.config_path.exists():
            self._config = Config.default()
            return self._config

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        # Handle environment variable substitution
        data = self._substitute_env_vars(data)
        self._config = Config(**data)
        return self._config

    def save(self, config: Config | None = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save. If None, saves current config.
        """
        if config is None:
            if self._config is None:
                raise ValueError("No configuration to save")
            config = self._config

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        data = config.to_dict()
        with open(self.config_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get(self) -> Config:
        """Get current configuration.

        Returns:
            Current configuration.
        """
        if self._config is None:
            self._config = self.load()
        return self._config

    def set_value(self, key_path: str, value: Any) -> None:
        """Set a configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., "llm.default_provider")
            value: Value to set
        """
        config = self.get()
        keys = key_path.split(".")

        # Navigate to the target
        current: Any = config
        for key in keys[:-1]:
            current = getattr(current, key)

        # Set the final value
        setattr(current, keys[-1], value)

        # Save updated config
        self.save(config)

    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in config data.

        Supports ${VAR_NAME} syntax.

        Args:
            data: Configuration data (dict, list, or primitive)

        Returns:
            Data with environment variables substituted
        """
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Simple ${VAR} substitution
            if data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                return os.environ.get(var_name, "")
            return data
        else:
            return data

    def init_config(self) -> None:
        """Initialize a new configuration file with defaults."""
        if self.config_path.exists():
            raise FileExistsError(f"Configuration already exists at {self.config_path}")

        config = Config.default()
        self.save(config)
        print(f"Configuration initialized at {self.config_path}")

    def show_config(self) -> str:
        """Get configuration as formatted YAML string.

        Returns:
            YAML representation of current config
        """
        config = self.get()
        return yaml.safe_dump(
            config.to_dict(), default_flow_style=False, sort_keys=False
        )
