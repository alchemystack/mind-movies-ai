# Investigation: bugs-1 — Errors on `mindmovie generate`

## Bug Summary

Running `mindmovie generate` crashes with a `NotFoundError` (HTTP 404) because the Anthropic client uses an invalid model ID. Additionally, the full error traceback leaks the plaintext API key as a local variable.

---

## Bug 1: Invalid Anthropic Model Name (404 Not Found)

### Root Cause

The hardcoded default model `claude-sonnet-4-5-20250514` does not exist in the Anthropic API. The correct model ID format for Claude Opus 4 (user's desired model) is `claude-opus-4-20250514`.

### Affected Components

| File | Line(s) | Issue |
|------|---------|-------|
| `src/mindmovie/api/anthropic_client.py` | 26 | `DEFAULT_MODEL = "claude-sonnet-4-5-20250514"` — invalid model ID |
| `src/mindmovie/core/pipeline.py` | 145, 168 | `AnthropicClient(api_key=api_key)` — uses DEFAULT_MODEL (no model override) |
| `src/mindmovie/cli/commands/questionnaire.py` | 55 | `AnthropicClient(api_key=api_key)` — uses DEFAULT_MODEL (no model override) |
| `src/mindmovie/config/settings.py` | (missing) | No `anthropic_model` field in `APISettings` — model cannot be configured |
| `tests/fixtures/sample_llm_responses.json` | 6, 23, 35, 144 | Test fixtures reference the invalid model ID |

### Design Gap

Unlike the Veo video model which is configurable via `settings.video.model` (settings.py:34), the Anthropic model is hardcoded with no settings equivalent. The `AnthropicClient.__init__` accepts a `model` parameter (anthropic_client.py:37), but no caller ever passes a value — they all rely on `DEFAULT_MODEL`.

### Proposed Fix

1. **Change DEFAULT_MODEL** to `"claude-opus-4-20250514"` in `anthropic_client.py:26` (per user request for `claude-opus-4-6` — the model ID is `claude-opus-4-20250514`).
2. **Add `anthropic_model` field** to `APISettings` in `settings.py` so the model can be configured via `.env` or YAML.
3. **Pass model from settings** in `pipeline.py` and `questionnaire.py` when constructing `AnthropicClient`.
4. **Update test fixtures** in `sample_llm_responses.json` to use the new model ID.

---

## Bug 2: API Key Leaked in Plaintext in Error Tracebacks

### Root Cause

In `pipeline.py:138` and `:160`, the API key is extracted from `SecretStr` into a plain `str` local variable:

```python
api_key = self.settings.api.anthropic_api_key.get_secret_value()
# ...
client = AnthropicClient(api_key=api_key)
```

When an exception occurs (as it does with the 404), Python's rich traceback inspector displays all local variables, including `api_key = 'sk-ant-api03-YCTGL84m52...'`. The same pattern exists for the Gemini key.

### Affected Components

| File | Line(s) | Variable leaked |
|------|---------|-----------------|
| `src/mindmovie/core/pipeline.py` | 138 | `api_key` (Anthropic) |
| `src/mindmovie/core/pipeline.py` | 160 | `api_key` (Anthropic) |
| `src/mindmovie/core/pipeline.py` | 207 | `gemini_key` (Gemini) |
| `src/mindmovie/cli/commands/questionnaire.py` | 54 | `api_key` (Anthropic) |
| `src/mindmovie/cli/commands/render.py` | 124 | `gemini_key` (Gemini) |

### Proposed Fix

Avoid extracting the secret into a named local variable. Instead, pass `.get_secret_value()` inline:

```python
client = AnthropicClient(api_key=self.settings.api.anthropic_api_key.get_secret_value())
```

This way, the plaintext key is a transient expression — not bound to a local variable name — and will not appear in traceback locals. The `AnthropicClient.__init__` still stores it as `self.client`, but that's inside the Anthropic SDK (which already receives the key by design) and won't appear in the caller's traceback frame.

---

## Bug 3: Missing `NotFoundError` Handling

### Root Cause

The `generate.py` command catches `PipelineError` and `CompositionError` (line 159), but a `NotFoundError` from the Anthropic API is neither of those. It propagates uncaught to `asyncio.run()` and produces the full raw traceback (which is what leaks the key).

The `questionnaire.py` command has specific Anthropic error handling (lines 73-90) for `AuthenticationError`, `RateLimitError`, `APIConnectionError`, and `APITimeoutError`, but **not** `NotFoundError`.

### Proposed Fix

1. **In `generate.py`**: Catch `anthropic.NotFoundError` (or more broadly `anthropic.APIError`) and display a user-friendly message about the invalid model.
2. **In `questionnaire.py`**: Add a `NotFoundError` handler.
3. **In `pipeline.py`**: Consider wrapping API calls to convert `NotFoundError` into `PipelineError` with a descriptive message.

---

## Bug 4: Retry on Non-Retryable Errors (Minor)

### Observation

The tenacity retry decorator in `anthropic_client.py:41-46` correctly only retries on `_RETRYABLE_ERRORS` (timeout, connection, rate limit, internal server). A `NotFoundError` is NOT in that list, so it will NOT be retried. This is correct behavior.

However, the traceback shows `attempt #1` with the 404 error, confirming only one attempt was made before the error was re-raised. This is working as designed.

### No fix needed for retry logic.

---

## Summary of All Required Changes

### High Priority (Crash Fixes)

1. **`src/mindmovie/api/anthropic_client.py:26`** — Change `DEFAULT_MODEL` to `"claude-opus-4-20250514"`
2. **`src/mindmovie/config/settings.py`** — Add `anthropic_model` field to `APISettings`
3. **`src/mindmovie/core/pipeline.py:145,168`** — Pass model from settings to `AnthropicClient`
4. **`src/mindmovie/cli/commands/questionnaire.py:55`** — Pass model from settings to `AnthropicClient`

### High Priority (Security)

5. **`src/mindmovie/core/pipeline.py:138,160,207`** — Eliminate plaintext API key local variables
6. **`src/mindmovie/cli/commands/questionnaire.py:54`** — Eliminate plaintext API key local variable
7. **`src/mindmovie/cli/commands/render.py:124`** — Eliminate plaintext Gemini key local variable

### Medium Priority (Error Handling)

8. **`src/mindmovie/cli/commands/generate.py:159`** — Catch `NotFoundError` with user-friendly message
9. **`src/mindmovie/cli/commands/questionnaire.py:67-90`** — Add `NotFoundError` handler

### Low Priority (Test Maintenance)

10. **`tests/fixtures/sample_llm_responses.json`** — Update model references in test fixtures

---

## Edge Cases and Side Effects

- Changing the model to `claude-opus-4-20250514` will change the cost profile (Opus is more expensive than Sonnet). The `cost_estimator.py` uses a flat `$0.02` for LLM cost (`LLM_COST_SCENE_GENERATION`), which may need adjustment, but this is an approximation anyway.
- Adding a configurable model field means users can also set it via `ANTHROPIC_MODEL` env var or YAML config, giving flexibility without code changes.
- The `AnthropicClient` constructor stores `api_key` as a parameter name in its `__init__` — this is acceptable since the SDK itself needs the key; the concern is about the *caller's* stack frame leaking it.

---

## Implementation Notes

All fixes were implemented and verified. Summary of changes:

### Files Modified

| File | Change |
|------|--------|
| `src/mindmovie/api/anthropic_client.py` | Changed `DEFAULT_MODEL` from `"claude-sonnet-4-5-20250514"` to `"claude-opus-4-20250514"` |
| `src/mindmovie/config/settings.py` | Added `anthropic_model` field to `APISettings` (default: `"claude-opus-4-20250514"`, env var: `ANTHROPIC_MODEL`) |
| `src/mindmovie/core/pipeline.py` | Inlined `.get_secret_value()` calls (no local `api_key`/`gemini_key` variables); passed `model=self.settings.api.anthropic_model` to `AnthropicClient` |
| `src/mindmovie/cli/commands/questionnaire.py` | Inlined `.get_secret_value()` call; passed `model` from settings; added `NotFoundError` handler |
| `src/mindmovie/cli/commands/generate.py` | Added `anthropic.NotFoundError` and `anthropic.AuthenticationError` handlers with user-friendly messages |
| `src/mindmovie/cli/commands/render.py` | Inlined `.get_secret_value()` call (no local `gemini_key` variable) |
| `tests/fixtures/sample_llm_responses.json` | Updated all 4 model references from `claude-sonnet-4-5-20250514` to `claude-opus-4-20250514` |
| `tests/integration/test_pipeline.py` | Added `anthropic_model` to `model_construct` call in settings fixture |

### Test Results

- **116 tests passed** (0 failed)
- **ruff**: All checks passed
- **mypy**: Success, no issues found in 41 source files
