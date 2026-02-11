"""Integration tests for the PipelineOrchestrator."""

import json
from collections import deque
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from mindmovie.config.settings import APISettings, Settings
from mindmovie.core.pipeline import PipelineError, PipelineOrchestrator
from mindmovie.core.questionnaire import COMPLETION_MARKER
from mindmovie.models.goals import ExtractedGoals
from mindmovie.models.scenes import MindMovieSpec
from mindmovie.state import AssetStatus, PipelineStage, StateManager

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

SAMPLE_GOALS_JSON = json.dumps({
    "title": "Test Vision",
    "categories": [
        {"category": cat, "vision": "v", "visual_details": "d",
         "actions": "a", "emotions": "e", "skipped": False}
        for cat in ["health", "wealth", "career", "relationships", "growth", "lifestyle"]
    ],
})


@pytest.fixture
def sample_spec(fixtures_dir: Path) -> MindMovieSpec:
    data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
    return MindMovieSpec.model_validate(data)


@pytest.fixture
def sample_goals(fixtures_dir: Path) -> ExtractedGoals:
    data = json.loads((fixtures_dir / "sample_goals.json").read_text())
    return ExtractedGoals.model_validate(data)


@pytest.fixture
def state_manager(temp_build_dir: Path) -> StateManager:
    return StateManager(str(temp_build_dir))


@pytest.fixture
def settings(temp_build_dir: Path) -> Settings:
    s = Settings()
    s.build = s.build.model_copy(update={"build_dir": str(temp_build_dir)})
    # Provide fake API keys so pipeline stages pass validation.
    # Client constructors are mocked in tests that exercise API calls.
    # model_construct bypasses pydantic-settings env loading which would
    # override keyword arguments due to validation_alias precedence.
    s.api = APISettings.model_construct(
        anthropic_api_key=SecretStr("fake-anthropic-key"),
        gemini_api_key=SecretStr("fake-gemini-key"),
        anthropic_model="claude-opus-4-20250514",
    )
    return s


def _completion(goals_json: str = SAMPLE_GOALS_JSON) -> str:
    return f"Great summary!\n\n{COMPLETION_MARKER}\n{goals_json}"


def _mock_anthropic_for_questionnaire(sample_scenes_data: dict) -> AsyncMock:
    """Build a mock AnthropicClient that handles both questionnaire and scene gen."""
    client = AsyncMock()
    chat_responses = deque(["Welcome! Tell me about your health.", _completion()])
    client.chat = AsyncMock(side_effect=lambda **_: chat_responses.popleft())
    client.generate_structured = AsyncMock(return_value=sample_scenes_data)
    return client


async def _fake_generate_video(
    prompt: str, output_path: Path, **kwargs: object
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"fake-video-content")
    return output_path


