# Technical Specification: Affirmation Cleanup & Model Default Fix

## Difficulty: Medium

Two interrelated issues need fixing: (1) the obsolete affirmation validation that crashes the pipeline, and (2) the hardcoded Anthropic model default that doesn't use a sensible, cost-effective default.

## Technical Context

- **Language**: Python 3.11+
- **Key Dependencies**: Pydantic v2, Anthropic SDK, MoviePy, Pillow, Typer
- **Test Framework**: pytest with asyncio_mode=auto

## Problem Analysis

### Bug 1: Affirmation Prefix Validator Crashes Pipeline

The `Scene` model in `src/mindmovie/models/scenes.py:33-52` has a `field_validator` that enforces affirmations must start with one of: "i am", "i have", "i feel", "i live". However, the LLM's scene generation routinely produces affirmations like "I lead...", "I glide...", "I dance...", "I work...", "I drive...", etc. — perfectly valid first-person present-tense affirmations that fail the overly restrictive prefix check.

The original design intended affirmations to be used as voice-over text with a very constrained format. Since voice-over was removed, affirmations now serve as **text overlays** on each video scene. The restrictive prefix validator is no longer justified and actively prevents the pipeline from completing.

**Root cause**: `validate_affirmation_format()` in `Scene` rejects any affirmation not starting with exactly "I am/have/feel/live", but the LLM prompt (`GENERATION_PROMPT` in `scene_generator.py:24-30`) instructs it to generate these constrained prefixes. The LLM frequently doesn't comply because the affirmation content naturally suggests other "I + verb" constructions.

**Impact**: Pipeline crashes at scene generation stage (100% repro when LLM generates diverse affirmations).

### Bug 2: Hardcoded Anthropic Model Default

The `APISettings` in `src/mindmovie/config/settings.py:27-31` defaults `anthropic_model` to `"claude-opus-4-20250514"`, and the `DEFAULT_MODEL` constant in `src/mindmovie/api/anthropic_client.py:26` also hardcodes this value. While valid, this is the most expensive Anthropic model and was set during a previous bug fix without considering cost implications. The model should default to a more appropriate model for the task (questionnaire + scene generation don't require Opus-level reasoning).

Additionally, `.env.example` does not document the `ANTHROPIC_MODEL` environment variable, so users don't know they can override the model.

## Implementation Approach

### Fix 1: Remove Overly Restrictive Affirmation Validator

The affirmation field on `Scene` should remain (it is used as text overlay on video clips and as the closing card text), but the prefix validation should be relaxed. Since affirmations are now text overlays rather than voice-over scripts, the only constraint that matters is that they are non-empty, reasonably sized, and first-person (start with "I").

**Changes**:

1. **`src/mindmovie/models/scenes.py`**:
   - Remove the `AFFIRMATION_PREFIXES` constant (line 10)
   - Replace `validate_affirmation_format()` validator (lines 33-52) with a simpler validator that only checks the affirmation starts with "I " (first person) and contains no obvious negative words
   - Update the `Scene` docstring (line 14) — change "with affirmation" to "with text overlay" or keep as-is (minor)

2. **`src/mindmovie/core/scene_generator.py`**:
   - Update `GENERATION_PROMPT` (lines 24-30) — relax the affirmation instructions. Remove the "Must start with I am/have/feel/live" constraint. Instead instruct: "First person, present tense, positive, 5-12 words. Must start with 'I'."
   - This ensures the LLM still produces first-person affirmations but isn't restricted to 4 prefixes

3. **Tests** (`tests/unit/test_models.py`, `tests/integration/test_composer.py`, `tests/unit/test_state_manager.py`):
   - Update `test_invalid_prefix_rejected` to test the new (relaxed) validation
   - Update `test_valid_prefixes` to include broader first-person constructions
   - Existing test fixtures (`tests/fixtures/sample_scenes.json`, `tests/fixtures/sample_llm_responses.json`) already use "I am/have" prefixes and remain valid

### Fix 2: Change Anthropic Model Default

**Changes**:

1. **`src/mindmovie/config/settings.py`**:
   - Change `anthropic_model` default from `"claude-opus-4-20250514"` to `"claude-sonnet-4-20250514"` (Sonnet 4 is a good balance of capability and cost for questionnaire/scene generation tasks)

2. **`src/mindmovie/api/anthropic_client.py`**:
   - Change `DEFAULT_MODEL` from `"claude-opus-4-20250514"` to `"claude-sonnet-4-20250514"` to keep them in sync

3. **`.env.example`**:
   - Add `ANTHROPIC_MODEL=claude-sonnet-4-20250514` with comment explaining override capability

4. **Tests** (`tests/integration/test_pipeline.py` and any other tests referencing the model):
   - Update hardcoded model strings to match new default

## Source Code Files to Modify

| File | Change |
|------|--------|
| `src/mindmovie/models/scenes.py` | Remove AFFIRMATION_PREFIXES, relax validator to "starts with I" |
| `src/mindmovie/core/scene_generator.py` | Relax GENERATION_PROMPT affirmation instructions |
| `src/mindmovie/config/settings.py` | Change anthropic_model default to claude-sonnet-4-20250514 |
| `src/mindmovie/api/anthropic_client.py` | Change DEFAULT_MODEL to claude-sonnet-4-20250514 |
| `.env.example` | Document ANTHROPIC_MODEL variable |
| `tests/unit/test_models.py` | Update affirmation validation tests |
| `tests/integration/test_pipeline.py` | Update model string in test fixture |

## Files NOT Changed (Affirmation Still Used Correctly)

These files use `scene.affirmation` and `spec.closing_affirmation` for text overlay rendering. This is valid functionality that should remain:

- `src/mindmovie/video/text_overlay.py` — `render_affirmation_overlay()` and `render_closing_card()` render text on video
- `src/mindmovie/video/composer.py` — `_create_scene_clip()` composites affirmation text overlay; `_create_closing_card()` renders closing text
- `src/mindmovie/video/__init__.py` — exports remain unchanged
- `src/mindmovie/assets/video_generator.py` — logging only
- `src/mindmovie/cli/commands/compile_cmd.py` — docstring only
- `src/mindmovie/cli/app.py` — help text only
- `tests/fixtures/sample_scenes.json` — already uses valid "I am/have" prefixes
- `tests/fixtures/sample_llm_responses.json` — already uses valid prefixes
- `tests/integration/test_composer.py` — test data already uses valid "I am" prefix

## Verification Approach

1. `ruff check src/ tests/` — linting passes
2. `mypy src/` — type checking passes
3. `pytest tests/unit/ -v` — all unit tests pass (especially updated affirmation tests)
4. `pytest tests/integration/ -v` — all integration tests pass
5. Manual: verify that affirmations like "I lead...", "I dance...", "I work..." pass the relaxed validator
6. Manual: verify the `APISettings()` default model is `claude-sonnet-4-20250514`
