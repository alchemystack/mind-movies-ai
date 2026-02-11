"""Single-scene video generation with state tracking.

Wraps a VideoGeneratorProtocol client to generate one scene's video clip
while updating the pipeline state before and after generation. This
per-scene wrapper is called by the AssetGenerator orchestrator for each
scene in the mind movie specification.
"""

import logging
from pathlib import Path

from mindmovie.api.base import VideoGeneratorProtocol
from mindmovie.config.settings import Settings
from mindmovie.models.scenes import Scene
from mindmovie.state.manager import StateManager
from mindmovie.state.models import AssetStatus

logger = logging.getLogger(__name__)


class VideoGenerationResult:
    """Result of a single scene video generation attempt."""

    def __init__(
        self,
        scene_index: int,
        success: bool,
        video_path: Path | None = None,
        error: str | None = None,
    ) -> None:
        self.scene_index = scene_index
        self.success = success
        self.video_path = video_path
        self.error = error


class SceneVideoGenerator:
    """Generates a video clip for a single scene with state persistence.

    Marks the scene as GENERATING before starting, then updates to
    COMPLETE or FAILED based on the outcome. State is saved to disk
    after each transition so the pipeline can resume on interruption.
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

    def _video_output_path(self, scene_index: int) -> Path:
        """Build the output path for a scene's video file."""
        return Path(self.settings.build_dir) / f"scene_{scene_index:02d}.mp4"

    async def generate(self, scene: Scene) -> VideoGenerationResult:
        """Generate a video clip for a single scene.

        Updates pipeline state to GENERATING before the API call, then
        to COMPLETE or FAILED afterward. The state is persisted to disk
        at each transition.

        Args:
            scene: The scene specification containing the video prompt.

        Returns:
            VideoGenerationResult indicating success/failure and file path.
        """
        output_path = self._video_output_path(scene.index)

        # Mark as generating
        self.state_manager.update_video_status(
            scene_index=scene.index,
            status=AssetStatus.GENERATING,
        )

        logger.info(
            "Generating video for scene %d [%s]: %s",
            scene.index,
            scene.category,
            scene.affirmation,
        )

        try:
            result_path = await self.video_client.generate_video(
                prompt=scene.video_prompt,
                output_path=output_path,
                duration=self.settings.movie.scene_duration,
                resolution=self.settings.video.resolution,
                aspect_ratio=self.settings.video.aspect_ratio,
                generate_audio=self.settings.video.generate_audio,
            )

            # Mark as complete
            self.state_manager.update_video_status(
                scene_index=scene.index,
                status=AssetStatus.COMPLETE,
                video_path=str(result_path),
            )

            logger.info("Scene %d video saved to %s", scene.index, result_path)
            return VideoGenerationResult(
                scene_index=scene.index,
                success=True,
                video_path=result_path,
            )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error("Scene %d video generation failed: %s", scene.index, error_msg)

            # Mark as failed
            self.state_manager.update_video_status(
                scene_index=scene.index,
                status=AssetStatus.FAILED,
                error_message=error_msg,
            )

            return VideoGenerationResult(
                scene_index=scene.index,
                success=False,
                error=error_msg,
            )