# ---------------------------------------------------------------------------
# Tests: full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """Test running the pipeline end-to-end with mocked API clients."""

    async def test_full_pipeline_from_scratch(
        self,
        state_manager: StateManager,
        settings: Settings,
        fixtures_dir: Path,
    ) -> None:
        """Pipeline runs all stages from QUESTIONNAIRE to COMPLETE."""
        scenes_data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        mock_client = _mock_anthropic_for_questionnaire(scenes_data)

        mock_video_client = AsyncMock()
        mock_video_client.generate_video = AsyncMock(side_effect=_fake_generate_video)
        mock_video_client.estimate_cost = MagicMock(return_value=0.80)

        user_inputs = deque(["I want to be healthy and fit."])

        output_path = state_manager.build_dir / "test_output.mp4"

        with (
            patch("mindmovie.core.pipeline.AnthropicClient", return_value=mock_client),
            patch("mindmovie.core.pipeline.VeoClient", return_value=mock_video_client),
            patch("mindmovie.core.pipeline.VideoComposer") as mock_composer_cls,
        ):
            mock_composer = MagicMock()
            mock_composer.compose.return_value = output_path
            mock_composer_cls.return_value = mock_composer

            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
                input_fn=lambda: user_inputs.popleft(),
                output_fn=lambda _: None,
                cost_confirm_fn=lambda _breakdown: True,
            )
            result = await orchestrator.run(output_path=output_path)

        assert result == output_path
        state = state_manager.load_or_create()
        assert state.current_stage == PipelineStage.COMPLETE
        assert state.output_path == str(output_path)

    async def test_dry_run_stops_after_cost_estimate(
        self,
        state_manager: StateManager,
        settings: Settings,
        fixtures_dir: Path,
    ) -> None:
        """With dry_run=True, pipeline stops after scene generation."""
        scenes_data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        mock_client = _mock_anthropic_for_questionnaire(scenes_data)

        user_inputs = deque(["I want to be healthy."])

        with patch("mindmovie.core.pipeline.AnthropicClient", return_value=mock_client):
            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
                input_fn=lambda: user_inputs.popleft(),
                output_fn=lambda _: None,
            )
            result = await orchestrator.run(dry_run=True)

        assert result is None
        state = state_manager.load_or_create()
        # Should still be at VIDEO_GENERATION (scene gen completed, cost gate stopped it)
        assert state.current_stage == PipelineStage.VIDEO_GENERATION

    async def test_user_declines_cost(
        self,
        state_manager: StateManager,
        settings: Settings,
        fixtures_dir: Path,
    ) -> None:
        """Pipeline stops when user declines cost confirmation."""
        scenes_data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        mock_client = _mock_anthropic_for_questionnaire(scenes_data)

        user_inputs = deque(["I want health."])

        with patch("mindmovie.core.pipeline.AnthropicClient", return_value=mock_client):
            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
                input_fn=lambda: user_inputs.popleft(),
                output_fn=lambda _: None,
                cost_confirm_fn=lambda _breakdown: False,
            )
            result = await orchestrator.run()

        assert result is None


# ---------------------------------------------------------------------------
# Tests: resume from each stage
# ---------------------------------------------------------------------------

