"""Unit tests for the SceneGenerator."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from mindmovie.core.scene_generator import GENERATION_PROMPT, SceneGenerator, _unwrap_llm_result
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


class TestUnwrapLLMResult:
    def test_unwraps_output_envelope(self) -> None:
        data = {"title": "Test", "scenes": []}
        wrapped = {"output": data}
        assert _unwrap_llm_result(wrapped) == data

    def test_passes_through_flat_response(self) -> None:
        data = {"title": "Test", "scenes": []}
        assert _unwrap_llm_result(data) == data

    def test_ignores_non_dict_output(self) -> None:
        data = {"output": "not a dict", "title": "Test"}
        assert _unwrap_llm_result(data) == data


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

    async def test_generate_handles_wrapped_response(
        self, sample_scenes_data: dict, sample_goals: ExtractedGoals,
    ) -> None:
        """Reproduces the real bug: Claude wraps tool output in {"output": {...}}."""
        client = AsyncMock()
        client.generate_structured = AsyncMock(return_value={"output": sample_scenes_data})
        gen = SceneGenerator(client=client)
        result = await gen.generate(sample_goals)
        assert isinstance(result, MindMovieSpec)
        assert 10 <= len(result.scenes) <= 15

    async def test_generate_raises_on_invalid_response(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        client = AsyncMock()
        client.generate_structured = AsyncMock(return_value={"title": "Test"})
        gen = SceneGenerator(client=client)
        with pytest.raises(ValidationError):
            await gen.generate(sample_goals)


class TestBuildUserMessage:
    def test_includes_appearance_when_present(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        gen = SceneGenerator(client=AsyncMock())
        msg = gen._build_user_message(sample_goals)
        assert "## Subject Appearance" in msg
        assert sample_goals.appearance.description in msg  # type: ignore[union-attr]

    def test_includes_initial_vision_when_present(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        gen = SceneGenerator(client=AsyncMock())
        msg = gen._build_user_message(sample_goals)
        assert "## Initial Vision Summary" in msg
        assert sample_goals.initial_vision in msg  # type: ignore[operator]

    def test_omits_appearance_when_absent(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        sample_goals.appearance = None
        gen = SceneGenerator(client=AsyncMock())
        msg = gen._build_user_message(sample_goals)
        assert "## Subject Appearance" not in msg

    def test_omits_initial_vision_when_absent(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        sample_goals.initial_vision = None
        gen = SceneGenerator(client=AsyncMock())
        msg = gen._build_user_message(sample_goals)
        assert "## Initial Vision Summary" not in msg

    def test_appearance_precedes_categories(
        self, sample_goals: ExtractedGoals,
    ) -> None:
        gen = SceneGenerator(client=AsyncMock())
        msg = gen._build_user_message(sample_goals)
        appearance_pos = msg.index("## Subject Appearance")
        first_category_pos = msg.index("## Health")
        assert appearance_pos < first_category_pos


class TestGenerationPrompt:
    def test_prompt_mentions_subject_appearance(self) -> None:
        assert "SUBJECT APPEARANCE" in GENERATION_PROMPT

    def test_prompt_mentions_initial_vision(self) -> None:
        assert "INITIAL VISION" in GENERATION_PROMPT

    def test_prompt_forbids_speech(self) -> None:
        assert "NO SPEECH" in GENERATION_PROMPT

    def test_prompt_requires_visual_only(self) -> None:
        assert "VISUAL-ONLY" in GENERATION_PROMPT

    def test_prompt_addresses_video_model_achievability(self) -> None:
        assert "KEEP IT SIMPLE AND ACHIEVABLE" in GENERATION_PROMPT

    def test_prompt_prioritizes_emotion(self) -> None:
        assert "EMOTIONAL EXPRESSIVENESS" in GENERATION_PROMPT

    def test_prompt_requires_photorealism(self) -> None:
        assert "PHOTOREALISTIC" in GENERATION_PROMPT

    def test_prompt_references_camera_technique(self) -> None:
        assert "CAMERA-FIRST" in GENERATION_PROMPT


class TestFixtureValidation:
    def test_fixture_scenes_validate(self, sample_scenes_data: dict) -> None:
        spec = MindMovieSpec.model_validate(sample_scenes_data)
        assert len(spec.scenes) == 12
        indices = [s.index for s in spec.scenes]
        assert indices == list(range(12))
