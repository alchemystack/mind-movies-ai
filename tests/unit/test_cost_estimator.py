"""Unit tests for the CostEstimator."""

import json
from pathlib import Path

import pytest

from mindmovie.config.settings import (
    APISettings,
    BuildSettings,
    MovieSettings,
    MusicSettings,
    Settings,
    VideoSettings,
)
from mindmovie.core.cost_estimator import VIDEO_PRICING, CostBreakdown, CostEstimator
from mindmovie.models.scenes import MindMovieSpec


@pytest.fixture
def sample_spec(fixtures_dir: Path) -> MindMovieSpec:
    with open(fixtures_dir / "sample_scenes.json") as f:
        return MindMovieSpec.model_validate(json.load(f))


def _settings(model: str = "veo-3.1-fast-generate-preview") -> Settings:
    return Settings(
        api=APISettings(), video=VideoSettings(model=model),
        music=MusicSettings(), movie=MovieSettings(), build=BuildSettings(),
    )


class TestCostEstimator:
    def test_veo_fast_cost(self) -> None:
        est = CostEstimator(_settings())
        cost = est.estimate_video_cost(num_scenes=12, scene_duration=8)
        assert cost == pytest.approx(14.40)

    def test_full_estimate(self, sample_spec: MindMovieSpec) -> None:
        est = CostEstimator(_settings())
        result = est.estimate(sample_spec)
        assert isinstance(result, CostBreakdown)
        assert result.num_scenes == len(sample_spec.scenes)
        assert result.total_cost > 0

    def test_pricing_table(self) -> None:
        for model in ["veo-3.1-generate-preview", "veo-3.1-fast-generate-preview",
                       "veo-3.0-generate-001", "veo-2.0-generate-001"]:
            assert model in VIDEO_PRICING
