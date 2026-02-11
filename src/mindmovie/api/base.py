"""Base protocol definitions for API clients.

Defines structural typing protocols that all API client implementations
must satisfy. Using Protocol instead of ABC allows duck-typing —
any class with matching method signatures automatically conforms.
"""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VideoGeneratorProtocol(Protocol):
    """Protocol for video generation clients."""

    async def generate_video(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 8,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
    ) -> Path:
        """Generate a video clip from a text prompt."""
        ...

    def estimate_cost(self, duration: int) -> float:
        """Estimate cost for generating a video of given duration."""
        ...


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM chat clients.

    Supports two modes of interaction:
    - chat(): Free-form conversational responses (used by questionnaire)
    - generate_structured(): JSON output validated against a schema (used by scene generator)
    """

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> str:
        """Send chat messages and get a text response."""
        ...

    async def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: type,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON output matching schema."""
        ...
