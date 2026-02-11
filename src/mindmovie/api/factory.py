"""Factory for creating video generation clients based on provider setting.

Centralizes the provider selection logic so that both the pipeline
orchestrator and the render CLI command create the correct client
without duplicating provider-specific wiring.
"""

from mindmovie.api.base import VideoGeneratorProtocol
from mindmovie.config.settings import Settings


def create_video_client(settings: Settings) -> VideoGeneratorProtocol:
    """Create a video generation client for the configured provider.

    Reads ``settings.video.provider`` to determine which client to
    instantiate, pulling the appropriate API key from ``settings.api``.

    Args:
        settings: Resolved application settings.

    Returns:
        A client implementing ``VideoGeneratorProtocol``.

    Raises:
        ValueError: If the required API key for the chosen provider is
            not set, or if the provider name is unrecognised.
    """
    provider = settings.video.provider

    if provider == "veo":
        api_key = settings.api.gemini_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Required for the Veo video provider. "
                "Set it in your .env file or environment variables."
            )

        from mindmovie.api.veo_client import VeoClient

        return VeoClient(
            api_key=api_key,
            model=settings.video.model,
        )

    if provider == "byteplus":
        api_key = settings.api.byteplus_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "BYTEPLUS_API_KEY is not set. "
                "Required for the BytePlus video provider. "
                "Set it in your .env file or environment variables."
            )

        from mindmovie.api.byteplus_client import BytePlusClient

        return BytePlusClient(
            api_key=api_key,
            model=settings.video.model,
            generate_audio=settings.video.generate_audio,
        )

    raise ValueError(
        f"Unknown video provider: {provider!r}. "
        f"Supported providers: veo, byteplus"
    )
