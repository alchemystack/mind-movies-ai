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
<!-- chat-id: de0573a0-740e-4918-8c81-58aa86437b03 -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Important: unit tests must be part of each implementation task, not separate tasks. Each task should implement the code and its tests together, if relevant.

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Relax affirmation validator and update scene generation prompt
<!-- chat-id: d22f08b1-9d47-42a5-815b-da4b18e0fb52 -->

Fix the primary crash: the `Scene.validate_affirmation_format()` validator in `src/mindmovie/models/scenes.py` rejects valid first-person affirmations that don't start with "I am/have/feel/live". Also update the LLM prompt.

- Remove `AFFIRMATION_PREFIXES` constant
- Replace `validate_affirmation_format()` with a relaxed validator that checks "starts with I" only
- Update `GENERATION_PROMPT` in `src/mindmovie/core/scene_generator.py` to remove the prefix constraint
- Update unit tests in `tests/unit/test_models.py` for the new validation rules
- Run `ruff check src/ tests/` and `pytest tests/ -v` to verify

### [ ] Step: Fix hardcoded Anthropic model default and update .env.example

Change the default model from Opus to Sonnet for cost-effectiveness.

- Change default in `src/mindmovie/config/settings.py` (`anthropic_model` field) to `claude-sonnet-4-20250514`
- Change `DEFAULT_MODEL` in `src/mindmovie/api/anthropic_client.py` to match
- Add `ANTHROPIC_MODEL` to `.env.example` with documentation
- Update any test fixtures referencing the old model default
- Run `ruff check src/ tests/`, `mypy src/`, and `pytest tests/ -v` to verify all passes
- Write report to `{@artifacts_path}/report.md`
