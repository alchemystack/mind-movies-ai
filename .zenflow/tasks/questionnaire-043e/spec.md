# Technical Specification: Enhanced Questionnaire with Physical Appearance & Pre-existing Vision

## Task Summary

Modify the Coach LLM questionnaire to:
1. **Ask for physical appearance** at the beginning (height, weight, skin color, hair color/style, etc.) so the generated video prompts can depict a person that roughly matches the user.
2. **Ask if the user already has a summary or vision** they'd like to paste in, enabling a fast-track flow where users can supply pre-existing material before the guided conversation begins.

## Difficulty Assessment: **Medium**

- Two new conversational phases in the system prompt
- A new data model field for appearance
- Downstream propagation of appearance data into scene generation prompts
- Updates to fixtures and tests
- No new API calls, no architectural changes

---

## Technical Context

- **Language**: Python 3.11+
- **Key deps**: Pydantic v2, Anthropic SDK, Typer, Rich
- **LLM interaction**: `AnthropicClient.chat()` for multi-turn conversation; `AnthropicClient.generate_structured()` for scene generation
- **Models**: `ExtractedGoals` (goals.py), `MindMovieSpec` / `Scene` (scenes.py)
- **Prompt location**: `SYSTEM_PROMPT` in `core/questionnaire.py`, `GENERATION_PROMPT` in `core/scene_generator.py`

---

## Implementation Approach

### 1. New Data Model: `PhysicalAppearance`

Add an optional structured field to `ExtractedGoals` to carry the user's physical description through the pipeline.

**File**: `src/mindmovie/models/goals.py`

Add a new Pydantic model:

```python
class PhysicalAppearance(BaseModel):
    """Physical appearance details for consistent video depiction."""
    description: str = Field(
        ...,
        description="Free-form physical appearance description (height, build, skin tone, hair color/style, etc.)"
    )
```

Add to `ExtractedGoals`:
```python
class ExtractedGoals(BaseModel):
    ...
    appearance: PhysicalAppearance | None = Field(
        default=None,
        description="User's physical appearance for consistent video depiction",
    )
    initial_vision: str | None = Field(
        default=None,
        description="User's pre-existing vision summary, pasted at the start",
    )
```

**Rationale**: A single free-form `description` string is better than individual fields (height, weight, skin_color, hair_color, etc.) because:
- The Coach LLM extracts a natural-language summary that maps directly to video prompt language
- Avoids rigid schema mismatch with the variety of physical attributes people may describe
- The downstream consumer (scene generation prompt) needs prose, not structured fields

### 2. Updated Questionnaire System Prompt

**File**: `src/mindmovie/core/questionnaire.py`

Modify `SYSTEM_PROMPT` to insert two new phases at the beginning of the WORKFLOW, before the 6 life categories:

```
WORKFLOW:
1. Greet warmly. Explain that you'll create a personalized mind movie together.
2. FIRST, ask if the user already has a summary, notes, or vision for their
   ideal life that they'd like to share upfront. If they paste text, acknowledge
   it and use it as context for the rest of the conversation. If they say no,
   proceed normally.
3. NEXT, ask about their physical appearance so the video can depict someone
   who looks like them. Ask about:
   - General build (height, body type)
   - Skin tone
   - Hair color and style
   - Any other distinguishing features they'd like shown
   Summarize what you heard and confirm.
4. For each area (Health, Wealth, Career, Relationships, Growth, Lifestyle):
   a. Ask ONE open-ended question about their vision
   ...
```

Update the completion JSON schema in the prompt to include:
```json
{
  "title": "...",
  "appearance": {
    "description": "consolidated physical appearance summary"
  },
  "initial_vision": "the text the user pasted, or null if none",
  "categories": [...]
}
```

**Key behavioral rules to add**:
- If the user provides a pre-existing vision, use it to pre-fill context and skip questions for areas already well-covered, while still confirming and probing for missing visual details.
- The appearance question should be brief and conversational — not a form. Ask naturally, then summarize back.
- If the user declines to share appearance details, proceed without them (the field becomes null).

### 3. Updated Scene Generation Prompt

**File**: `src/mindmovie/core/scene_generator.py`

Modify `GENERATION_PROMPT` to instruct the scene designer to use appearance data:

Add a new section:
```
SUBJECT APPEARANCE:
- If physical appearance is provided, use it consistently in ALL video prompts
- Replace generic "person" with appearance-matching descriptions
- Example: Instead of "A vibrant person in athletic wear", use
  "A tall woman with warm brown skin and curly dark hair in athletic wear"
- Keep descriptions natural and cinematic — weave appearance into the scene
  rather than listing traits mechanically
- If no appearance is provided, use generic inclusive descriptions
```

