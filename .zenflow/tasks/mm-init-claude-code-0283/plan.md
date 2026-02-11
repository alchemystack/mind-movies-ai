# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 2f72db75-2021-443c-919d-19c4d60843af -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 576e62af-190c-42db-a9b0-6ebee56b173a -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: dcc74354-d46d-4c94-859b-9e710a093e84 -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint). Avoid steps that are too granular (single function) or too broad (entire feature).

Important: unit tests must be part of each implementation task, not separate tasks. Each task should implement the code and its tests together, if relevant.

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

# Implementation Plan

## Phase 1: Foundation (Core Infrastructure)

### [x] Step: Project Setup and Configuration
<!-- chat-id: e9dbb6ef-bbd9-4e79-8135-b7187d236361 -->

Set up the Python project structure with all foundational files:

1. Create `pyproject.toml` with project metadata and dependencies (see spec section 12)
2. Create `.gitignore` with Python/Node patterns
3. Create directory structure as specified in spec section 3:
   - `src/mindmovie/` with all subpackages
   - `tests/` with unit/integration/fixtures directories
4. Create `src/mindmovie/__init__.py` with version
5. Create `src/mindmovie/__main__.py` entry point
6. Create `.env.example` with required API keys
7. Create `config.example.yaml` with default settings

**Verification:**
- Run `pip install -e .` successfully
- Run `python -m mindmovie --help` shows CLI placeholder

### [x] Step: Configuration Management
<!-- chat-id: 0ed3dfc3-6b64-4034-88eb-fc91e059b41b -->

Implement configuration loading with Pydantic Settings:

1. Create `src/mindmovie/config/settings.py` with all settings models:
   - `APISettings`, `VideoSettings`, `MovieSettings`, `Settings`
   - Environment variable loading from `.env`
   - Nested configuration support
2. Create `src/mindmovie/config/loader.py` for YAML config file parsing
3. Create `src/mindmovie/config/__init__.py` with `load_settings()` function
4. Add unit tests in `tests/unit/test_config.py`:
   - Test env var loading
   - Test YAML config parsing
   - Test settings validation
   - Test defaults

**Verification:**
- `pytest tests/unit/test_config.py -v` passes
- `ruff check src/mindmovie/config/`

### [x] Step: Data Models
<!-- chat-id: aea6a91f-2623-443d-a51a-d8269289f7e3 -->

Implement all Pydantic data models:

1. Create `src/mindmovie/models/goals.py`:
   - `LifeCategory` enum
   - `CategoryGoal` model
   - `ExtractedGoals` model
2. Create `src/mindmovie/models/scenes.py`:
   - `Scene` model with affirmation validator
   - `MindMovieSpec` model
3. Create `src/mindmovie/models/movie.py`:
   - Any additional movie specification models
4. Create `src/mindmovie/models/__init__.py` with exports
5. Add unit tests in `tests/unit/test_models.py`:
   - Test model validation
   - Test affirmation validation rules
   - Test serialization/deserialization

**Verification:**
- `pytest tests/unit/test_models.py -v` passes
- `ruff check src/mindmovie/models/`

### [x] Step: State Management
<!-- chat-id: 09bad00c-cb83-4ecb-a4d0-33a290d95cb6 -->

Implement pipeline state persistence for resume capability:

1. Create `src/mindmovie/state/models.py`:
   - `PipelineStage` enum
   - `AssetStatus` enum
   - `SceneAsset` model
   - `PipelineState` model with helper methods
2. Create `src/mindmovie/state/manager.py`:
   - `StateManager` class with all CRUD operations
   - File-based persistence to `build/` directory
   - Methods: `exists()`, `load_or_create()`, `save()`, `clear()`
   - Goal/scene loading and saving
   - Stage completion tracking
3. Create `src/mindmovie/state/__init__.py` with exports
4. Add unit tests in `tests/unit/test_state_manager.py`:
   - Test state persistence
   - Test resume detection
   - Test stage transitions
   - Test asset tracking

**Verification:**
- `pytest tests/unit/test_state_manager.py -v` passes
- `ruff check src/mindmovie/state/`

### [x] Step: CLI Framework with Stub Commands
<!-- chat-id: 517b123e-ade9-4d60-afd8-b6d5d7c8d22b -->

Set up Typer CLI with all command stubs:

1. Create `src/mindmovie/cli/ui/console.py`:
   - Rich console singleton
   - Helper methods for styled output
2. Create `src/mindmovie/cli/ui/progress.py`:
   - Progress bar and spinner wrappers
3. Create `src/mindmovie/cli/ui/prompts.py`:
   - User input prompts
   - Cost confirmation dialog
4. Create `src/mindmovie/cli/app.py`:
   - Main Typer app with callback
5. Create command stubs in `src/mindmovie/cli/commands/`:
   - `generate.py` - placeholder with options
   - `questionnaire.py` - placeholder
   - `render.py` - placeholder
   - `compile.py` - placeholder
   - `config.py` - show current config
   - `clean.py` - clear build directory
6. Add integration tests in `tests/integration/test_cli_commands.py`:
   - Test `--help` for all commands
   - Test `config` shows settings
   - Test `clean` clears build dir

