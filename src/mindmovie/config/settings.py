"""Pydantic settings models for Mind Movie Generator configuration."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API key configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="ANTHROPIC_API_KEY",
        description="Anthropic API key for Claude (questionnaire and scene generation)",
    )
    gemini_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="GEMINI_API_KEY",
        description="Google Gemini/Veo API key (video generation)",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        validation_alias="ANTHROPIC_MODEL",
        description="Anthropic model ID for questionnaire and scene generation",
    )


class VideoSettings(BaseSettings):
    """Video generation settings."""

    model_config = SettingsConfigDict(extra="ignore")

    model: str = Field(
        default="veo-3.1-fast-generate-preview",
        description="Video generation model ID",
    )
    resolution: Literal["720p", "1080p", "4K"] = Field(
        default="1080p",
        description="Output resolution: 720p, 1080p, or 4K",
    )
    aspect_ratio: Literal["16:9", "9:16"] = Field(
        default="16:9",
        description="Aspect ratio: 16:9 or 9:16",
    )
    generate_audio: bool = Field(
        default=True,
        description="Generate audio with video (Veo 3+ only)",
    )
    max_concurrent: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum concurrent video generations",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed generations",
    )


class MusicSettings(BaseSettings):
    """Background music settings."""

    model_config = SettingsConfigDict(extra="ignore")

    source: Literal["file", "mubert", "musicgen"] = Field(
        default="file",
        description="Music source: file, mubert, or musicgen",
    )
    file_path: str = Field(
        default="",
        description="Path to background music file (if source is 'file')",
    )
    volume: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Music volume (0.0 to 1.0)",
    )


class MovieSettings(BaseSettings):
    """Mind movie structure settings."""

    model_config = SettingsConfigDict(extra="ignore")

    scene_duration: int = Field(
        default=8,
        ge=5,
        le=15,
        description="Duration of each scene in seconds",
    )
    num_scenes: int = Field(
        default=12,
        ge=10,
        le=15,
        description="Target number of scenes (10-15 recommended)",
    )
    title_duration: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Title card duration in seconds",
    )
    closing_duration: int = Field(
        default=5,
        ge=3,
        le=10,
        description="Closing card duration in seconds",
    )
    crossfade_duration: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Crossfade duration between scenes in seconds",
    )
    fps: int = Field(
        default=24,
        ge=24,
        le=60,
        description="Output video frame rate",
    )


class BuildSettings(BaseSettings):
    """Build and output settings."""

    model_config = SettingsConfigDict(extra="ignore")

    build_dir: str = Field(
        default="build",
        description="Directory for intermediate files and pipeline state",
    )
    output_path: str = Field(
        default="mind_movie.mp4",
        description="Default output file path",
    )


class Settings(BaseSettings):
    """Root settings aggregating all configuration sections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    api: APISettings = Field(default_factory=APISettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    music: MusicSettings = Field(default_factory=MusicSettings)
    movie: MovieSettings = Field(default_factory=MovieSettings)
    build: BuildSettings = Field(default_factory=BuildSettings)

    @property
    def build_dir(self) -> str:
        """Convenience accessor for build directory."""
        return self.build.build_dir

    @property
    def output_path(self) -> str:
        """Convenience accessor for output path."""
        return self.build.output_path

    def has_required_api_keys(self) -> bool:
        """Check if required API keys are configured."""
        return bool(
            self.api.anthropic_api_key.get_secret_value()
            and self.api.gemini_api_key.get_secret_value()
        )

    def get_missing_api_keys(self) -> list[str]:
        """Return list of missing required API keys."""
        missing = []
        if not self.api.anthropic_api_key.get_secret_value():
            missing.append("ANTHROPIC_API_KEY")
        if not self.api.gemini_api_key.get_secret_value():
            missing.append("GEMINI_API_KEY")
        return missing
