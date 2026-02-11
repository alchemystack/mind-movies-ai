"""Configuration file loading utilities for Mind Movie Generator."""

from pathlib import Path
from typing import Any

import yaml

from .settings import (
    BuildSettings,
    MovieSettings,
    MusicSettings,
    Settings,
    VideoSettings,
)

# Default config file names to search for
DEFAULT_CONFIG_FILES = ["config.yaml", "config.yml", "mindmovie.yaml", "mindmovie.yml"]


class ConfigLoader:
    """Loads and merges configuration from YAML files and environment variables."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        """Initialize the config loader.

        Args:
            config_path: Optional path to a specific config file.
                         If None, searches for default config files.
        """
        self.config_path = Path(config_path) if config_path else None
        self._yaml_config: dict[str, Any] | None = None

    def find_config_file(self, search_dir: Path | None = None) -> Path | None:
        """Find a config file in the given or current directory.

        Args:
            search_dir: Directory to search in. Defaults to current directory.

        Returns:
            Path to the config file if found, None otherwise.
        """
        if self.config_path and self.config_path.exists():
            return self.config_path

        search_dir = search_dir or Path.cwd()
        for filename in DEFAULT_CONFIG_FILES:
            path = search_dir / filename
            if path.exists():
                return path
        return None

    def load_yaml_config(self, path: Path | None = None) -> dict[str, Any]:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML file. If None, searches for default files.

        Returns:
            Dictionary with configuration values, empty dict if no file found.
        """
        if self._yaml_config is not None:
            return self._yaml_config

        config_file = path or self.find_config_file()
        if config_file is None:
            self._yaml_config = {}
            return self._yaml_config

        with open(config_file, encoding="utf-8") as f:
            content = yaml.safe_load(f)
            self._yaml_config = content if content else {}

        return self._yaml_config

    def load_settings(self, config_path: Path | str | None = None) -> Settings:
        """Load settings by merging YAML config with environment variables.

        YAML config provides base values, environment variables take precedence.

        Args:
            config_path: Optional path to a specific config file.

        Returns:
            Fully configured Settings instance.
        """
        if config_path:
            self.config_path = Path(config_path)

        yaml_config = self.load_yaml_config()

        # Build nested settings from YAML config sections
        video_config = yaml_config.get("video", {})
        music_config = yaml_config.get("music", {})
        movie_config = yaml_config.get("movie", {})
        build_config = yaml_config.get("build", {})

        # Create section settings (YAML values can be overridden by env vars)
        video_settings = VideoSettings(**video_config) if video_config else VideoSettings()
        music_settings = MusicSettings(**music_config) if music_config else MusicSettings()
        movie_settings = MovieSettings(**movie_config) if movie_config else MovieSettings()
        build_settings = BuildSettings(**build_config) if build_config else BuildSettings()

        # Create root settings - API settings load from environment variables
        return Settings(
            video=video_settings,
            music=music_settings,
            movie=movie_settings,
            build=build_settings,
        )


def load_settings(config_path: Path | str | None = None) -> Settings:
    """Convenience function to load settings.

    Args:
        config_path: Optional path to a specific config file.

    Returns:
        Fully configured Settings instance.
    """
    loader = ConfigLoader(config_path)
    return loader.load_settings()