**Verification:**
- `mindmovie --help` works
- `mindmovie config` displays configuration
- `mindmovie clean` clears build directory
- `pytest tests/integration/test_cli_commands.py -v` passes

---

## Phase 2: Questionnaire & Scene Generation

### [x] Step: Anthropic API Client
<!-- chat-id: 6d256e3b-7d34-4aa4-b67a-aef2d150611f -->

Implement Claude API client with retry logic:

1. Create `src/mindmovie/api/base.py`:
   - `LLMClientProtocol` protocol definition
   - `VideoGeneratorProtocol` protocol definition
   - ~~`TTSGeneratorProtocol` protocol definition~~ (removed)
2. Create `src/mindmovie/api/anthropic_client.py`:
   - `AnthropicClient` class implementing `LLMClientProtocol`
   - `chat()` method for conversational turns
   - `generate_structured()` method for JSON schema output
   - Tenacity retry decorator with exponential backoff
3. Create `src/mindmovie/api/__init__.py` with exports
4. Add unit tests in `tests/unit/test_anthropic_client.py`:
   - Test with mocked responses
   - Test retry behavior
   - Test structured output parsing
5. Add fixtures in `tests/fixtures/sample_llm_responses.json`

**Verification:**
- `pytest tests/unit/test_anthropic_client.py -v` passes
- `ruff check src/mindmovie/api/`

### [x] Step: Questionnaire Engine
<!-- chat-id: 1a89993f-b0cb-431e-8074-e99f4d382d49 -->

Implement conversational goal extraction:

1. Create `src/mindmovie/core/questionnaire.py`:
   - System prompt for life vision coach
   - `QuestionnaireEngine` class
   - Interactive conversation loop
   - `[QUESTIONNAIRE_COMPLETE]` marker detection
   - Goal extraction from completion response
2. Create `src/mindmovie/core/__init__.py` with exports
3. Update `src/mindmovie/cli/commands/questionnaire.py`:
   - Implement full questionnaire command
   - Save extracted goals to state
4. Add unit tests in `tests/unit/test_questionnaire.py`:
   - Test conversation flow with mocked LLM
   - Test completion detection
   - Test goal parsing
5. Add integration test with mocked Claude responses

**Verification:**
- `pytest tests/unit/test_questionnaire.py -v` passes
- Manual test: `mindmovie questionnaire` runs interactive session

### [x] Step: Scene Generator
<!-- chat-id: f57f1e8f-df8f-4c4b-ae4d-4b4b1008a183 -->

Implement goals-to-scenes transformation:

1. Create `src/mindmovie/core/scene_generator.py`:
   - Scene generation system prompt
   - `SceneGenerator` class
   - Structured output with `MindMovieSpec` schema
   - Video prompt engineering (subject + action + camera + style)
2. Create `src/mindmovie/core/cost_estimator.py`:
   - `CostEstimator` class
   - Methods for video and total cost calculation
   - Time estimation based on scene count
3. Add unit tests in `tests/unit/test_scene_generator.py`:
   - Test scene generation with mocked LLM
   - Test video prompt format validation
   - Test affirmation rules enforcement
4. Add unit tests in `tests/unit/test_cost_estimator.py`:
   - Test cost calculations for different configurations
5. Add fixtures: `tests/fixtures/sample_goals.json`, `tests/fixtures/sample_scenes.json`

**Verification:**
- `pytest tests/unit/test_scene_generator.py tests/unit/test_cost_estimator.py -v` passes
- Scene generation produces valid `MindMovieSpec` from sample goals

---

## Phase 3: Asset Generation

### [x] Step: Veo Video Client
<!-- chat-id: b5aa49fa-8213-4fc7-811b-f2536d3b91e2 -->

Implement Google Veo API client:

1. Create `src/mindmovie/api/veo_client.py`:
   - `VeoClient` class implementing `VideoGeneratorProtocol`
   - `generate_video()` async method with polling
   - Cost calculation per model variant
   - Tenacity retry with exponential backoff
   - Configurable model, resolution, aspect ratio
2. Add unit tests in `tests/unit/test_veo_client.py`:
   - Test with mocked google-genai responses
   - Test polling behavior
   - Test retry on failure
   - Test cost estimation

**Verification:**
- `pytest tests/unit/test_veo_client.py -v` passes
- `ruff check src/mindmovie/api/veo_client.py`

### [x] Step: TTS Clients → Removed
<!-- chat-id: 64dfbe2a-e5d4-4965-b6d1-8358bf049655 -->

**Removed:** TTS/voiceover functionality was removed from the project. Veo generates
its own audio natively, so no separate TTS clients are needed. All TTS references,
`voiceover_text` fields, `TTSSettings`, `TTSGeneratorProtocol`, TTS pricing/cost
estimation, and related tests/fixtures were purged from the codebase. The `openai`
dependency was also removed from `pyproject.toml`.

### [x] Step: Asset Generator Orchestrator
<!-- chat-id: 046ade02-1b79-4dd9-ac6d-6eb20344e6f9 -->

Implement parallel asset generation with progress tracking:

