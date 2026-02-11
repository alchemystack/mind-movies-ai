"""Google Veo video generation client.

Wraps the google-genai SDK to generate video clips from text prompts
using Google's Veo models (3.0, 3.1, and their Fast variants).

The SDK's generate_videos() call is synchronous and long-running
(2–6 minutes per clip), so we push it to a thread via asyncio.to_thread()
to keep the event loop free for concurrent scene generation.
"""

import asyncio
import logging
from pathlib import Path

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Default model — Veo 3.1 Fast offers the best cost/speed trade-off
DEFAULT_MODEL = "veo-3.1-fast-generate-preview"

# Polling interval in seconds while waiting for video generation
_POLL_INTERVAL = 10

# Per-second cost by model variant (Veo 3.x always generates audio natively)
_COST_PER_SECOND: dict[str, float] = {
    "veo-3.1-fast-generate-preview": 0.15,
    "veo-3.1-generate-preview": 0.40,
    "veo-3.0-fast-generate-001": 0.15,
    "veo-3.0-generate-001": 0.40,
    "veo-2.0-generate-001": 0.35,
}

# Transient errors worth retrying
_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class VeoClient:
    """Google Veo video generation client implementing VideoGeneratorProtocol.

    Generates 8-second video clips from text prompts using Google's Veo models.
    Supports configurable resolution (720p/1080p/4K) and aspect ratio (16:9/9:16).
    Veo 3.x models natively generate audio as part of the video output.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        poll_interval: int = _POLL_INTERVAL,
    ) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.poll_interval = poll_interval

    def _generate_and_poll(
        self,
        prompt: str,
        output_path: Path,
        resolution: str,
        aspect_ratio: str,
        negative_prompt: str | None,
    ) -> Path:
        """Synchronous generate + poll loop run inside a thread.

        This method is intentionally synchronous — it is called via
        asyncio.to_thread() from generate_video().
        """
        config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            person_generation="allow_adult",
            number_of_videos=1,
        )
        if negative_prompt:
            config.negative_prompt = negative_prompt

        logger.info(
            "Starting Veo generation: model=%s, resolution=%s",
            self.model,
            resolution,
        )

        operation = self.client.models.generate_videos(
            model=self.model,
            prompt=prompt,
            config=config,
        )

        # Poll until the operation completes
        import time

        while not operation.done:
            time.sleep(self.poll_interval)
            operation = self.client.operations.get(operation)

        # Validate response
        if (
            not operation.response
            or not operation.response.generated_videos
        ):
            raise RuntimeError(
                "Video generation failed: no videos returned by Veo API"
            )

        video = operation.response.generated_videos[0]
        if video.video is None:
            raise RuntimeError(
                "Video generation failed: video object is empty in Veo response"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        video.video.save(str(output_path))

        logger.info("Video saved to %s", output_path)
        return output_path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    async def generate_video(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 8,  # noqa: ARG002 — part of VideoGeneratorProtocol
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        negative_prompt: str | None = None,
    ) -> Path:
        """Generate a video clip from a text prompt.

        Delegates to a background thread so the event loop stays free
        for concurrent generation of other scenes.

        Note: Veo always produces 8-second clips regardless of the *duration*
        parameter. The parameter is accepted for protocol conformance.

        Args:
            prompt: Cinematic text prompt describing the scene.
            output_path: Where to save the generated MP4 file.
            duration: Accepted for protocol conformance (Veo produces 8s clips).
            resolution: Output resolution — "720p", "1080p", or "4K".
            aspect_ratio: "16:9" or "9:16".
            negative_prompt: Things to avoid in the generated video.

        Returns:
            The output_path where the video was saved.

        Raises:
            RuntimeError: If Veo returns no generated videos.
            ConnectionError/TimeoutError/OSError: Retried up to 3 times.
        """
        return await asyncio.to_thread(
            self._generate_and_poll,
            prompt,
            output_path,
            resolution,
            aspect_ratio,
            negative_prompt,
        )

    def estimate_cost(self, duration: int) -> float:
        """Estimate cost for generating a video of given duration.

        Args:
            duration: Video duration in seconds.

        Returns:
            Estimated cost in USD.
        """
        rate = _COST_PER_SECOND.get(
            self.model,
            _COST_PER_SECOND[DEFAULT_MODEL],
        )
        return duration * rate
