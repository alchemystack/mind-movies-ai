"""Unit tests for the video client factory."""

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from mindmovie.api.factory import create_video_client
from mindmovie.config.settings import APISettings, Settings, VideoSettings


def _settings(
    provider: str = "byteplus",
    model: str = "seedance-1-5-pro-251215",
    gemini_key: str = "",
    byteplus_key: str = "",
    generate_audio: bool = True,
) -> Settings:
    """Build settings with the given provider and API keys."""
    s = Settings()
    s.api = APISettings.model_construct(
        anthropic_api_key=SecretStr("fake-anthropic"),
        gemini_api_key=SecretStr(gemini_key),
        byteplus_api_key=SecretStr(byteplus_key),
        anthropic_model="claude-sonnet-4-20250514",
    )
    s.video = VideoSettings(
        provider=provider,  # type: ignore[arg-type]
        model=model,
        generate_audio=generate_audio,
    )
    return s


class TestCreateVideoClient:
    def test_byteplus_provider_returns_byteplus_client(self) -> None:
        with patch("mindmovie.api.byteplus_client.BytePlusClient") as mock_cls:
            mock_cls.return_value = mock_cls
            client = create_video_client(
                _settings(provider="byteplus", byteplus_key="bp-test-key")
            )
            mock_cls.assert_called_once_with(
                api_key="bp-test-key",
                model="seedance-1-5-pro-251215",
                generate_audio=True,
            )
            assert client is mock_cls

    def test_veo_provider_returns_veo_client(self) -> None:
        with patch("mindmovie.api.veo_client.VeoClient") as mock_cls:
            mock_cls.return_value = mock_cls
            client = create_video_client(
                _settings(
                    provider="veo",
                    model="veo-3.1-fast-generate-preview",
                    gemini_key="gk-test-key",
                )
            )
            mock_cls.assert_called_once_with(
                api_key="gk-test-key",
                model="veo-3.1-fast-generate-preview",
            )
            assert client is mock_cls

    def test_byteplus_missing_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="BYTEPLUS_API_KEY"):
            create_video_client(_settings(provider="byteplus", byteplus_key=""))

    def test_veo_missing_key_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            create_video_client(_settings(provider="veo", gemini_key=""))

    def test_unknown_provider_raises_value_error(self) -> None:
        s = _settings(provider="byteplus", byteplus_key="key")
        # Force an invalid provider value
        s.video = s.video.model_copy(update={"provider": "invalid"})  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unknown video provider"):
            create_video_client(s)

    def test_byteplus_audio_setting_passed_through(self) -> None:
        with patch("mindmovie.api.byteplus_client.BytePlusClient") as mock_cls:
            mock_cls.return_value = mock_cls
            create_video_client(
                _settings(
                    provider="byteplus",
                    byteplus_key="bp-key",
                    generate_audio=False,
                )
            )
            mock_cls.assert_called_once_with(
                api_key="bp-key",
                model="seedance-1-5-pro-251215",
                generate_audio=False,
            )
