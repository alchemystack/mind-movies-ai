"""Integration tests for the asset generation orchestrator."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mindmovie.assets import AssetGenerator, GenerationSummary
from mindmovie.assets.video_generator import VideoGenerationResult
from mindmovie.config.settings import Settings
from mindmovie.models.scenes import MindMovieSpec
from mindmovie.state import AssetStatus, PipelineStage, StateManager


@pytest.fixture
def sample_spec(fixtures_dir: Path) -> MindMovieSpec:
    data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
    return MindMovieSpec.model_validate(data)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def state_manager(temp_build_dir: Path) -> StateManager:
    return StateManager(str(temp_build_dir))


@pytest.fixture
def mock_video_client() -> AsyncMock:
    client = AsyncMock()

    async def fake_generate(prompt: str, output_path: Path, **kwargs: object) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-video")
        return output_path

    client.generate_video = AsyncMock(side_effect=fake_generate)
    client.estimate_cost = MagicMock(return_value=0.80)
    return client


def _setup(sm: StateManager, spec: MindMovieSpec) -> None:
    sm.save_scenes(spec)
    sm.complete_scene_generation(spec)


class TestAssetGenerator:
    async def test_generates_all_and_advances(
        self, mock_video_client: AsyncMock, state_manager: StateManager,
        settings: Settings, sample_spec: MindMovieSpec,
    ) -> None:
        _setup(state_manager, sample_spec)
        settings.build = settings.build.model_copy(update={"build_dir": str(state_manager.build_dir)})
        gen = AssetGenerator(mock_video_client, state_manager, settings)
        summary = await gen.generate_all(sample_spec)
        assert summary.all_succeeded is True
        assert summary.total == len(sample_spec.scenes)
        state = state_manager.load_or_create()
        assert state.current_stage == PipelineStage.COMPOSITION

    async def test_skips_complete_scenes(
        self, mock_video_client: AsyncMock, state_manager: StateManager,
        settings: Settings, sample_spec: MindMovieSpec,
    ) -> None:
        _setup(state_manager, sample_spec)
        settings.build = settings.build.model_copy(update={"build_dir": str(state_manager.build_dir)})
        state_manager.update_video_status(0, AssetStatus.COMPLETE, "s0.mp4")
        state_manager.update_video_status(1, AssetStatus.COMPLETE, "s1.mp4")
        gen = AssetGenerator(mock_video_client, state_manager, settings)
        summary = await gen.generate_all(sample_spec)
        assert summary.total == len(sample_spec.scenes) - 2


class TestGenerationSummary:
    def test_all_succeeded(self) -> None:
        results = [
            VideoGenerationResult(scene_index=0, success=True, video_path=Path("a.mp4")),
        ]
        s = GenerationSummary(results)
        assert s.all_succeeded is True
        assert s.total == 1

    def test_partial_failure(self) -> None:
        results = [
            VideoGenerationResult(scene_index=0, success=True, video_path=Path("a.mp4")),
            VideoGenerationResult(scene_index=1, success=False, error="Boom"),
        ]
        s = GenerationSummary(results)
        assert s.all_succeeded is False
        assert len(s.failed) == 1
