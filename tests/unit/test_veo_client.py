"""Unit tests for Google Veo video generation client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mindmovie.api import VeoClient
from mindmovie.api.veo_client import _COST_PER_SECOND


def _make_operation(done: bool = True, generated_videos: list | None = None) -> MagicMock:
    op = MagicMock()
    op.done = done
    if done:
        op.response = MagicMock()
        if generated_videos is None:
            gv = MagicMock()
            gv.video = MagicMock()
            op.response.generated_videos = [gv]
        else:
            op.response.generated_videos = generated_videos
    else:
        op.response = None
    return op


@pytest.fixture
def mock_genai_client() -> MagicMock:
    client = MagicMock()
    client.models = MagicMock()
    client.operations = MagicMock()
    return client


@pytest.fixture
def veo_client(mock_genai_client: MagicMock) -> VeoClient:
    with patch("mindmovie.api.veo_client.genai") as mock_genai:
        mock_genai.Client.return_value = mock_genai_client
        client = VeoClient(api_key="test-key", poll_interval=0)
    return client


class TestVeoClientGenerate:
    async def test_generate_video_returns_path(self, veo_client: VeoClient, tmp_path: Path) -> None:
        output = tmp_path / "scene.mp4"
        veo_client.client.models.generate_videos.return_value = _make_operation(done=True)
        result = await veo_client.generate_video(prompt="test", output_path=output)
        assert result == output

    async def test_polls_until_done(self, veo_client: VeoClient, tmp_path: Path) -> None:
        output = tmp_path / "scene.mp4"
        pending = _make_operation(done=False)
        done = _make_operation(done=True)
        veo_client.client.models.generate_videos.return_value = pending
        veo_client.client.operations.get.return_value = done
        await veo_client.generate_video(prompt="test", output_path=output)
        veo_client.client.operations.get.assert_called_once()

    async def test_raises_on_empty_response(self, veo_client: VeoClient, tmp_path: Path) -> None:
        output = tmp_path / "scene.mp4"
        veo_client.client.models.generate_videos.return_value = _make_operation(done=True, generated_videos=[])
        with pytest.raises(RuntimeError, match="no videos returned"):
            await veo_client.generate_video(prompt="test", output_path=output)


class TestVeoClientRetry:
    async def test_retries_on_connection_error(self, veo_client: VeoClient, tmp_path: Path) -> None:
        output = tmp_path / "scene.mp4"
        veo_client.client.models.generate_videos.side_effect = [
            ConnectionError("fail"), _make_operation(done=True),
        ]
        result = await veo_client.generate_video(prompt="test", output_path=output)
        assert result == output
        assert veo_client.client.models.generate_videos.call_count == 2

    async def test_no_retry_on_value_error(self, veo_client: VeoClient, tmp_path: Path) -> None:
        output = tmp_path / "scene.mp4"
        veo_client.client.models.generate_videos.side_effect = ValueError("bad")
        with pytest.raises(ValueError):
            await veo_client.generate_video(prompt="test", output_path=output)
        assert veo_client.client.models.generate_videos.call_count == 1


class TestVeoClientCost:
    def test_cost_estimation(self, veo_client: VeoClient) -> None:
        assert veo_client.estimate_cost(8, with_audio=True) == pytest.approx(8 * 0.15)
        assert veo_client.estimate_cost(8, with_audio=False) == pytest.approx(8 * 0.10)

    def test_all_models_in_cost_table(self) -> None:
        expected = {"veo-3.1-fast-generate-preview", "veo-3.1-generate-preview",
                    "veo-3.0-fast-generate-001", "veo-3.0-generate-001", "veo-2.0-generate-001"}
        assert set(_COST_PER_SECOND.keys()) == expected
