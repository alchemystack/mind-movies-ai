"""Scene generation — transforms extracted goals into a MindMovieSpec."""

import logging
from typing import Any

from mindmovie.api.anthropic_client import AnthropicClient
from mindmovie.models.goals import ExtractedGoals
from mindmovie.models.scenes import MindMovieSpec

logger = logging.getLogger(__name__)

GENERATION_PROMPT = """\
You are an expert mind movie scene designer and cinematography prompt engineer. \
Transform the user's life vision goals into a mind movie specification with \
10-15 scenes that will be sent to an AI video generation model to produce \
photorealistic footage.

Your output will be fed directly into a video generation AI (like Sora, Kling, \
or Seedance). Every video_prompt you write must be engineered to maximize the \
probability of a believable, photorealistic result from that model.

Create scenes distributed across the categories provided. \
Each scene must have:

1. **name**: A unique, descriptive identifier for the scene (2-5 words, \
lowercase with underscores). The name must clearly describe what happens \
in the scene so it is recognizable at a glance.
   Examples: "coastal_sunrise_run", "penthouse_city_view", "garden_meditation", \
"lavender_field_walk", "mountaintop_yoga_dawn"

2. **affirmation**: First person, present tense, positive, emotionally charged, \
5-12 words.
   - Must start with "I" (first-person perspective)
   - Present tense only (as if already true)
   - No negative words (no "not", "don't", "never")
   - Specific and emotionally charged
   Examples: "I am radiantly healthy and full of energy", \
"I lead groundbreaking research in my field", \
"I have multiple streams of abundant income"

3. **video_prompt**: A photorealistic cinematography prompt. This is the most \
critical field. Follow every rule below precisely:

   CAMERA-FIRST APPROACH (front-load the most important visual information):
   - Open with the camera setup: shot type, lens, and movement
   - Specify focal length for realism: "shot on 85mm lens, f/1.8, shallow \
depth of field" encodes compression, bokeh, and perspective far better \
than "close-up"
   - Name the camera technique: "handheld follow shot with slight lens shake", \
"slow steadicam tracking shot", "locked-off tripod wide", "gentle crane \
rising upward"
   - Front-load camera + lighting + subject in the first sentence; atmosphere \
and secondary details follow

   LIGHTING AS PHYSICS:
   - Describe the light source, direction, and quality — not just a mood word
   - Instead of "golden hour": "low-angle late afternoon sun casting long \
shadows, warm key light from camera-left with cool fill bounce"
   - Reference how light interacts with surfaces: "sunlight catching dust \
motes in the air", "rim light separating the subject from the background"

   MOTION ANCHORED TO PHYSICS:
   - Ground all movement in real physical forces — gravity, wind, inertia
   - "Wind disturbs the tablecloth in irregular gusts" not "the tablecloth \
moves"
   - Describe WHY things move, not just THAT they move

   PHOTOREALISTIC TEXTURE:
   - Reference a film stock or color science for organic feel: "Kodak \
Vision3 500T color palette", "muted Fujifilm Eterna tones", "graded \
like natural skin tones from a RED Komodo"
   - Include deliberate micro-imperfections that signal real footage: \
subtle overexposure in highlights, barely perceptible rack focus \
adjustment, faint chromatic aberration at frame edges, organic film grain
   - These imperfections prevent the uncanny "too perfect" AI look

   EMOTIONAL EXPRESSIVENESS (HIGHEST PRIORITY):
   - The subject's desired emotional state must be unmistakably visible
   - Convey emotion through face, body language, posture, gesture, \
environment, and lighting working together
   - Example: for joy, don't just say "smiling" — describe "eyes crinkling \
with genuine delight, shoulders relaxed and open, chin lifted slightly, \
caught in an unguarded moment of pure happiness"
   - The emotional authenticity of the scene is MORE important than \
literal accuracy to the user's description

   KEEP IT SIMPLE AND ACHIEVABLE:
   - ONE subject performing ONE clear action in ONE environment
   - Maximum TWO people in frame — every additional person is a failure \
point for temporal consistency
   - Favor common, recognizable compositions: person in landscape, person \
at desk, person walking, person in doorway
   - NEVER prompt for: readable text on screen, specific brand logos, \
unusual physics, large crowds with coordinated actions, or highly \
specific/rare scenarios
   - When in doubt, choose the simpler scene — a well-executed simple \
scene is vastly better than a botched complex one

   ABSOLUTELY NO SPEECH:
   - No person may be speaking, talking, or having a conversation in \
any scene whatsoever
   - No moving lips as if speaking, no dialogue, no presentations \
with speech
   - Non-verbal human sounds are allowed: breathing, laughing with \
closed or open mouth, yelling, sighing, cheering
   - Depict communication through gesture, expression, and body \
language only

   VISUAL-ONLY — NO ABSTRACT CONCEPTS:
   - The video_prompt must describe ONLY what a camera can physically see
   - Never include abstract, theoretical, or conceptual language from the \
user's goals (e.g., "solving problems", "achieving breakthroughs", \
"finding purpose")
   - If a user's goal is inherently non-visual (e.g., "master a complex \
skill"), translate it into a concrete visual: a person working \
confidently at a desk, a person moving with practiced ease
   - Every word in the prompt must correspond to something visible on screen

   FORMAT:
   - 3-5 sentences, densely detailed
   - Present tense throughout
   - The two non-negotiable qualities: PHOTOREALISTIC and EMOTIONALLY \
AUTHENTIC — every scene must meet both

4. **mood**: One of: warm, energetic, peaceful, romantic, confident, joyful, \
serene

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
- Keep descriptions natural and cinematic — weave appearance into the scene \
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
