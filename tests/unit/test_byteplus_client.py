"""Unit tests for BytePlus Seedance video generation client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mindmovie.api.byteplus_client import (
    _COST_PER_SECOND_AUDIO,
    _COST_PER_SECOND_NO_AUDIO,
    BytePlusClient,
)


def _make_task_id(task_id: str = "task-123") -> MagicMock:
    """Create a mock ContentGenerationTaskID."""
    ref = MagicMock()
    ref.id = task_id
    return ref


def _make_task(
    status: str = "succeeded",
    video_url: str = "https://example.com/video.mp4",
    error_message: str = "",
    error_code: str = "",
) -> MagicMock:
    """Create a mock ContentGenerationTask."""
    task = MagicMock()
    task.status = status
    task.error = MagicMock()
    task.error.message = error_message
    task.error.code = error_code
    task.content = MagicMock()
    task.content.video_url = video_url
    return task


@pytest.fixture
def mock_ark_client() -> MagicMock:
    client = MagicMock()
    client.content_generation = MagicMock()
    client.content_generation.tasks = MagicMock()
    return client


@pytest.fixture
def bp_client(mock_ark_client: MagicMock) -> BytePlusClient:
    with patch("mindmovie.api.byteplus_client.Ark") as mock_ark:
        mock_ark.return_value = mock_ark_client
        client = BytePlusClient(api_key="test-key", poll_interval=0)
    return client


@pytest.fixture
def bp_client_no_audio(mock_ark_client: MagicMock) -> BytePlusClient:
    with patch("mindmovie.api.byteplus_client.Ark") as mock_ark:
        mock_ark.return_value = mock_ark_client
        client = BytePlusClient(
            api_key="test-key", poll_interval=0, generate_audio=False
        )
    return client


class TestBytePlusClientGenerate:
    async def test_generate_video_returns_path(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Happy path: create -> poll (immediate success) -> download -> return."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.return_value = _make_task()

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            result = await bp_client.generate_video(prompt="test", output_path=output)

        assert result == output

    async def test_polls_until_succeeded(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Task starts running, then succeeds on second poll."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.side_effect = [
            _make_task(status="running"),
            _make_task(status="succeeded"),
        ]

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            await bp_client.generate_video(prompt="test", output_path=output)

        assert bp_client.client.content_generation.tasks.get.call_count == 2

    async def test_polls_through_queued_and_running(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Task transitions queued -> running -> succeeded."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.side_effect = [
            _make_task(status="queued"),
            _make_task(status="running"),
            _make_task(status="succeeded"),
        ]

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            await bp_client.generate_video(prompt="test", output_path=output)

        assert bp_client.client.content_generation.tasks.get.call_count == 3

    async def test_failed_task_raises_runtime_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Failed task raises RuntimeError with error message."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.return_value = _make_task(
            status="failed", error_message="Content policy violation"
        )

        with pytest.raises(RuntimeError, match="Content policy violation"):
            await bp_client.generate_video(prompt="test", output_path=output)

    async def test_cancelled_task_raises_runtime_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Cancelled task raises RuntimeError."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.return_value = _make_task(
            status="cancelled"
        )

        with pytest.raises(RuntimeError, match="cancelled"):
            await bp_client.generate_video(prompt="test", output_path=output)

    async def test_no_video_url_raises_runtime_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Succeeded task with empty video URL raises RuntimeError."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.return_value = _make_task(
            video_url=""
        )

        with pytest.raises(RuntimeError, match="no video URL"):
            await bp_client.generate_video(prompt="test", output_path=output)


class TestBytePlusClientRetry:
    async def test_retries_on_connection_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.side_effect = [
            ConnectionError("fail"),
            _make_task_id(),
        ]
        bp_client.client.content_generation.tasks.get.return_value = _make_task()

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            result = await bp_client.generate_video(prompt="test", output_path=output)

        assert result == output
        assert bp_client.client.content_generation.tasks.create.call_count == 2

    async def test_retries_on_timeout_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.side_effect = [
            TimeoutError("timeout"),
            _make_task_id(),
        ]
        bp_client.client.content_generation.tasks.get.return_value = _make_task()

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            result = await bp_client.generate_video(prompt="test", output_path=output)

        assert result == output

    async def test_no_retry_on_value_error(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.side_effect = ValueError("bad")

        with pytest.raises(ValueError):
            await bp_client.generate_video(prompt="test", output_path=output)

        assert bp_client.client.content_generation.tasks.create.call_count == 1


class TestBytePlusClientConfig:
    """Tests for correct API parameters passed to BytePlus."""

    async def test_passes_sdk_params_directly(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Verify resolution, ratio, duration, generate_audio are passed as SDK kwargs."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id()
        bp_client.client.content_generation.tasks.get.return_value = _make_task()

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            await bp_client.generate_video(
                prompt="a golden sunset", output_path=output,
                duration=5, resolution="720p", aspect_ratio="16:9",
            )

        call_kwargs = bp_client.client.content_generation.tasks.create.call_args.kwargs
        assert call_kwargs["resolution"] == "720p"
        assert call_kwargs["ratio"] == "16:9"
        assert call_kwargs["duration"] == 5
        assert call_kwargs["generate_audio"] is True
        assert call_kwargs["content"] == [{"type": "text", "text": "a golden sunset"}]

    async def test_audio_disabled(
        self, bp_client_no_audio: BytePlusClient, tmp_path: Path
    ) -> None:
        """Verify generate_audio=False is passed through."""
        output = tmp_path / "scene.mp4"
        bp_client_no_audio.client.content_generation.tasks.create.return_value = (
            _make_task_id()
        )
        bp_client_no_audio.client.content_generation.tasks.get.return_value = (
            _make_task()
        )

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            await bp_client_no_audio.generate_video(prompt="test", output_path=output)

        call_kwargs = (
            bp_client_no_audio.client.content_generation.tasks.create.call_args.kwargs
        )
        assert call_kwargs["generate_audio"] is False

    async def test_task_id_passed_to_poll(
        self, bp_client: BytePlusClient, tmp_path: Path
    ) -> None:
        """Verify the task ID from create is used for polling."""
        output = tmp_path / "scene.mp4"
        bp_client.client.content_generation.tasks.create.return_value = _make_task_id(
            task_id="my-task-42"
        )
        bp_client.client.content_generation.tasks.get.return_value = _make_task()

        with patch("mindmovie.api.byteplus_client.urllib.request.urlretrieve"):
            await bp_client.generate_video(prompt="test", output_path=output)

        call_kwargs = bp_client.client.content_generation.tasks.get.call_args.kwargs
        assert call_kwargs["task_id"] == "my-task-42"


class TestBytePlusClientCost:
    def test_cost_estimation_with_audio(self, bp_client: BytePlusClient) -> None:
        # Default rate: $0.026/s with audio
        assert bp_client.estimate_cost(8) == pytest.approx(8 * 0.026)

    def test_cost_estimation_without_audio(
        self, bp_client_no_audio: BytePlusClient
    ) -> None:
        # Rate without audio: $0.013/s
        assert bp_client_no_audio.estimate_cost(8) == pytest.approx(8 * 0.013)

    def test_cost_tables_have_default_model(self) -> None:
        assert "seedance-1-5-pro-251215" in _COST_PER_SECOND_AUDIO
        assert "seedance-1-5-pro-251215" in _COST_PER_SECOND_NO_AUDIO

    def test_cost_unknown_model_falls_back(self) -> None:
        """Unknown model uses the default model's rate."""
        with patch("mindmovie.api.byteplus_client.Ark"):
            client = BytePlusClient(api_key="k", model="future-model-v99")
        cost = client.estimate_cost(10)
        assert cost == pytest.approx(10 * 0.026)
