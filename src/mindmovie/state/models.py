"""State models for pipeline persistence and resume capability."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PipelineStage(StrEnum):
    """Pipeline execution stages in order."""

    QUESTIONNAIRE = "questionnaire"
    SCENE_GENERATION = "scene_generation"
    VIDEO_GENERATION = "video_generation"
    COMPOSITION = "composition"
    COMPLETE = "complete"


class AssetStatus(StrEnum):
    """Status of an individual generated asset."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


class SceneAsset(BaseModel):
    """Tracking for a single scene's generated assets."""

    scene_index: int = Field(..., ge=0, description="Index of the scene this asset belongs to")
    video_status: AssetStatus = Field(
        default=AssetStatus.PENDING, description="Video generation status"
    )
    video_path: str | None = Field(
        default=None, description="Path to generated video file"
    )
    error_message: str | None = Field(
        default=None, description="Error message if generation failed"
    )


class PipelineState(BaseModel):
    """Complete pipeline state for resume capability.

    Persisted to disk after each stage transition, enabling the pipeline
    to resume from the last successful checkpoint if interrupted.
    """

    id: str = Field(..., description="Unique pipeline run ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    current_stage: PipelineStage = Field(default=PipelineStage.QUESTIONNAIRE)

    # Stage output paths
    goals_path: str | None = Field(
        default=None, description="Path to saved goals JSON"
    )
    scenes_path: str | None = Field(
        default=None, description="Path to saved scenes JSON"
    )
    music_path: str | None = Field(
        default=None, description="Path to background music file"
    )
    output_path: str | None = Field(
        default=None, description="Path to final output video"
    )

    # Per-scene asset tracking
    scene_assets: list[SceneAsset] = Field(default_factory=list)

    # Cost tracking
    estimated_cost: float = Field(default=0.0, ge=0.0)
    actual_cost: float = Field(default=0.0, ge=0.0)

    def is_resumable(self) -> bool:
        """Check if pipeline can be resumed (not yet complete)."""
        return self.current_stage != PipelineStage.COMPLETE

    def pending_videos(self) -> list[int]:
        """Get scene indices that still need video generation."""
        return [
            a.scene_index
            for a in self.scene_assets
            if a.video_status in (AssetStatus.PENDING, AssetStatus.FAILED)
        ]

    def get_asset(self, scene_index: int) -> SceneAsset | None:
        """Get the asset tracker for a specific scene index."""
        for asset in self.scene_assets:
            if asset.scene_index == scene_index:
                return asset
        return None

    def all_videos_complete(self) -> bool:
        """Check if all scene videos have been generated."""
        return all(
            a.video_status == AssetStatus.COMPLETE for a in self.scene_assets
        )

