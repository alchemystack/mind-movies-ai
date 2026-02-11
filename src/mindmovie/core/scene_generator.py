"""Scene generation engine for Mind Movie Generator.

Transforms extracted goals from the questionnaire into a complete
MindMovieSpec with cinematic video prompts and affirmations. Uses
Claude's structured output to guarantee valid JSON that conforms
to the MindMovieSpec Pydantic schema.
"""

import logging

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

MUSIC MOOD:
- Describe an overall music mood that complements all scenes
- Example: "uplifting ambient with gentle piano and warm synthesizer pads"

CLOSING AFFIRMATION:
- A gratitude-based affirmation for the closing card
- Example: "I Am Grateful For My Beautiful Life"

TITLE:
- Use the user's provided title, or create a meaningful one if not provided

Skip categories that are marked as skipped — do not generate scenes for them."""


class SceneGenerator:
    """Generates structured scene specifications from extracted goals.

    Takes the goals produced by the questionnaire engine and sends them
    to Claude with a scene-design system prompt. Claude returns a
    MindMovieSpec via structured output (tool-use), which is then
    validated against the Pydantic schema.
    """

    def __init__(self, client: AnthropicClient, *, num_scenes: int = 12) -> None:
        """Initialize the scene generator.

        Args:
            client: Anthropic API client for Claude interactions.
            num_scenes: Target number of scenes to generate (10-15).
        """
        self.client = client
        self.num_scenes = max(10, min(15, num_scenes))

    async def generate(self, goals: ExtractedGoals) -> MindMovieSpec:
        """Generate a complete mind movie specification from extracted goals.

        Sends the goals to Claude with a scene-design system prompt.
        Claude produces structured JSON matching the MindMovieSpec schema
        via tool-use, which is validated by Pydantic.

        Args:
            goals: Extracted goals from the questionnaire session.

        Returns:
            Validated MindMovieSpec with scenes, affirmations, and prompts.

        Raises:
            ValueError: If structured output cannot be parsed or validated.
        """
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

        spec = MindMovieSpec.model_validate(result)

        logger.info(
            "Generated %d scenes across %d categories",
            len(spec.scenes),
            len(spec.scenes_by_category()),
        )

        return spec

    def _build_user_message(self, goals: ExtractedGoals) -> str:
        """Build the user message containing goals for scene generation.

        Formats the extracted goals into a clear prompt that tells Claude
        exactly how many scenes to produce and which categories to cover.

        Args:
            goals: Extracted goals from the questionnaire.

        Returns:
            Formatted string for the user message.
        """
        parts: list[str] = []
        parts.append(f"Title: {goals.title}")
        parts.append(f"Target number of scenes: {self.num_scenes}")
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
