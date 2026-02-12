"""Scene and mind movie specification models for Mind Movie Generator."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .goals import LifeCategory


class Scene(BaseModel):
    """A single scene in the mind movie with affirmation and video prompt."""

    index: int = Field(..., ge=0, description="Scene index (0-based)")
    name: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Unique descriptive scene identifier (e.g. 'coastal_sunrise_run')",
    )
    category: LifeCategory = Field(..., description="Life category this scene belongs to")
    affirmation: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="First-person present-tense affirmation (5-12 words recommended)",
    )
    video_prompt: str = Field(
        ...,
        min_length=50,
        description="Photorealistic cinematography prompt for video generation model",
    )
    mood: Literal["warm", "energetic", "peaceful", "romantic", "confident", "joyful", "serene"] = Field(
        ..., description="Emotional mood of the scene"
    )

    @field_validator("affirmation")
    @classmethod
    def validate_affirmation_format(cls, v: str) -> str:
        """Ensure affirmation follows proper format rules.

        Affirmations must:
        - Start with 'I' (first-person)
        - Be present tense (as if already true)
        - Be positive (no negative words)
        """
        stripped = v.strip()

        if not stripped.startswith("I "):
            raise ValueError(
                f"Affirmation must be first-person (start with 'I'). Got: '{v[:30]}...'"
            )

        return v


class MindMovieSpec(BaseModel):
    """Complete specification for a mind movie."""

    title: str = Field(
        default="My Vision",
        min_length=1,
        max_length=100,
        description="Title displayed on the opening card",
    )
    scenes: list[Scene] = Field(
        ...,
        min_length=10,
        max_length=15,
        description="10-15 scenes, each with affirmation and video prompt",
    )
    music_mood: str = Field(
        ...,
        description="Overall mood for background music selection (e.g., 'uplifting ambient', 'calm meditation')",
    )
    closing_affirmation: str = Field(
        default="I Am Grateful For My Beautiful Life",
        description="Final gratitude affirmation on closing card",
    )

    def total_duration(
        self,
        scene_duration: int = 12,
        title_duration: int = 5,
        closing_duration: int = 5,
    ) -> int:
        """Calculate total video duration in seconds.

        Args:
            scene_duration: Duration of each scene in seconds
            title_duration: Duration of title card in seconds
            closing_duration: Duration of closing card in seconds

        Returns:
            Total duration in seconds
        """
        return title_duration + (len(self.scenes) * scene_duration) + closing_duration

    def scenes_by_category(self) -> dict[LifeCategory, list[Scene]]:
        """Group scenes by their life category.

        Returns:
            Dictionary mapping categories to their scenes
        """
        result: dict[LifeCategory, list[Scene]] = {}
        for scene in self.scenes:
            if scene.category not in result:
                result[scene.category] = []
            result[scene.category].append(scene)
        return result

    def get_scene(self, index: int) -> Scene | None:
        """Get a scene by its index.

        Args:
            index: Scene index to retrieve

        Returns:
            Scene if found, None otherwise
        """
        for scene in self.scenes:
            if scene.index == index:
                return scene
        return None
