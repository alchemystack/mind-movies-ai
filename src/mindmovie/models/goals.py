"""Goal extraction data models for Mind Movie Generator."""

from enum import StrEnum

from pydantic import BaseModel, Field


class LifeCategory(StrEnum):
    """Life categories for mind movie visualization."""

    HEALTH = "health"
    WEALTH = "wealth"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    GROWTH = "growth"
    LIFESTYLE = "lifestyle"


class CategoryGoal(BaseModel):
    """Extracted goal for a single life category."""

    category: LifeCategory
    vision: str = Field(..., description="User's described vision for this life area")
    visual_details: str = Field(
        ..., description="What the vision looks like - setting, environment, colors"
    )
    actions: str = Field(
        ..., description="What the user is doing in this vision, who's with them"
    )
    emotions: str = Field(
        ..., description="How the vision feels - emotions and sensations"
    )
    skipped: bool = Field(
        default=False, description="Whether the user skipped this category"
    )


class PhysicalAppearance(BaseModel):
    """Physical appearance details for consistent video depiction."""

    description: str = Field(
        ...,
        description=(
            "Free-form physical appearance description "
            "(height, build, skin tone, hair color/style, etc.)"
        ),
    )


class ExtractedGoals(BaseModel):
    """Complete goals extracted from the questionnaire session."""

    title: str = Field(
        default="My Vision",
        description="Custom title for the mind movie, if provided by user",
    )
    appearance: PhysicalAppearance | None = Field(
        default=None,
        description="User's physical appearance for consistent video depiction",
    )
    initial_vision: str | None = Field(
        default=None,
        description="User's pre-existing vision summary, pasted at the start",
    )
    categories: list[CategoryGoal] = Field(
        default_factory=list, description="Goals for each life category"
    )
    conversation_id: str = Field(
        ..., description="Unique ID for tracking and resume capability"
    )

    @property
    def active_categories(self) -> list[CategoryGoal]:
        """Return only categories that were not skipped."""
        return [cat for cat in self.categories if not cat.skipped]

    @property
    def category_count(self) -> int:
        """Return the number of active (non-skipped) categories."""
        return len(self.active_categories)
