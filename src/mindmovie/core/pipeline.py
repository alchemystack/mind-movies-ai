"""Pipeline orchestrator for end-to-end mind movie generation.

Chains the four pipeline stages — questionnaire, scene generation,
video generation, and composition — with checkpointed state after
each stage so the pipeline can resume from the last successful step.
"""

import logging
from pathlib import Path
from typing import Any

from mindmovie.api.anthropic_client import AnthropicClient
from mindmovie.api.veo_client import VeoClient
from mindmovie.assets import AssetGenerator
from mindmovie.config.settings import Settings
from mindmovie.core.cost_estimator import CostEstimator
from mindmovie.core.questionnaire import QuestionnaireEngine
from mindmovie.core.scene_generator import SceneGenerator
from mindmovie.models.scenes import MindMovieSpec
from mindmovie.state import PipelineStage, StateManager
from mindmovie.video import CompositionError, VideoComposer

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when a pipeline stage fails unrecoverably."""


class PipelineOrchestrator:
    """Orchestrates the full mind movie generation pipeline.

    Each stage delegates to the corresponding engine or generator,
    persisting state after completion so the pipeline can resume
    from any checkpoint.

    Args:
        settings: Resolved application settings.
        state_manager: Manages pipeline state persistence.
        input_fn: Callable for reading user text input (questionnaire).
        output_fn: Callable for displaying assistant messages (questionnaire).
        cost_confirm_fn: Callable that receives a ``CostBreakdown`` and returns
            ``True`` if the user accepts the estimated cost.
        progress_callback: Called once per completed video generation.
    """

    def __init__(
        self,
        settings: Settings,
        state_manager: StateManager,
        *,
        input_fn: Any | None = None,
        output_fn: Any | None = None,
        cost_confirm_fn: Any | None = None,
        progress_callback: Any | None = None,
    ) -> None:
        self.settings = settings
        self.state_manager = state_manager
        self._input_fn = input_fn
        self._output_fn = output_fn
        self._cost_confirm_fn = cost_confirm_fn
        self._progress_callback = progress_callback

    async def run(
        self,
        *,
        output_path: Path | None = None,
        music_path: Path | None = None,
        dry_run: bool = False,
    ) -> Path | None:
        """Execute the pipeline from the current stage to completion.

        Resumes from whatever ``current_stage`` the persisted state holds.
        Each stage transitions atomically — state is saved *after* the stage
        succeeds, so a crash at any point simply restarts from the last
        checkpoint.

        Args:
            output_path: Override for the final MP4 output path.
            music_path: Override for the background music file.
            dry_run: If ``True``, stop after cost estimation (no API calls
                beyond the questionnaire and scene generation).

        Returns:
            Path to the final MP4, or ``None`` if the run was a dry-run
            or was cancelled by the user at the cost confirmation prompt.
        """
        state = self.state_manager.load_or_create()

        # --- Stage: Questionnaire ---
        if state.current_stage == PipelineStage.QUESTIONNAIRE:
            logger.info("Pipeline stage: QUESTIONNAIRE")
            await self._run_questionnaire()
            state = self.state_manager.load_or_create()

        # --- Stage: Scene Generation ---
        if state.current_stage == PipelineStage.SCENE_GENERATION:
            logger.info("Pipeline stage: SCENE_GENERATION")
            spec = await self._run_scene_generation()
            state = self.state_manager.load_or_create()

            # Cost estimation and confirmation gate
            cancelled = self._confirm_cost(spec, dry_run=dry_run)
            if cancelled:
                return None
        else:
            spec = None

        # --- Stage: Video Generation ---
        if state.current_stage == PipelineStage.VIDEO_GENERATION:
            logger.info("Pipeline stage: VIDEO_GENERATION")
            if spec is None:
                spec = self.state_manager.load_scenes()
            await self._run_video_generation(spec)
            state = self.state_manager.load_or_create()

        # --- Stage: Composition ---
        if state.current_stage == PipelineStage.COMPOSITION:
            logger.info("Pipeline stage: COMPOSITION")
            if spec is None:
                spec = self.state_manager.load_scenes()
            result = self._run_composition(spec, output_path, music_path)
            return result

        # Already complete
        if state.current_stage == PipelineStage.COMPLETE:
            logger.info("Pipeline already complete.")
            return Path(state.output_path) if state.output_path else None

        return None

    # ------------------------------------------------------------------
    # Individual stage runners
    # ------------------------------------------------------------------

    async def _run_questionnaire(self) -> None:
        """Run the interactive questionnaire and persist goals."""
        if not self.settings.api.anthropic_api_key.get_secret_value():
            raise PipelineError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your .env file or environment variables."
            )

        client = AnthropicClient(
            api_key=self.settings.api.anthropic_api_key.get_secret_value(),
            model=self.settings.api.anthropic_model,
        )
        engine = QuestionnaireEngine(
            client=client,
            input_fn=self._input_fn,
            output_fn=self._output_fn,
        )
        goals = await engine.run()
        self.state_manager.complete_questionnaire(goals)
        logger.info(
            "Questionnaire complete — %d categories extracted.",
            goals.category_count,
        )

    async def _run_scene_generation(self) -> MindMovieSpec:
        """Generate scenes from persisted goals and save them."""
        if not self.settings.api.anthropic_api_key.get_secret_value():
            raise PipelineError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your .env file or environment variables."
            )

        goals = self.state_manager.load_goals()
        client = AnthropicClient(
            api_key=self.settings.api.anthropic_api_key.get_secret_value(),
            model=self.settings.api.anthropic_model,
        )
        generator = SceneGenerator(
            client=client, num_scenes=self.settings.movie.num_scenes
        )
        spec = await generator.generate(goals)
        self.state_manager.complete_scene_generation(spec)
        logger.info("Scene generation complete — %d scenes.", len(spec.scenes))
        return spec

    def _confirm_cost(
        self, spec: MindMovieSpec, *, dry_run: bool
    ) -> bool:
        """Estimate cost and ask for user confirmation.

        Returns ``True`` if the pipeline should **stop** (dry-run or
        user declined).
        """
        estimator = CostEstimator(self.settings)
        breakdown = estimator.estimate(spec)

        # Persist estimated cost
        state = self.state_manager.load_or_create()
        state.estimated_cost = breakdown.total_cost
        self.state_manager.save(state)

        if dry_run:
            logger.info("Dry run — stopping after cost estimate.")
            return True

        if self._cost_confirm_fn is not None:
            accepted = self._cost_confirm_fn(breakdown)
            if not accepted:
                logger.info("User declined cost estimate.")
                return True

        return False

    async def _run_video_generation(self, spec: MindMovieSpec) -> None:
        """Generate video clips for all pending scenes."""
        if not self.settings.api.gemini_api_key.get_secret_value():
            raise PipelineError(
                "GEMINI_API_KEY is not set. "
                "Set it in your .env file or environment variables."
            )

        video_client = VeoClient(
            api_key=self.settings.api.gemini_api_key.get_secret_value(),
            model=self.settings.video.model,
        )
        generator = AssetGenerator(
            video_client=video_client,
            state_manager=self.state_manager,
            settings=self.settings,
        )
        summary = await generator.generate_all(
            spec, progress_callback=self._progress_callback
        )

        if not summary.all_succeeded:
            failed_count = len(summary.failed)
            logger.warning(
                "%d of %d scenes failed video generation.",
                failed_count,
                summary.total,
            )
            raise PipelineError(
                f"{failed_count} scene(s) failed video generation. "
                "Run 'mindmovie generate --resume' to retry."
            )

        logger.info("All %d scene videos generated.", summary.total)

    def _run_composition(
        self,
        spec: MindMovieSpec,
        output_path: Path | None,
        music_path: Path | None,
    ) -> Path:
        """Compose the final mind movie video."""
        state = self.state_manager.load_or_create()
        resolved_output = output_path or Path(self.settings.output_path)

        composer = VideoComposer(
            movie_settings=self.settings.movie,
            music_settings=self.settings.music,
            resolution=self.settings.video.resolution,
            aspect_ratio=self.settings.video.aspect_ratio,
        )

        try:
            result = composer.compose(
                spec=spec,
                state=state,
                output_path=resolved_output,
                music_path=music_path,
            )
        except CompositionError:
            raise
        except Exception as exc:
            raise PipelineError(f"Composition failed: {exc}") from exc

        # Mark pipeline complete
        state = self.state_manager.load_or_create()
        state.output_path = str(result)
        state.current_stage = PipelineStage.COMPLETE
        self.state_manager.save(state)
        logger.info("Pipeline complete — output: %s", result)
        return result
