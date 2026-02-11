"""Unit tests for the SceneGenerator."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from mindmovie.core.scene_generator import SceneGenerator
from mindmovie.models.goals import ExtractedGoals
from mindmovie.models.scenes import MindMovieSpec


@pytest.fixture
def sample_goals(fixtures_dir: Path) -> ExtractedGoals:
    with open(fixtures_dir / "sample_goals.json") as f:
        return ExtractedGoals.model_validate(json.load(f))


@pytest.fixture
def sample_scenes_data(fixtures_dir: Path) -> dict:
    with open(fixtures_dir / "sample_scenes.json") as f:
        return json.load(f)


@pytest.fixture
def mock_client(sample_scenes_data: dict) -> AsyncMock:
    client = AsyncMock()
    client.generate_structured = AsyncMock(return_value=sample_scenes_data)
    return client


class TestSceneGenerator:
    def test_num_scenes_clamped(self) -> None:
        assert SceneGenerator(client=AsyncMock(), num_scenes=5).num_scenes == 10
        assert SceneGenerator(client=AsyncMock(), num_scenes=20).num_scenes == 15

    async def test_generate_returns_valid_spec(
        self, mock_client: AsyncMock, sample_goals: ExtractedGoals,
    ) -> None:
        gen = SceneGenerator(client=mock_client)
        result = await gen.generate(sample_goals)
        assert isinstance(result, MindMovieSpec)
        assert 10 <= len(result.scenes) <= 15
        assert result.title
        assert result.music_mood

    async def test_generate_raises_on_invalid_response(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        client = AsyncMock()
        client.generate_structured = AsyncMock(return_value={"title": "Test"})
        gen = SceneGenerator(client=client)
        with pytest.raises(ValidationError):
            await gen.generate(sample_goals)


class TestFixtureValidation:
    def test_fixture_scenes_validate(self, sample_scenes_data: dict) -> None:
        spec = MindMovieSpec.model_validate(sample_scenes_data)
        assert len(spec.scenes) == 12
        indices = [s.index for s in spec.scenes]
        assert indices == list(range(12))
