"""Unit tests for configuration management."""

from pathlib import Path

import pytest

from mindmovie.config import load_settings
from mindmovie.config.loader import ConfigLoader
from mindmovie.config.settings import APISettings, MovieSettings, Settings, VideoSettings


class TestSettings:
    def test_default_values(self) -> None:
        settings = Settings()
        assert settings.build_dir == "build"
        assert settings.output_path == "mind_movie.mp4"
        assert settings.has_required_api_keys() is False

    def test_loads_api_keys_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ak")
        monkeypatch.setenv("GEMINI_API_KEY", "gk")
        s = APISettings()
        assert s.anthropic_api_key.get_secret_value() == "ak"
        assert s.gemini_api_key.get_secret_value() == "gk"

    def test_validates_ranges(self) -> None:
        with pytest.raises(ValueError):
            VideoSettings(max_concurrent=0)
        with pytest.raises(ValueError):
            MovieSettings(num_scenes=9)


class TestConfigLoader:
    def test_load_yaml_config(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("video:\n  model: custom\nbuild:\n  build_dir: cb\n")
        loader = ConfigLoader(cfg)
        settings = loader.load_settings()
        assert settings.video.model == "custom"
        assert settings.build.build_dir == "cb"

    def test_load_settings_function(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("video:\n  model: test\n")
        s = load_settings(cfg)
        assert s.video.model == "test"
