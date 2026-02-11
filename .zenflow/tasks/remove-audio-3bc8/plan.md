# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification

Specification saved to `.zenflow/tasks/remove-audio-3bc8/spec.md`.

Difficulty: Easy-Medium. The fix is straightforward (remove invalid `generate_audio` parameter from Veo API calls), but the parameter is threaded through 8 source files and 2 test files.

Key decision: Veo 3.x natively generates audio — there is no opt-in toggle. Remove `generate_audio` from all layers. Keep background music mixing (`MusicSettings`, `mix_audio()`) since it's unrelated to the Veo API error.

---

### [x] Step: Implementation

Removed `generate_audio` parameter from API layer, protocol, settings, cost estimation, CLI display, and video generator. Updated affected unit tests. All verification passed.

**Source files modified (6):**
- `src/mindmovie/api/veo_client.py` — Removed `generate_audio` param; simplified cost dict to single rate
- `src/mindmovie/api/base.py` — Removed from protocol
- `src/mindmovie/config/settings.py` — Removed `generate_audio` field
- `src/mindmovie/assets/video_generator.py` — Removed kwarg
- `src/mindmovie/core/cost_estimator.py` — Simplified to single rate per model
- `src/mindmovie/cli/commands/config_cmd.py` — Removed from display

**Test files updated (2):**
- `tests/unit/test_veo_client.py` — Updated cost test
- `tests/unit/test_cost_estimator.py` — Updated settings helper and expected costs

**Verification:**
- [x] `ruff check src/ tests/` — All checks passed
- [x] `mypy src/` — No issues found in 41 source files
- [x] `pytest tests/ -v` — 116 passed
- [x] `grep -r "generate_audio" src/` — Zero matches
- [x] `grep -r "with_audio" src/` — Only MoviePy's `VideoClip.with_audio()` (unrelated)

Report saved to `.zenflow/tasks/remove-audio-3bc8/report.md`.
