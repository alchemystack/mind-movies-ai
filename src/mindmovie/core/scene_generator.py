"""Scene generation — transforms extracted goals into a MindMovieSpec."""

import logging
from typing import Any

from mindmovie.api.anthropic_client import AnthropicClient
from mindmovie.models.goals import ExtractedGoals
from mindmovie.models.scenes import MindMovieSpec

logger = logging.getLogger(__name__)

GENERATION_PROMPT = """\
You are a mind movie scene designer. Transform the user's life vision goals \
into a mind movie specification with 10-15 vivid cinematic scenes.

Create scenes distributed across the categories provided. \
Each scene must have:

1. **affirmation**: First person, present tense, positive, emotionally charged, 5-12 words.
   - Must start with "I" (first-person perspective)
   - Present tense only (as if already true)
   - No negative words (no "not", "don't", "never")
   - Specific and emotionally charged
   Examples: "I am radiantly healthy and full of energy", \
"I lead groundbreaking research in my field", \
"I have multiple streams of abundant income"

2. **video_prompt**: Cinematic prompt following this formula:
   Subject + Action + Scene + Camera Movement + Style/Mood + Lighting
   - Describe motion, not static scenes
   - Include specific camera movements (dolly, pan, tracking shot, crane)
   - Specify lighting (golden hour, soft natural light, warm glow)
   - Include style keywords (cinematic, aspirational, film grain, shallow depth of field)
   - Present tense throughout
   - 2-4 sentences, highly detailed

3. **mood**: One of: warm, energetic, peaceful, romantic, confident, joyful, serene

SCENE DISTRIBUTION:
- Create 2-3 scenes per active (non-skipped) category
- Vary moods within each category for emotional dynamics
- Order scenes to build emotional momentum: start energetic, \
build through confident/joyful, end serene/grateful

SUBJECT APPEARANCE:
- If physical appearance is provided, use it consistently in ALL video prompts
- Replace generic "person" with appearance-matching descriptions
- Example: Instead of "A vibrant person in athletic wear", use
  "A tall woman with warm brown skin and curly dark hair in athletic wear"
- Keep descriptions natural and cinematic — weave appearance into the scene
  rather than listing traits mechanically
- If no appearance is provided, use generic inclusive descriptions

INITIAL VISION:
- If an initial vision summary is provided, use it as additional context
  to inform the tone, themes, and imagery of the scenes
- The vision should complement (not override) the per-category goals

MUSIC MOOD:
- Describe an overall music mood that complements all scenes
- Example: "uplifting ambient with gentle piano and warm synthesizer pads"

CLOSING AFFIRMATION:
- A gratitude-based affirmation for the closing card
- Example: "I Am Grateful For My Beautiful Life"

TITLE:
- Use the user's provided title, or create a meaningful one if not provided

Skip categories that are marked as skipped — do not generate scenes for them."""


def _unwrap_llm_result(result: dict[str, Any]) -> dict[str, Any]:
    """Unwrap LLM structured output if nested under an envelope key.

    Claude's tool-use sometimes wraps the response in {"output": {...}}.
    This handles both wrapped and flat responses.
    """
    if "output" in result and isinstance(result["output"], dict):
        return result["output"]
    return result


class SceneGenerator:
    """Generates a MindMovieSpec from extracted goals via Claude structured output."""

    def __init__(self, client: AnthropicClient, *, num_scenes: int = 12) -> None:
        self.client = client
        self.num_scenes = max(10, min(15, num_scenes))

    async def generate(self, goals: ExtractedGoals) -> MindMovieSpec:
        """Generate a complete mind movie specification from extracted goals."""
        user_content = self._build_user_message(goals)

        logger.info(
            "Generating %d scenes for %d active categories",
            self.num_scenes,
            goals.category_count,
        )

        result = await self.client.generate_structured(
            messages=[{"role": "user", "content": user_content}],
            schema=MindMovieSpec,
            system_prompt=GENERATION_PROMPT,
        )

        spec = MindMovieSpec.model_validate(_unwrap_llm_result(result))

        logger.info(
            "Generated %d scenes across %d categories",
            len(spec.scenes),
            len(spec.scenes_by_category()),
        )

        return spec

    def _build_user_message(self, goals: ExtractedGoals) -> str:
        """Build the user message containing goals for scene generation."""
        parts: list[str] = []
        parts.append(f"Title: {goals.title}")
        parts.append(f"Target number of scenes: {self.num_scenes}")
        parts.append("")

        if goals.appearance:
            parts.append("## Subject Appearance")
            parts.append(goals.appearance.description)
            parts.append("")

        if goals.initial_vision:
            parts.append("## Initial Vision Summary")
            parts.append(goals.initial_vision)
            parts.append("")

        for cat_goal in goals.categories:
            status = "SKIPPED" if cat_goal.skipped else "ACTIVE"
            parts.append(f"## {cat_goal.category.value.title()} [{status}]")
            if not cat_goal.skipped:
                parts.append(f"Vision: {cat_goal.vision}")
                parts.append(f"Visual details: {cat_goal.visual_details}")
                parts.append(f"Actions: {cat_goal.actions}")
                parts.append(f"Emotions: {cat_goal.emotions}")
            parts.append("")

        return "\n".join(parts)