1. Create `src/mindmovie/assets/video_generator.py`:
   - Wrapper for video generation with state updates
2. Create `src/mindmovie/assets/generator.py`:
   - `AssetGenerator` class
   - Semaphore-based concurrency control
   - `generate_all()` method orchestrating video generation
   - Progress tracking with Rich progress bars
   - Per-asset state persistence
4. Create `src/mindmovie/assets/__init__.py` with exports
5. Update `src/mindmovie/cli/commands/render.py`:
   - Implement render command
   - Load scenes from state
   - Generate all assets
   - Display progress
6. Add integration tests in `tests/integration/test_asset_generator.py`:
   - Test with mocked API clients
   - Test progress tracking
   - Test resume capability

**Verification:**
- `pytest tests/integration/test_asset_generator.py -v` passes
- `mindmovie render` generates assets from saved scenes (with mocked APIs)

---

## Phase 4: Video Composition

### [x] Step: Video Composer Core
<!-- chat-id: 0d851750-4e5a-4561-8ee4-efb21c5094a0 -->

Implement MoviePy-based video composition:

1. Create `src/mindmovie/video/text_overlay.py`:
   - Text rendering utilities
   - Font handling
   - Shadow/stroke effects
2. Create `src/mindmovie/video/effects.py`:
   - Fade in/out transitions
   - Crossfade between clips
3. Create `src/mindmovie/video/composer.py`:
   - `VideoComposer` class
   - `_create_title_card()` method
   - `_create_closing_card()` method
   - `_create_scene_clip()` with text overlay
   - `compose()` method assembling final video
   - Audio mixing (video audio + background music)
4. Create `src/mindmovie/video/__init__.py` with exports
5. Add sample test assets in `tests/fixtures/`:
   - Small sample video clip
6. Add integration tests in `tests/integration/test_composer.py`:
   - Test title card generation
   - Test scene composition with sample assets
   - Test audio mixing

**Verification:**
- `pytest tests/integration/test_composer.py -v` passes
- Composer produces valid MP4 from sample assets

### [x] Step: Compile Command
<!-- chat-id: 6015db84-9edd-4388-a2b2-a9df155d5242 -->

Implement the compile CLI command:

1. Update `src/mindmovie/cli/commands/compile.py`:
   - Load scenes and assets from state
   - Validate all required assets exist
   - Run composer
   - Display progress
   - Output final video path
2. Add integration test for compile command

**Verification:**
- `mindmovie compile` produces MP4 from generated assets
- `pytest tests/integration/test_cli_commands.py::test_compile -v` passes

---

## Phase 5: Integration & Polish

### [x] Step: Pipeline Orchestrator
<!-- chat-id: e2741f51-5f42-4a53-bd87-45f611fd69a1 -->

Implement full pipeline orchestration:

1. Create `src/mindmovie/core/pipeline.py`:
   - `PipelineOrchestrator` class
   - Stage-by-stage execution with state transitions
   - Resume capability from any checkpoint
   - Error handling with state preservation
   - Keyboard interrupt handling
   - Cost estimation before generation
2. Update `src/mindmovie/cli/commands/generate.py`:
   - Implement full generate command
   - API key validation
   - Cost confirmation prompt
   - Resume prompt
   - Full pipeline execution
3. Add end-to-end integration tests in `tests/integration/test_pipeline.py`:
   - Test full pipeline with mocked APIs
   - Test resume from each stage
   - Test interrupt handling

**Verification:**
- `mindmovie generate` runs full pipeline
- `pytest tests/integration/test_pipeline.py -v` passes

### [x] Step: Error Handling and User Experience
<!-- chat-id: 470b3ead-274a-4334-a8a3-12bebbd5dc4f -->

Polish error handling and user messaging:

1. Review all CLI commands for consistent error handling:
   - Clear error messages with actionable guidance
   - API key missing prompts
   - Network error handling
   - Invalid state recovery
2. Add setup wizard for first-run experience:
   - Detect missing API keys
   - Guide user through configuration
3. Ensure graceful Ctrl+C handling throughout
4. Add `--dry-run` support to generate command
5. Add comprehensive `--help` text for all commands and options
6. Update `README.md` with:
   - Installation instructions
   - Quick start guide
   - Configuration reference
   - Troubleshooting section

**Verification:**
- All commands have helpful `--help` output
- Missing API keys show clear instructions
- Ctrl+C saves state at any point

### [x] Step: Final Verification and Documentation
<!-- chat-id: 80b09ea7-a675-49be-bf6e-2be0637f76dc -->

Complete final verification:

1. Run full linting suite: `ruff check src/ tests/`
2. Run type checking: `mypy src/`
3. Run all tests: `pytest tests/ -v`
4. Manual end-to-end test with real APIs (optional, document in test notes)
5. Create `CLAUDE.md` with:
   - Project overview for AI assistants
   - Key commands
   - Architecture summary
6. Final code review for consistency

**Verification:**
- `ruff check src/ tests/` passes
- `mypy src/` passes (or has documented exceptions)
- `pytest tests/ -v` all tests pass
- Manual verification checklist from spec section 10.4 completed
