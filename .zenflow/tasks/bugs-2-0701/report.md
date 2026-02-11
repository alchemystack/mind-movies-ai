# Bug Fix Report: Hardcoded Anthropic Model Default

## Problem

The Anthropic model was hardcoded to `claude-opus-4-20250514` in three locations:

1. **`src/mindmovie/config/settings.py:28`** — Default value for the `anthropic_model` field in `APISettings`
2. **`src/mindmovie/api/anthropic_client.py:26`** — `DEFAULT_MODEL` constant used as fallback in `AnthropicClient.__init__`
3. **`tests/integration/test_pipeline.py:60`** — Test fixture constructing `APISettings` with hardcoded model

Additionally, `.env.example` did not document the `ANTHROPIC_MODEL` environment variable, so users had no guidance on how to override the model selection.

## Root Cause

When model selection was recently added (via `ANTHROPIC_MODEL` env var with `validation_alias`), the default value was set to Opus rather than the more cost-effective Sonnet. The pipeline correctly passes `settings.api.anthropic_model` to the client constructor, but the defaults in both settings and client pointed to Opus.

## Changes Made

| File | Change |
|------|--------|
| `src/mindmovie/config/settings.py` | Default `anthropic_model` changed from `claude-opus-4-20250514` to `claude-sonnet-4-20250514` |
| `src/mindmovie/api/anthropic_client.py` | `DEFAULT_MODEL` constant changed from `claude-opus-4-20250514` to `claude-sonnet-4-20250514` |
| `tests/integration/test_pipeline.py` | Test fixture updated to use `claude-sonnet-4-20250514` |
| `.env.example` | Added documented `ANTHROPIC_MODEL` variable (commented out, showing default) |

## Verification

- **ruff check**: All checks passed
- **mypy**: Success, no issues found in 41 source files
- **pytest**: All 116 tests passed (18.62s)

## Notes

- Users who want to use Opus can set `ANTHROPIC_MODEL=claude-opus-4-20250514` in their `.env` file
- The `validation_alias="ANTHROPIC_MODEL"` on the settings field means the env var is automatically picked up by pydantic-settings