class TestResumeCapability:
    """Test resuming the pipeline from each intermediate stage."""

    async def test_resume_from_scene_generation(
        self,
        state_manager: StateManager,
        settings: Settings,
        sample_goals: ExtractedGoals,
        fixtures_dir: Path,
    ) -> None:
        """Resume from SCENE_GENERATION stage (questionnaire already done)."""
        # Pre-populate state as if questionnaire is complete
        state_manager.complete_questionnaire(sample_goals)

        scenes_data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        mock_client = AsyncMock()
        mock_client.generate_structured = AsyncMock(return_value=scenes_data)

        mock_video_client = AsyncMock()
        mock_video_client.generate_video = AsyncMock(side_effect=_fake_generate_video)
        mock_video_client.estimate_cost = MagicMock(return_value=0.80)

        output_path = state_manager.build_dir / "resumed.mp4"

        with (
            patch("mindmovie.core.pipeline.AnthropicClient", return_value=mock_client),
            patch("mindmovie.core.pipeline.VeoClient", return_value=mock_video_client),
            patch("mindmovie.core.pipeline.VideoComposer") as mock_composer_cls,
        ):
            mock_composer = MagicMock()
            mock_composer.compose.return_value = output_path
            mock_composer_cls.return_value = mock_composer

            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
                cost_confirm_fn=lambda _: True,
            )
            result = await orchestrator.run(output_path=output_path)

        assert result == output_path
        # Questionnaire chat should NOT have been called
        mock_client.chat.assert_not_called()

    async def test_resume_from_video_generation(
        self,
        state_manager: StateManager,
        settings: Settings,
        sample_spec: MindMovieSpec,
    ) -> None:
        """Resume from VIDEO_GENERATION stage (scenes already saved)."""
        state_manager.complete_scene_generation(sample_spec)

        mock_video_client = AsyncMock()
        mock_video_client.generate_video = AsyncMock(side_effect=_fake_generate_video)
        mock_video_client.estimate_cost = MagicMock(return_value=0.80)

        output_path = state_manager.build_dir / "resumed_video.mp4"

        with (
            patch("mindmovie.core.pipeline.VeoClient", return_value=mock_video_client),
            patch("mindmovie.core.pipeline.VideoComposer") as mock_composer_cls,
        ):
            mock_composer = MagicMock()
            mock_composer.compose.return_value = output_path
            mock_composer_cls.return_value = mock_composer

            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
            )
            result = await orchestrator.run(output_path=output_path)

        assert result == output_path
        state = state_manager.load_or_create()
        assert state.current_stage == PipelineStage.COMPLETE

    async def test_resume_from_composition(
        self,
        state_manager: StateManager,
        settings: Settings,
        sample_spec: MindMovieSpec,
    ) -> None:
        """Resume from COMPOSITION stage (all videos done)."""
        state_manager.complete_scene_generation(sample_spec)
        # Mark all videos as complete
        for scene in sample_spec.scenes:
            fake_path = str(state_manager.build_dir / f"scene_{scene.index:02d}.mp4")
            state_manager.update_video_status(
                scene.index, AssetStatus.COMPLETE, video_path=fake_path,
            )
        state_manager.advance_stage(PipelineStage.COMPOSITION)

        output_path = state_manager.build_dir / "resumed_comp.mp4"

        with patch("mindmovie.core.pipeline.VideoComposer") as mock_composer_cls:
            mock_composer = MagicMock()
            mock_composer.compose.return_value = output_path
            mock_composer_cls.return_value = mock_composer

            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
            )
            result = await orchestrator.run(output_path=output_path)

        assert result == output_path
        state = state_manager.load_or_create()
        assert state.current_stage == PipelineStage.COMPLETE

    async def test_resume_when_already_complete(
        self,
        state_manager: StateManager,
        settings: Settings,
    ) -> None:
        """Resume returns existing output path when pipeline is already done."""
        state = state_manager.load_or_create()
        state.current_stage = PipelineStage.COMPLETE
        state.output_path = "/some/output.mp4"
        state_manager.save(state)

        orchestrator = PipelineOrchestrator(
            settings=settings,
            state_manager=state_manager,
        )
        result = await orchestrator.run()

        assert result == Path("/some/output.mp4")


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    async def test_missing_anthropic_key_raises(
        self,
        state_manager: StateManager,
    ) -> None:
        """Pipeline raises PipelineError when ANTHROPIC_API_KEY is empty."""
        # Settings with empty API keys
        settings = Settings()
        settings.build = settings.build.model_copy(
            update={"build_dir": str(state_manager.build_dir)}
        )

        orchestrator = PipelineOrchestrator(
            settings=settings,
            state_manager=state_manager,
            input_fn=lambda: "hello",
            output_fn=lambda _: None,
        )

        with pytest.raises(PipelineError, match="ANTHROPIC_API_KEY"):
            await orchestrator.run()

    async def test_missing_gemini_key_raises(
        self,
        state_manager: StateManager,
        settings: Settings,
        sample_spec: MindMovieSpec,
    ) -> None:
        """Pipeline raises PipelineError when GEMINI_API_KEY is empty at video stage."""
        state_manager.complete_scene_generation(sample_spec)

        # Override gemini key to empty
        from pydantic import SecretStr
        settings.api.gemini_api_key = SecretStr("")

        orchestrator = PipelineOrchestrator(
            settings=settings,
            state_manager=state_manager,
        )

        with pytest.raises(PipelineError, match="GEMINI_API_KEY"):
            await orchestrator.run()

    async def test_video_generation_failure_raises(
        self,
        state_manager: StateManager,
        settings: Settings,
        sample_spec: MindMovieSpec,
    ) -> None:
        """Pipeline raises PipelineError when some videos fail."""
        state_manager.complete_scene_generation(sample_spec)

        mock_video_client = AsyncMock()

        call_count = 0

        async def _fail_first(prompt: str, output_path: Path, **kwargs: object) -> Path:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API timeout")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake-video")
            return output_path

        mock_video_client.generate_video = AsyncMock(side_effect=_fail_first)
        mock_video_client.estimate_cost = MagicMock(return_value=0.80)

        with patch("mindmovie.core.pipeline.VeoClient", return_value=mock_video_client):
            orchestrator = PipelineOrchestrator(
                settings=settings,
                state_manager=state_manager,
            )
            with pytest.raises(PipelineError, match="failed video generation"):
                await orchestrator.run()
