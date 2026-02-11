# Bug Investigation: Veo API `personGeneration` Error

## Bug Summary

All 12 scene video generations fail with:
```
ClientError: 400 INVALID_ARGUMENT.
{'error': {'code': 400, 'message': 'allow_adult for personGeneration is currently not supported.', 'status': 'INVALID_ARGUMENT'}}
```

## Root Cause Analysis

### Primary Issue: Wrong `person_generation` value for text-to-video

**File:** `src/mindmovie/api/veo_client.py`, line 83

The code currently sets:
```python
person_generation="allow_adult"
```

According to the [Google Veo API docs](https://ai.google.dev/gemini-api/docs/video), the `personGeneration` parameter has **different allowed values depending on the use case**:

| Use Case | Veo 3.1 / 3.1 Fast Allowed Values |
|---|---|
| **Text-to-video** (our use case) | `"allow_all"` only |
| Image-to-video | `"allow_adult"` only |
| Interpolation | `"allow_adult"` only |
| Reference images | `"allow_adult"` only |

This app does **text-to-video generation**, so the only valid value is `"allow_all"` -- not `"allow_adult"`.

### Secondary Issue: Resolution casing mismatch (potential)

**File:** `src/mindmovie/config/settings.py`, line 43

The settings define the 4K resolution option as uppercase `"4K"`:
```python
resolution: Literal["720p", "1080p", "4K"] = Field(...)
```

But the Google API docs specify lowercase `"4k"` as the accepted value. The default is `"1080p"` so this doesn't trigger today, but would fail if a user configured 4K output.

## Affected Components

1. **`src/mindmovie/api/veo_client.py`** - `_generate_and_poll()` method, line 83
   - Passes invalid `person_generation="allow_adult"` in `GenerateVideosConfig`
2. **`src/mindmovie/config/settings.py`** - `VideoSettings.resolution`, line 43
   - Accepts `"4K"` but the API expects `"4k"`
3. **`tests/unit/test_veo_client.py`** - Tests don't verify the config parameters passed to the API

## Proposed Solution

### Fix 1: Change `person_generation` value (critical)

In `veo_client.py:83`, change:
```python
person_generation="allow_adult"
```
to:
```python
person_generation="allow_all"
```

This is the only valid value for text-to-video generation on Veo 3.1 models.

### Fix 2: Normalize resolution casing (defensive)

In `veo_client.py`, normalize the resolution value to lowercase before passing it to the API:
```python
resolution=resolution.lower()
```

And update the `VideoSettings.resolution` Literal type in `settings.py` to use lowercase `"4k"` to match the API:
```python
resolution: Literal["720p", "1080p", "4k"]
```

### Fix 3: Add a regression test

Add a test in `test_veo_client.py` that verifies the correct config parameters are passed to `generate_videos()`, specifically:
- `person_generation="allow_all"`
- The resolution value is lowercase

## Edge Cases and Side Effects

- **Regional restrictions**: In EU/UK/CH/MENA regions, Veo 3 only allows `"allow_adult"` for person generation. However, since `"allow_adult"` isn't valid for text-to-video anyway, users in those regions may face a different error. The API documentation isn't clear on how this interacts. The safest approach is to use `"allow_all"` (the documented text-to-video value) and let the API handle regional restrictions.
- **Veo 2 models**: For `veo-2.0-generate-001`, the valid values include `"allow_all"`, `"allow_adult"`, and `"dont_allow"`. Using `"allow_all"` is valid across all model versions for text-to-video.
- **No breaking changes**: These are config value changes only; no API surface or protocol changes needed.

## Implementation Notes

### Changes Made

1. **`src/mindmovie/api/veo_client.py:83`** — Changed `person_generation="allow_adult"` to `person_generation="allow_all"` (critical fix)
2. **`src/mindmovie/api/veo_client.py:82`** — Added `resolution.lower()` to normalize resolution casing at the API boundary (defensive fix)
3. **`tests/unit/test_veo_client.py`** — Added `TestVeoClientConfig` class with two regression tests:
   - `test_person_generation_is_allow_all` — asserts the config passed to `generate_videos()` uses `"allow_all"`
   - `test_resolution_sent_lowercase` — asserts that `"4K"` input is sent as `"4k"` to the API

### Decision: Resolution normalization at API boundary only

The internal `VideoSettings.resolution` Literal type still uses `"4K"` (uppercase) because:
- The `text_overlay.py` lookup table uses `"4K"` as a key for `(3840, 2160)` pixel dimensions
- Changing the Literal would break existing YAML configs and the text overlay
- Normalizing at the API boundary (`resolution.lower()` in `veo_client.py`) is the minimal change that fixes the issue without ripple effects

### Test Results

- 129/129 tests pass (127 existing + 2 new regression tests)
- ruff: all checks passed
- mypy: no issues found
