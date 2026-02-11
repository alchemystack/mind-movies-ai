"""Scene and mind movie specification models for Mind Movie Generator."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .goals import LifeCategory

# Valid affirmation prefixes (case-insensitive)
AFFIRMATION_PREFIXES = ("i am", "i have", "i feel", "i live")


class Scene(BaseModel):
    """A single scene in the mind movie with affirmation and video prompt."""

    index: int = Field(..., ge=0, description="Scene index (0-based)")
    category: LifeCategory = Field(..., description="Life category this scene belongs to")
    affirmation: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Present-tense affirmation (5-12 words recommended)",
    )
    video_prompt: str = Field(
        ...,
        min_length=50,
        description="Cinematic video prompt for Veo: subject + action + scene + camera + style + lighting",
    )
    mood: Literal["warm", "energetic", "peaceful", "romantic", "confident", "joyful", "serene"] = Field(
        ..., description="Emotional mood of the scene"
    )

    @field_validator("affirmation")
    @classmethod
    def validate_affirmation_format(cls, v: str) -> str:
        """Ensure affirmation follows proper format rules.

        Affirmations must:
        - Start with 'I am', 'I have', 'I feel', or 'I live'
        - Be present tense (as if already true)
        - Be positive (no negative words)
        """
        lower_v = v.lower().strip()

        # Check prefix
        if not any(lower_v.startswith(prefix) for prefix in AFFIRMATION_PREFIXES):
            raise ValueError(
                f"Affirmation must start with one of: {', '.join(AFFIRMATION_PREFIXES)}. "
                f"Got: '{v[:20]}...'"
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
        scene_duration: int = 8,
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
