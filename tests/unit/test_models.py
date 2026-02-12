"""Unit tests for Pydantic data models."""

import pytest

from mindmovie.models import ExtractedGoals, LifeCategory, MindMovieSpec, Scene
from mindmovie.models.goals import CategoryGoal


class TestGoalModels:
    def test_active_categories(self) -> None:
        goals = ExtractedGoals(
            title="Test", conversation_id="cid",
            categories=[
                CategoryGoal(
                    category=LifeCategory.HEALTH, vision="v",
                    visual_details="d", actions="a", emotions="e",
                ),
                CategoryGoal(
                    category=LifeCategory.CAREER, vision="",
                    visual_details="", actions="", emotions="", skipped=True,
                ),
            ],
        )
        assert goals.category_count == 1
        assert len(goals.active_categories) == 1

    def test_serialization_roundtrip(self) -> None:
        goals = ExtractedGoals(
            title="T", conversation_id="c",
            categories=[
                CategoryGoal(
                    category=LifeCategory.WEALTH, vision="v",
                    visual_details="d", actions="a", emotions="e",
                ),
            ],
        )
        restored = ExtractedGoals.model_validate_json(goals.model_dump_json())
        assert restored.title == "T"


class TestSceneModels:
    def _make_scene(self, **overrides: object) -> Scene:
        defaults = {
            "index": 0, "name": "coastal_sunrise_run",
            "category": LifeCategory.HEALTH,
            "affirmation": "I am radiantly healthy and full of energy",
            "video_prompt": "A person runs along a coastal trail at sunrise with warm cinematic lighting and tracking camera movement.",
            "mood": "energetic",
        }
        defaults.update(overrides)
        return Scene(**defaults)

    def test_valid_scene(self) -> None:
        s = self._make_scene()
        assert s.index == 0

    def test_non_first_person_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be first-person"):
            self._make_scene(affirmation="My life is amazing and beautiful today")

    def test_valid_first_person_affirmations(self) -> None:
        for affirmation in [
            "I am great and healthy",
            "I have abundance in life",
            "I feel strong every day",
            "I live freely and joyfully",
            "I lead groundbreaking research",
            "I dance with amazing friends",
            "I work with brilliant innovators",
            "I embrace challenges with calm",
        ]:
            self._make_scene(affirmation=affirmation, video_prompt="A" * 50)


class TestMindMovieSpec:
    def _make_spec(self, n: int = 10) -> MindMovieSpec:
        all_moods = ["warm", "energetic", "peaceful", "romantic", "confident",
                     "joyful", "serene"]
        cats = list(LifeCategory)
        return MindMovieSpec(
            scenes=[
                Scene(
                    index=i, name=f"test_scene_{i}",
                    category=cats[i % len(cats)],
                    affirmation=f"I am living my best life scene {i + 1}",
                    video_prompt=f"Scene {i}: cinematic shot with beautiful lighting and camera movement through setting.",
                    mood=all_moods[i % len(all_moods)],
                )
                for i in range(n)
            ],
            music_mood="ambient",
        )

    def test_total_duration(self) -> None:
        spec = self._make_spec(12)
        # 5s title + 12 scenes × 12s default + 5s closing = 154s
        assert spec.total_duration() == 5 + (12 * 12) + 5

    def test_min_max_scenes_validation(self) -> None:
        with pytest.raises(ValueError):
            self._make_spec(9)
        with pytest.raises(ValueError):
            self._make_spec(16)
