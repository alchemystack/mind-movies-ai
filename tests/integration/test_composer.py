"""Integration tests for the video composition module.

Tests text overlays, effects, and VideoComposer methods using synthetic assets.
No slow MoviePy encoding tests — those are manual.
"""

from pathlib import Path

import numpy as np
import pytest
from moviepy import ImageClip

from mindmovie.config.settings import MovieSettings, MusicSettings
from mindmovie.models.scenes import LifeCategory, MindMovieSpec, Scene
from mindmovie.state.models import PipelineState, SceneAsset
from mindmovie.video.composer import CompositionError, VideoComposer
from mindmovie.video.effects import crossfade_concatenate
from mindmovie.video.text_overlay import (
    get_resolution,
    render_affirmation_overlay,
    render_closing_card,
    render_title_card,
)
from tests.fixtures.create_test_video import create_test_video


def _movie_settings() -> MovieSettings:
    return MovieSettings(scene_duration=5, title_duration=3, closing_duration=3, crossfade_duration=0.3, fps=24)


def _music_settings() -> MusicSettings:
    return MusicSettings()


def _make_spec(n: int = 10) -> MindMovieSpec:
    moods = ["warm", "energetic", "peaceful", "romantic", "confident",
             "joyful", "serene", "warm", "confident", "peaceful"]
    cats = list(LifeCategory)
    return MindMovieSpec(
        scenes=[
            Scene(index=i, name=f"test_scene_{i}",
                  category=cats[i % len(cats)],
                  affirmation=f"I am living my best life scene {i + 1}",
                  video_prompt="A" * 50, mood=moods[i])
            for i in range(n)
        ],
        music_mood="ambient",
    )


class TestTextOverlay:
    def test_render_title_card(self) -> None:
        img = render_title_card("Test Title", 640, 360)
        assert img.size == (640, 360)
        assert img.mode == "RGB"

    def test_render_closing_card(self) -> None:
        img = render_closing_card("Grateful", 640, 360)
        assert img.size == (640, 360)

    def test_render_affirmation_overlay(self) -> None:
        img = render_affirmation_overlay("I am strong", 640, 360)
        assert img.mode == "RGBA"

    def test_get_resolution(self) -> None:
        assert get_resolution("1080p", "16:9") == (1920, 1080)
        assert get_resolution("720p", "16:9") == (1280, 720)
        assert get_resolution("480p", "16:9") == (854, 480)
        with pytest.raises(ValueError):
            get_resolution("360p", "16:9")


class TestEffects:
    def test_crossfade_concatenate(self) -> None:
        c1 = ImageClip(np.zeros((100, 100, 3), dtype=np.uint8)).with_duration(2).with_fps(24)
        c2 = ImageClip(np.ones((100, 100, 3), dtype=np.uint8) * 255).with_duration(2).with_fps(24)
        result = crossfade_concatenate([c1, c2], crossfade_duration=0.5)
        assert result.duration == pytest.approx(3.5, abs=0.1)

    def test_crossfade_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            crossfade_concatenate([], crossfade_duration=0.5)


class TestVideoComposer:
    def test_create_title_card(self) -> None:
        composer = VideoComposer(_movie_settings(), _music_settings(), "720p")
        clip = composer._create_title_card("Test")
        assert clip.duration == 3

    def test_create_scene_clip(self, tmp_path: Path) -> None:
        video_path = tmp_path / "scene.mp4"
        create_test_video(video_path, duration=5.0, size=(320, 180))
        composer = VideoComposer(_movie_settings(), _music_settings(), "720p")
        scene = Scene(index=0, name="test_scene_clip",
                      category=LifeCategory.HEALTH,
                      affirmation="I am strong", video_prompt="A" * 50, mood="energetic")
        clip = composer._create_scene_clip(scene, video_path)
        assert clip.duration <= 5

    def test_missing_video_raises(self, tmp_path: Path) -> None:
        composer = VideoComposer(_movie_settings(), _music_settings(), "720p")
        scene = Scene(index=0, name="test_missing_video",
                      category=LifeCategory.HEALTH,
                      affirmation="I am strong", video_prompt="A" * 50, mood="energetic")
        with pytest.raises(CompositionError):
            composer._create_scene_clip(scene, tmp_path / "nope.mp4")

    def test_resolve_missing_paths_raises(self) -> None:
        composer = VideoComposer(_movie_settings(), _music_settings(), "720p")
        spec = _make_spec()
        state = PipelineState(id="t", scene_assets=[
            SceneAsset(scene_index=i) for i in range(10)
        ])
        with pytest.raises(CompositionError, match="Missing video files"):
            composer._resolve_video_paths(spec, state)
