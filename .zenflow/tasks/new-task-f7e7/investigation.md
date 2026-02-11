# Investigation: MindMovieSpec Validation Error After Questionnaire

## Bug Summary

After completing the questionnaire, the pipeline crashes at scene generation with:
```
ValidationError: 2 validation errors for MindMovieSpec
scenes - Field required
music_mood - Field required
```

The LLM returns data wrapped in `{"output": {...}}` but the code expects top-level fields.

## Root Cause

**File**: `src/mindmovie/core/scene_generator.py:127`

The Anthropic API's tool-use response contains the MindMovieSpec data nested inside an `"output"` key:
```python
result = {"output": {"title": "My Vision", "scenes": [...], "music_mood": "..."}}
```

But `scene_generator.py` does:
```python
spec = MindMovieSpec.model_validate(result)  # Fails — looks for top-level "scenes"
```

`MindMovieSpec` expects `scenes` and `music_mood` at the top level, but they're inside `result["output"]`.

### Why tests pass but production fails

The test fixture `tests/fixtures/sample_scenes.json` stores data **without** the `"output"` wrapper (flat structure), so the mock `generate_structured` returns clean data. The real Claude API wraps the tool input differently.

## Affected Components

1. `src/mindmovie/core/scene_generator.py` - `SceneGenerator.generate()` line 127
2. `tests/unit/test_scene_generator.py` - mock doesn't match real API behavior

## Proposed Fix

**Simple approach — unwrap in `scene_generator.py`**:

In `SceneGenerator.generate()`, after receiving `result` from `generate_structured`, unwrap the `"output"` key if present before validating:

```python
result = await self.client.generate_structured(...)

# Unwrap if the LLM wrapped in {"output": {...}}
if "output" in result and isinstance(result["output"], dict):
    result = result["output"]

spec = MindMovieSpec.model_validate(result)
```

This is the simplest fix because:
- It handles both wrapped and unwrapped responses
- No changes needed to the Anthropic client (which correctly returns what the API gives)
- Minimal code change, easy to understand

**Also fix the test fixture** (`mock_client`) to return wrapped data matching real API behavior, so the test actually covers this path.

### User's request to simplify

The user asked to "remove all unnecessary bullshit and redundant code." During implementation, also simplify:
- Remove excessive docstrings/comments that just restate obvious code
- Remove the redundant `MindMovieSpec.model_validate()` call — `generate_structured` already returns a dict matching the schema, so we can validate once after unwrapping
- Simplify `SceneGenerator` class if methods are trivially small
