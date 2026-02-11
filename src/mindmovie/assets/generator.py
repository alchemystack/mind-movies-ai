"""Asset generation orchestrator for parallel video generation.

Coordinates the generation of all scene video clips with:
- Semaphore-based concurrency control (respects API rate limits)
- Per-scene state persistence for resume capability
- Rich progress bar integration for CLI feedback
- Aggregated results with success/failure summaries
"""

import asyncio
import logging

from mindmovie.api.base import VideoGeneratorProtocol
from mindmovie.config.settings import Settings
from mindmovie.models.scenes import MindMovieSpec, Scene
from mindmovie.state.manager import StateManager
from mindmovie.state.models import PipelineStage

from .video_generator import SceneVideoGenerator, VideoGenerationResult

logger = logging.getLogger(__name__)


class GenerationSummary:
    """Aggregated results from a full asset generation run."""

    def __init__(self, results: list[VideoGenerationResult]) -> None:
        self.results = results

    @property
    def succeeded(self) -> list[VideoGenerationResult]:
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[VideoGenerationResult]:
        return [r for r in self.results if not r.success]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0

    def format_summary(self) -> str:
        """Format a human-readable summary of generation results."""
        lines = [f"Generated {len(self.succeeded)}/{self.total} videos successfully."]
        if self.failed:
            lines.append("Failed scenes:")
            for r in self.failed:
                lines.append(f"  Scene {r.scene_index}: {r.error}")
        return "\n".join(lines)


class AssetGenerator:
    """Orchestrates parallel video generation for all scenes.

    Uses an asyncio.Semaphore to limit concurrent API calls to the
    configured maximum. Each scene's generation status is tracked
    individually via the StateManager, enabling partial retry on resume.

    Only scenes with PENDING or FAILED status are generated — scenes
    already marked COMPLETE are skipped, supporting resume from any point.
    """

    def __init__(
        self,
        video_client: VideoGeneratorProtocol,
        state_manager: StateManager,
        settings: Settings,
    ) -> None:
        self.video_client = video_client
        self.state_manager = state_manager
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.video.max_concurrent)
        self._scene_generator = SceneVideoGenerator(
            video_client=video_client,
            state_manager=state_manager,
            settings=settings,
        )

    def _get_pending_scenes(self, spec: MindMovieSpec) -> list[Scene]:
        """Identify scenes that need video generation.

        Checks the pipeline state to find scenes with PENDING or FAILED
        status, skipping any that are already COMPLETE.

        Args:
            spec: The mind movie specification with all scenes.

        Returns:
            List of scenes that need generation.
        """
        state = self.state_manager.load_or_create()
        pending_indices = set(state.pending_videos())

        return [
            scene for scene in spec.scenes
            if scene.index in pending_indices
        ]

    async def _generate_with_semaphore(
        self,
        scene: Scene,
        progress_callback: object | None = None,
    ) -> VideoGenerationResult:
        """Generate a single scene's video, guarded by the semaphore.

        Args:
            scene: The scene to generate a video for.
            progress_callback: Optional callable invoked after completion
                (used by the CLI to advance the progress bar).

        Returns:
            VideoGenerationResult for this scene.
        """
        async with self._semaphore:
            result = await self._scene_generator.generate(scene)

        if progress_callback is not None and callable(progress_callback):
            progress_callback()

        return result

    async def generate_all(
        self,
        spec: MindMovieSpec,
        progress_callback: object | None = None,
    ) -> GenerationSummary:
        """Generate video clips for all pending scenes in parallel.

        Launches all pending scene tasks concurrently, bounded by the
        semaphore. Advances the pipeline stage to COMPOSITION if all
        videos complete successfully.

        Args:
            spec: The mind movie specification.
            progress_callback: Optional callable invoked after each scene
                completes (used by the CLI progress bar).

        Returns:
            GenerationSummary with per-scene results.
        """
        pending_scenes = self._get_pending_scenes(spec)

        if not pending_scenes:
            logger.info("No pending scenes to generate — all videos complete.")
            return GenerationSummary(results=[])

        logger.info(
            "Starting video generation for %d scenes (max %d concurrent)",
            len(pending_scenes),
            self.settings.video.max_concurrent,
        )

        tasks = [
            self._generate_with_semaphore(scene, progress_callback)
            for scene in pending_scenes
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        summary = GenerationSummary(results=list(results))

        # Advance to composition if all scene videos are now complete
        state = self.state_manager.load_or_create()
        if state.all_videos_complete():
            self.state_manager.advance_stage(PipelineStage.COMPOSITION)
            logger.info("All videos complete — advanced to COMPOSITION stage.")
        else:
            logger.warning(
                "%d of %d scenes failed video generation.",
                len(summary.failed),
                summary.total,
            )

        return summary
