"""Unit tests for state management (models and manager)."""

from pathlib import Path

from mindmovie.models import CategoryGoal, ExtractedGoals, LifeCategory, MindMovieSpec, Scene
from mindmovie.state import AssetStatus, PipelineStage, PipelineState, SceneAsset, StateManager


def _make_goals() -> ExtractedGoals:
    return ExtractedGoals(
        title="Test Vision", conversation_id="conv-001",
        categories=[
            CategoryGoal(
                category=LifeCategory.HEALTH, vision="Radiant health",
                visual_details="Morning yoga", actions="Yoga", emotions="Peaceful",
            ),
        ],
    )


def _make_scenes() -> MindMovieSpec:
    moods = ["warm", "energetic", "peaceful", "romantic", "confident",
             "joyful", "serene", "warm", "confident", "peaceful"]
    cats = list(LifeCategory)
    return MindMovieSpec(
        scenes=[
            Scene(
                index=i, name=f"test_scene_{i}",
                category=cats[i % len(cats)],
                affirmation=f"I am living my best life scene {i + 1}",
                video_prompt=f"Scene {i}: cinematic shot with camera movement and lighting.",
                mood=moods[i],
            )
            for i in range(10)
        ],
        music_mood="uplifting ambient",
    )


class TestPipelineState:
    def test_defaults_and_resumable(self) -> None:
        state = PipelineState(id="t")
        assert state.current_stage == PipelineStage.QUESTIONNAIRE
        assert state.is_resumable() is True

    def test_pending_videos(self) -> None:
        state = PipelineState(
            id="t",
            scene_assets=[
                SceneAsset(scene_index=0, video_status=AssetStatus.COMPLETE),
                SceneAsset(scene_index=1, video_status=AssetStatus.PENDING),
                SceneAsset(scene_index=2, video_status=AssetStatus.FAILED),
            ],
        )
        assert state.pending_videos() == [1, 2]

    def test_all_videos_complete(self) -> None:
        state = PipelineState(
            id="t",
            scene_assets=[
                SceneAsset(scene_index=0, video_status=AssetStatus.COMPLETE),
                SceneAsset(scene_index=1, video_status=AssetStatus.COMPLETE),
            ],
        )
        assert state.all_videos_complete() is True

    def test_serialization_roundtrip(self) -> None:
        state = PipelineState(
            id="rt", current_stage=PipelineStage.VIDEO_GENERATION,
            scene_assets=[SceneAsset(scene_index=0, video_status=AssetStatus.COMPLETE, video_path="x.mp4")],
        )
        restored = PipelineState.model_validate_json(state.model_dump_json())
        assert restored.id == "rt"
        assert restored.scene_assets[0].video_path == "x.mp4"


class TestStateManager:
    def test_lifecycle(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        assert mgr.exists() is False
        state = mgr.load_or_create()
        mgr.save(state)
        assert mgr.exists() is True

    def test_goals_save_load(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        mgr.save_goals(_make_goals())
        assert mgr.load_goals().title == "Test Vision"

    def test_scenes_save_load(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        mgr.save_scenes(_make_scenes())
        assert len(mgr.load_scenes().scenes) == 10

    def test_stage_transitions(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        state = mgr.complete_questionnaire(_make_goals())
        assert state.current_stage == PipelineStage.SCENE_GENERATION
        state = mgr.complete_scene_generation(_make_scenes())
        assert state.current_stage == PipelineStage.VIDEO_GENERATION
        assert len(state.scene_assets) == 10

    def test_video_status_update(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        mgr.complete_scene_generation(_make_scenes())
        state = mgr.update_video_status(3, AssetStatus.COMPLETE, "scene_03.mp4")
        assert state.get_asset(3).video_status == AssetStatus.COMPLETE

    def test_clear(self, temp_build_dir: Path) -> None:
        mgr = StateManager(str(temp_build_dir))
        mgr.complete_questionnaire(_make_goals())
        mgr.clear()
        assert mgr.exists() is False
