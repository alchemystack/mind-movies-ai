"""State manager for pipeline persistence and resume capability."""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from ..models.goals import ExtractedGoals
from ..models.scenes import MindMovieSpec
from .models import AssetStatus, PipelineStage, PipelineState, SceneAsset


class StateManager:
    """Manages pipeline state for resume capability.

    All intermediate outputs are saved to a build directory as JSON files.
    The pipeline state file tracks which stage has been completed, enabling
    restart from the last successful checkpoint.
    """

    STATE_FILE = "pipeline_state.json"
    GOALS_FILE = "goals.json"
    SCENES_FILE = "scenes.json"

    def __init__(self, build_dir: str = "build") -> None:
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        """Check if resumable state exists on disk."""
        return (self.build_dir / self.STATE_FILE).exists()

    def load_or_create(self) -> PipelineState:
        """Load existing pipeline state or create a fresh one.

        Returns:
            Existing state if found, otherwise a new PipelineState
            with a generated UUID.
        """
        state_path = self.build_dir / self.STATE_FILE
        if state_path.exists():
            data = json.loads(state_path.read_text(encoding="utf-8"))
            return PipelineState.model_validate(data)
        return PipelineState(id=str(uuid.uuid4()))

    def save(self, state: PipelineState) -> None:
        """Persist current state to disk.

        Updates the `updated_at` timestamp before writing.
        """
        state.updated_at = datetime.now()
        state_path = self.build_dir / self.STATE_FILE
        state_path.write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )

    def save_goals(self, goals: ExtractedGoals) -> Path:
        """Save extracted goals to the build directory.

        Returns:
            Path to the saved goals file.
        """
        path = self.build_dir / self.GOALS_FILE
        path.write_text(goals.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_goals(self) -> ExtractedGoals:
        """Load previously saved goals.

        Raises:
            FileNotFoundError: If goals have not been saved yet.
        """
        path = self.build_dir / self.GOALS_FILE
        return ExtractedGoals.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def save_scenes(self, scenes: MindMovieSpec) -> Path:
        """Save generated scene specification to the build directory.

        Returns:
            Path to the saved scenes file.
        """
        path = self.build_dir / self.SCENES_FILE
        path.write_text(scenes.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_scenes(self) -> MindMovieSpec:
        """Load previously saved scenes.

        Raises:
            FileNotFoundError: If scenes have not been saved yet.
        """
        path = self.build_dir / self.SCENES_FILE
        return MindMovieSpec.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def complete_questionnaire(self, goals: ExtractedGoals) -> PipelineState:
        """Mark questionnaire complete, save goals, and advance to scene generation.

        Returns:
            Updated pipeline state at the SCENE_GENERATION stage.
        """
        state = self.load_or_create()
        self.save_goals(goals)
        state.goals_path = str(self.build_dir / self.GOALS_FILE)
        state.current_stage = PipelineStage.SCENE_GENERATION
        self.save(state)
        return state

    def complete_scene_generation(
        self, scenes: MindMovieSpec
    ) -> PipelineState:
        """Mark scene generation complete, save scenes, and initialize asset tracking.

        Creates a SceneAsset tracker for each scene in the spec, then
        advances to the VIDEO_GENERATION stage.

        Returns:
            Updated pipeline state at the VIDEO_GENERATION stage.
        """
        state = self.load_or_create()
        self.save_scenes(scenes)
        state.scenes_path = str(self.build_dir / self.SCENES_FILE)
        state.scene_assets = [
            SceneAsset(scene_index=scene.index) for scene in scenes.scenes
        ]
        state.current_stage = PipelineStage.VIDEO_GENERATION
        self.save(state)
        return state

    def update_video_status(
        self,
        scene_index: int,
        status: AssetStatus,
        video_path: str | None = None,
        error_message: str | None = None,
    ) -> PipelineState:
        """Update video generation status for a specific scene.

        Returns:
            Updated pipeline state.
        """
        state = self.load_or_create()
        asset = state.get_asset(scene_index)
        if asset is None:
            raise ValueError(f"No asset tracker for scene index {scene_index}")
        asset.video_status = status
        if video_path is not None:
            asset.video_path = video_path
        if error_message is not None:
            asset.error_message = error_message
        self.save(state)
        return state

    def advance_stage(self, stage: PipelineStage) -> PipelineState:
        """Advance the pipeline to a specific stage.

        Returns:
            Updated pipeline state.
        """
        state = self.load_or_create()
        state.current_stage = stage
        self.save(state)
        return state

    def clear(self) -> None:
        """Remove all state and generated assets from the build directory.

        Recreates the empty build directory after removal.
        """
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
