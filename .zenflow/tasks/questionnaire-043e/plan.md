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

### [x] Step: Add data models and update questionnaire system prompt
<!-- chat-id: 05a4dc0d-4425-4d09-aa96-9573e6099efd -->

Implement the data model changes and questionnaire prompt changes together, plus their tests.

1. Add `PhysicalAppearance` model to `src/mindmovie/models/goals.py`
2. Add `appearance: PhysicalAppearance | None` and `initial_vision: str | None` fields to `ExtractedGoals`
3. Rewrite `SYSTEM_PROMPT` in `src/mindmovie/core/questionnaire.py` to:
   - Ask for pre-existing vision/summary first
   - Ask about physical appearance second
   - Then proceed with the 6 life categories as before
   - Update the completion JSON schema in the prompt to include `appearance` and `initial_vision`
4. Update `tests/fixtures/sample_goals.json` to include the new fields
5. Update `tests/unit/test_questionnaire.py`:
   - Update `SAMPLE_GOALS_JSON` with appearance and initial_vision
   - Add test for parsing with appearance present
   - Add test for parsing with appearance absent (backward compat)
   - Update system prompt assertion to check for appearance keywords
6. Run `ruff check src/ tests/` and `mypy src/` and `pytest tests/unit/ -v`

### [x] Step: Update scene generation to use appearance data
<!-- chat-id: 03ae4ce4-677c-4273-8e15-8f3e57205ded -->

Propagate appearance into scene generation prompts and update downstream tests/fixtures.

1. Add `SUBJECT APPEARANCE` section to `GENERATION_PROMPT` in `src/mindmovie/core/scene_generator.py`
2. Update `_build_user_message()` to include `appearance.description` and `initial_vision` when present
3. Update `tests/fixtures/sample_scenes.json` video prompts to include appearance-aware descriptions
4. Run `ruff check src/ tests/` and `mypy src/` and `pytest tests/ -v` (full test suite)
5. Write report to `{@artifacts_path}/report.md`

