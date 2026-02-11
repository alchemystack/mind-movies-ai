"""Cost and time estimation for mind movie generation.

Calculates expected costs for each pipeline stage based on the
current configuration and scene count. Used to display a cost
summary and seek user confirmation before committing to API calls.
"""

import logging
from dataclasses import dataclass

from mindmovie.config.settings import Settings
from mindmovie.models.scenes import MindMovieSpec

logger = logging.getLogger(__name__)

# ── Video generation pricing (USD per second of generated video) ────────────
# Veo 3.x models natively generate audio; single rate per model.
# BytePlus Seedance pricing derived from token formula at 720p/24fps:
#   tokens = (1280 * 720 * 24 * duration) / 1024 ≈ 21,600 tokens/s
#   With audio ($1.2/M tokens): ~$0.026/s
VIDEO_PRICING: dict[str, float] = {
    "veo-3.1-generate-preview": 0.40,
    "veo-3.1-fast-generate-preview": 0.15,
    "veo-3.0-generate-001": 0.40,
    "veo-3.0-fast-generate-001": 0.15,
    "veo-2.0-generate-001": 0.35,
    "seedance-1-5-pro-251215": 0.026,
}

# Default fallback for unknown models
_DEFAULT_VIDEO_COST_PER_SEC = 0.15

# ── LLM pricing (Claude Sonnet) ────────────────────────────────────────────
# Approximate cost for scene generation (one structured call)
LLM_COST_SCENE_GENERATION = 0.02  # ~$0.02 per structured generation

# ── Time estimates (seconds) ────────────────────────────────────────────────
# Video generation: 2-6 minutes per clip, parallelizable
VIDEO_GEN_TIME_PER_CLIP_SECS = 240  # ~4 min average
COMPOSITION_TIME_SECS = 180          # ~3 min for MoviePy composition


@dataclass(frozen=True)
class CostBreakdown:
    """Itemized cost and time breakdown for a mind movie generation."""

    num_scenes: int
    scene_duration: int

    # Costs in USD
    video_cost: float
    llm_cost: float

    # Time estimates in seconds
    video_time: float
    composition_time: float

    @property
    def total_cost(self) -> float:
        """Total estimated cost in USD."""
        return self.video_cost + self.llm_cost

    @property
    def total_time(self) -> float:
        """Total estimated time in seconds."""
        return self.video_time + self.composition_time

    @property
    def total_video_duration(self) -> int:
        """Total seconds of video to generate (scenes only)."""
        return self.num_scenes * self.scene_duration

    def format_cost(self) -> str:
        """Format total cost as a human-readable string."""
        return f"${self.total_cost:.2f}"

    def format_time(self) -> str:
        """Format total time as a human-readable string."""
        minutes = int(self.total_time // 60)
        if minutes < 1:
            return f"{int(self.total_time)}s"
        return f"~{minutes} min"

    def format_summary(self) -> str:
        """Format a multi-line cost and time summary."""
        lines = [
            f"  Video generation ({self.num_scenes} clips × {self.scene_duration}s): "
            f"${self.video_cost:.2f}",
            f"  Scene generation (LLM): ${self.llm_cost:.2f}",
            "  ─────────────────────────────",
            f"  Total estimated cost: {self.format_cost()}",
            f"  Estimated time: {self.format_time()}",
        ]
        return "\n".join(lines)


class CostEstimator:
    """Estimates pipeline costs and generation time.

    Uses the current settings (video model, scene count) to calculate
    expected API costs. Provides both per-stage and total breakdowns
    for user confirmation before generation begins.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def estimate(self, spec: MindMovieSpec) -> CostBreakdown:
        """Calculate full cost breakdown for a mind movie specification.

        Args:
            spec: The generated mind movie specification.

        Returns:
            CostBreakdown with itemized costs and time estimates.
        """
        num_scenes = len(spec.scenes)
        scene_duration = self.settings.movie.scene_duration

        video_cost = self.estimate_video_cost(num_scenes, scene_duration)
        llm_cost = LLM_COST_SCENE_GENERATION

        video_time = self._estimate_video_time(num_scenes)
        composition_time = float(COMPOSITION_TIME_SECS)

        breakdown = CostBreakdown(
            num_scenes=num_scenes,
            scene_duration=scene_duration,
            video_cost=video_cost,
            llm_cost=llm_cost,
            video_time=video_time,
            composition_time=composition_time,
        )

        logger.info(
            "Estimated cost: %s, time: %s for %d scenes",
            breakdown.format_cost(),
            breakdown.format_time(),
            num_scenes,
        )

        return breakdown

    def estimate_video_cost(
        self, num_scenes: int, scene_duration: int
    ) -> float:
        """Calculate video generation cost.

        Args:
            num_scenes: Number of video clips to generate.
            scene_duration: Duration of each clip in seconds.

        Returns:
            Estimated cost in USD.
        """
        model = self.settings.video.model
        cost_per_sec = VIDEO_PRICING.get(model, _DEFAULT_VIDEO_COST_PER_SEC)
        total_seconds = num_scenes * scene_duration

        return cost_per_sec * total_seconds

    def _estimate_video_time(self, num_scenes: int) -> float:
        """Estimate video generation time accounting for concurrency.

        Args:
            num_scenes: Number of clips to generate.

        Returns:
            Estimated wall-clock time in seconds.
        """
        max_concurrent = self.settings.video.max_concurrent
        batches = -(-num_scenes // max_concurrent)  # Ceiling division
        return batches * VIDEO_GEN_TIME_PER_CLIP_SECS