Modify `_build_user_message()` to include appearance data:
```python
def _build_user_message(self, goals: ExtractedGoals) -> str:
    parts = []
    parts.append(f"Title: {goals.title}")
    parts.append(f"Target number of scenes: {self.num_scenes}")
    parts.append("")

    if goals.appearance:
        parts.append(f"## Subject Appearance")
        parts.append(goals.appearance.description)
        parts.append("")

    if goals.initial_vision:
        parts.append(f"## Initial Vision Summary")
        parts.append(goals.initial_vision)
        parts.append("")

    for cat_goal in goals.categories:
        ...
```

### 4. Parsing Logic Update

**File**: `src/mindmovie/core/questionnaire.py`

The `_parse_completion()` method needs no structural changes — it already parses arbitrary JSON and validates against `ExtractedGoals` via `model_validate()`. Since the new fields (`appearance`, `initial_vision`) have defaults (`None`), backward compatibility is preserved. The LLM is instructed in the system prompt to include them in the completion JSON.

### 5. Test Updates

**File**: `tests/unit/test_questionnaire.py`

- Update `SAMPLE_GOALS_JSON` to include `appearance` and `initial_vision` fields
- Add test: completion parsing with appearance data present
- Add test: completion parsing with appearance data absent (null) — backward compat
- Update `TestSystemPrompt.test_mentions_categories_and_marker` to also check for appearance-related keywords

**File**: `tests/unit/test_scene_generator.py`

- No structural changes needed (fixtures drive the tests)

**File**: `tests/fixtures/sample_goals.json`

- Add `appearance` and `initial_vision` fields to the fixture

**File**: `tests/fixtures/sample_scenes.json`

- Update a few video prompts to show appearance-aware descriptions (to match what the updated scene generator would produce)

---

## Source Code Changes Summary

| File | Change |
|------|--------|
| `src/mindmovie/models/goals.py` | Add `PhysicalAppearance` model; add `appearance` and `initial_vision` fields to `ExtractedGoals` |
| `src/mindmovie/core/questionnaire.py` | Rewrite `SYSTEM_PROMPT` to add pre-vision and appearance phases; update completion JSON schema in prompt |
| `src/mindmovie/core/scene_generator.py` | Add appearance instructions to `GENERATION_PROMPT`; update `_build_user_message()` to include appearance and initial_vision |
| `tests/unit/test_questionnaire.py` | Update sample JSON; add tests for new fields; update prompt assertion |
| `tests/fixtures/sample_goals.json` | Add `appearance` and `initial_vision` fields |
| `tests/fixtures/sample_scenes.json` | Update video prompts with appearance-aware descriptions |

---

## Data Model Changes

### `PhysicalAppearance` (NEW)
```
description: str  — free-form physical appearance summary
```

### `ExtractedGoals` (MODIFIED)
```
+ appearance: PhysicalAppearance | None = None
+ initial_vision: str | None = None
```

### No changes to:
- `Scene`, `MindMovieSpec` — these receive appearance data indirectly via the generation prompt
- `CategoryGoal`, `LifeCategory` — unchanged
- `PipelineState`, `StateManager` — goals are stored/loaded as JSON, new fields serialize naturally
- API clients — no interface changes

---

## Verification Approach

1. **Linting**: `ruff check src/ tests/` — ensure no style violations
2. **Type checking**: `mypy src/` — strict mode, verify new model fields are typed correctly
3. **Unit tests**: `pytest tests/unit/ -v` — all existing + new tests pass
4. **Integration test**: `pytest tests/integration/ -v` — CLI-level tests still pass
5. **Manual verification**: Run `mindmovie questionnaire` and verify:
   - Coach asks for pre-existing vision first
   - Coach asks about physical appearance second
   - Both are reflected in the saved `goals.json`
   - Scene generation includes appearance in video prompts

---

## Edge Cases & Considerations

- **User declines both**: User says "no" to pre-existing vision and "skip" to appearance. Both fields are `null` — pipeline continues unchanged from current behavior.
- **State compatibility**: Existing `goals.json` files from previous runs lack `appearance` and `initial_vision`. Since both default to `None`, `model_validate()` handles old data gracefully.
- **Prompt length**: Adding appearance to every video prompt increases token usage slightly in scene generation. This is negligible (~20 tokens per scene, ~240 total).
- **Privacy**: Physical appearance data is stored in `build/goals.json` alongside other personal vision data. No new privacy surface — same local-only storage model.
