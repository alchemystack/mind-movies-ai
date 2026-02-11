"""BytePlus Seedance video generation client.

Wraps the BytePlus Ark SDK to generate video clips from text prompts
using the Seedance model family (1.5 Pro, etc.).

The SDK's content_generation.tasks API is asynchronous (create task, poll
for completion, download result). The synchronous _generate_and_poll()
method is pushed to a thread via asyncio.to_thread() to keep the event
loop free for concurrent scene generation.
"""

import asyncio
import logging
import time
import urllib.request
from pathlib import Path

from byteplussdkarkruntime import Ark
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Default model — Seedance 1.5 Pro with native audio support
DEFAULT_MODEL = "seedance-1-5-pro-251215"

# Polling interval in seconds while waiting for video generation
_POLL_INTERVAL = 10

# Per-second cost derived from token-based pricing at 720p/24fps.
# Formula: tokens = (W * H * FPS * duration) / 1024
# At 720p (1280×720), 24fps: tokens_per_sec ≈ 21,600
# With audio offline rate $1.2/M tokens: ~$0.026/s
# Without audio offline rate $0.6/M tokens: ~$0.013/s
_COST_PER_SECOND_AUDIO: dict[str, float] = {
    "seedance-1-5-pro-251215": 0.026,
}
_COST_PER_SECOND_NO_AUDIO: dict[str, float] = {
    "seedance-1-5-pro-251215": 0.013,
}

# Transient errors worth retrying
_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class BytePlusClient:
    """BytePlus Seedance video generation client implementing VideoGeneratorProtocol.

    Generates video clips from text prompts using BytePlus's Seedance models.
    Supports configurable resolution (480p/720p/1080p), aspect ratio (16:9/9:16),
    duration, and native audio generation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        poll_interval: int = _POLL_INTERVAL,
        generate_audio: bool = True,
    ) -> None:
        self.client = Ark(
            base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
            api_key=api_key,
        )
        self.model = model
        self.poll_interval = poll_interval
        self.generate_audio = generate_audio

    def _generate_and_poll(
        self,
        prompt: str,
        output_path: Path,
        duration: int,
        resolution: str,
        aspect_ratio: str,
    ) -> Path:
        """Synchronous create + poll + download loop run inside a thread.

        This method is intentionally synchronous — it is called via
        asyncio.to_thread() from generate_video().
        """
        logger.info(
            "Starting BytePlus generation: model=%s, resolution=%s, audio=%s",
            self.model,
            resolution,
            self.generate_audio,
        )

        # Create video generation task with first-class SDK parameters.
        # The SDK supports resolution, ratio, duration, generate_audio as
        # proper kwargs — no need to embed them in the prompt text.
        task_ref = self.client.content_generation.tasks.create(
            model=self.model,
            content=[{"type": "text", "text": prompt}],
            resolution=resolution,
            ratio=aspect_ratio,
            duration=duration,
            generate_audio=self.generate_audio,
        )
        task_id = task_ref.id
        logger.debug("Created BytePlus task: %s", task_id)

        # Poll until the task completes
        while True:
            result = self.client.content_generation.tasks.get(task_id=task_id)

            if result.status == "succeeded":
                break
            elif result.status == "failed":
                error_msg = result.error.message if result.error else "Unknown error"
                raise RuntimeError(
                    f"BytePlus video generation failed: {error_msg}"
                )
            elif result.status == "cancelled":
                raise RuntimeError("BytePlus video generation was cancelled")

            # Status is "running" or "queued" — keep polling
            time.sleep(self.poll_interval)

        # Download the generated video
        video_url = result.content.video_url
        if not video_url:
            raise RuntimeError(
                "Video generation succeeded but no video URL was returned"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Downloading video from %s", video_url)
        urllib.request.urlretrieve(video_url, str(output_path))  # noqa: S310

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
        duration: int = 8,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
    ) -> Path:
        """Generate a video clip from a text prompt.

        Delegates to a background thread so the event loop stays free
        for concurrent generation of other scenes.

        Args:
            prompt: Text prompt describing the scene.
            output_path: Where to save the generated MP4 file.
            duration: Video duration in seconds (2-12s supported).
            resolution: Output resolution — "480p", "720p", or "1080p".
            aspect_ratio: "16:9" or "9:16".

        Returns:
            The output_path where the video was saved.

        Raises:
            RuntimeError: If the task fails, is cancelled, or returns no video.
            ConnectionError/TimeoutError/OSError: Retried up to 3 times.
        """
        return await asyncio.to_thread(
            self._generate_and_poll,
            prompt,
            output_path,
            duration,
            resolution,
            aspect_ratio,
        )

    def estimate_cost(self, duration: int) -> float:
        """Estimate cost for generating a video of given duration.

        Uses token-based pricing formula:
        tokens = (width * height * fps * duration) / 1024

        At 720p (1280×720), 24fps this works out to ~$0.026/s with audio
        and ~$0.013/s without audio (offline rates).

        Args:
            duration: Video duration in seconds.

        Returns:
            Estimated cost in USD.
        """
        cost_table = (
            _COST_PER_SECOND_AUDIO if self.generate_audio
            else _COST_PER_SECOND_NO_AUDIO
        )
        rate = cost_table.get(
            self.model,
            cost_table.get(DEFAULT_MODEL, 0.026),
        )
        return duration * rate
