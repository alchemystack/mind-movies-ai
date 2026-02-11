"""Unit tests for setup wizard and API key validation."""

from unittest.mock import patch

from pydantic import SecretStr

from mindmovie.cli.ui.setup import (
    check_system_dependencies,
    run_setup_check,
    validate_api_keys_for_command,
)
from mindmovie.config.settings import APISettings, Settings


def _settings_with_keys(
    anthropic: str = "", gemini: str = ""
) -> Settings:
    """Create settings with the given API keys."""
    s = Settings()
    s.api = APISettings.model_construct(
        anthropic_api_key=SecretStr(anthropic),
        gemini_api_key=SecretStr(gemini),
    )
    return s


class TestCheckSystemDependencies:
    def test_ffmpeg_found(self) -> None:
        with patch("mindmovie.cli.ui.setup.shutil.which", return_value="/usr/bin/ffmpeg"):
            missing = check_system_dependencies()
        # ffmpeg is found; imagemagick might or might not be
        assert "ffmpeg" not in missing

    def test_ffmpeg_not_found(self) -> None:
        def _which(name: str) -> str | None:
            # Nothing found
            return None

        with patch("mindmovie.cli.ui.setup.shutil.which", side_effect=_which):
            missing = check_system_dependencies()
        assert "ffmpeg" in missing
        assert "imagemagick" in missing


class TestValidateApiKeysForCommand:
    def test_anthropic_present(self) -> None:
        settings = _settings_with_keys(anthropic="sk-ant-test")
        assert validate_api_keys_for_command(settings, require_anthropic=True)

    def test_anthropic_missing(self) -> None:
        settings = _settings_with_keys()
        assert not validate_api_keys_for_command(settings, require_anthropic=True)

    def test_gemini_present(self) -> None:
        settings = _settings_with_keys(gemini="gk-test")
        assert validate_api_keys_for_command(settings, require_gemini=True)

    def test_gemini_missing(self) -> None:
        settings = _settings_with_keys()
        assert not validate_api_keys_for_command(settings, require_gemini=True)

    def test_both_required_both_present(self) -> None:
        settings = _settings_with_keys(anthropic="sk-ant-test", gemini="gk-test")
        assert validate_api_keys_for_command(
            settings, require_anthropic=True, require_gemini=True
        )

    def test_both_required_one_missing(self) -> None:
        settings = _settings_with_keys(anthropic="sk-ant-test")
        assert not validate_api_keys_for_command(
            settings, require_anthropic=True, require_gemini=True
        )

    def test_none_required(self) -> None:
        settings = _settings_with_keys()
        assert validate_api_keys_for_command(settings)


class TestRunSetupCheck:
    def test_all_present(self) -> None:
        settings = _settings_with_keys(anthropic="sk-ant-test", gemini="gk-test")
        with patch(
            "mindmovie.cli.ui.setup.check_system_dependencies", return_value=[]
        ):
            assert run_setup_check(settings)

    def test_missing_api_keys(self) -> None:
        settings = _settings_with_keys()
        with patch(
            "mindmovie.cli.ui.setup.check_system_dependencies", return_value=[]
        ):
            assert not run_setup_check(settings)

    def test_missing_system_deps(self) -> None:
        settings = _settings_with_keys(anthropic="sk-ant-test", gemini="gk-test")
        with patch(
            "mindmovie.cli.ui.setup.check_system_dependencies",
            return_value=["ffmpeg"],
        ):
            assert not run_setup_check(settings)
