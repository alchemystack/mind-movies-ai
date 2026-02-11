# Technical Specification: Mind Movie Generator CLI

## 1. Technical Context

### 1.1 Language & Runtime
- **Language**: Python 3.11+ (recommended for improved async performance and type hints)
- **Package Manager**: pip with pyproject.toml (PEP 621 compliant)
- **Virtual Environment**: venv or uv for dependency isolation

### 1.2 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `typer` | ^0.9.0 | CLI framework with type hints |
| `rich` | ^13.0 | Terminal UI (progress, panels, colors) |
| `pydantic` | ^2.0 | Configuration & data validation |
| `pydantic-settings` | ^2.0 | Settings management with env vars |
| `anthropic` | ^0.40 | Claude API client |
| `google-genai` | ^1.0 | Gemini/Veo API client |
| `openai` | ^1.0 | TTS API client |
| `moviepy` | ^2.2 | Video composition |
| `tenacity` | ^8.0 | Retry with exponential backoff |
| `pyyaml` | ^6.0 | YAML config parsing |
| `python-dotenv` | ^1.0 | Environment variable loading |

### 1.3 System Dependencies
- **FFmpeg** >= 5.0 (video encoding/decoding)
- **ImageMagick** >= 7.0 (text rendering for MoviePy)

### 1.4 Development Dependencies
| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `pytest-asyncio` | Async test support |
| `pytest-mock` | Mocking utilities |
| `ruff` | Linting and formatting |
| `mypy` | Type checking |

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Typer)                          │
│  mindmovie generate | questionnaire | render | compile | config    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Pipeline Orchestrator                          │
│              Coordinates stages, manages state, handles errors      │
└─────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Questionnaire │ │    Scene     │ │    Asset     │ │   Video      │
│   Engine     │ │  Generator   │ │  Generator   │ │  Composer    │
│              │ │              │ │              │ │              │
│ Claude API   │ │ Claude API   │ │ Veo + TTS    │ │   MoviePy    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
             │  Veo Client  │    │  TTS Client  │    │ Music Client │
             │  (Video)     │    │  (Voiceover) │    │  (optional)  │
             └──────────────┘    └──────────────┘    └──────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        State Manager                                │
│              Persists progress, enables resume, tracks assets       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Config Manager (Pydantic)                       │
│              config.yaml + .env + CLI overrides                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Design Principles

1. **Resumable Pipeline**: Every stage persists its output before proceeding. Failures at any point can resume from the last successful checkpoint.

2. **Provider Abstraction**: API clients implement a common interface, enabling future swaps (e.g., Runway instead of Veo).

3. **Async-First Generation**: Video and audio generation use async I/O with controlled concurrency for optimal throughput within rate limits.

4. **Graceful Degradation**: Handle API failures, rate limits, and interrupts without data loss.

5. **User-Centric Output**: Rich terminal UI provides clear feedback for non-technical users.

---

## 3. Source Code Structure

```
mindmovie/
├── pyproject.toml              # Project metadata & dependencies
├── README.md                   # User documentation
├── .env.example                # Example environment variables
├── config.example.yaml         # Example configuration file
│
├── src/
│   └── mindmovie/
│       ├── __init__.py         # Package version
│       ├── __main__.py         # Entry point: python -m mindmovie
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py          # Typer app definition
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── generate.py     # Full pipeline command
│       │   │   ├── questionnaire.py# Questionnaire-only command
│       │   │   ├── render.py       # Render from saved goals
│       │   │   ├── compile.py      # Compile from assets
│       │   │   ├── config.py       # Config management
│       │   │   └── clean.py        # Clean build artifacts
│       │   └── ui/
│       │       ├── __init__.py
│       │       ├── console.py      # Rich console singleton
│       │       ├── progress.py     # Progress bars & spinners
│       │       └── prompts.py      # User prompts & confirmations
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── pipeline.py         # Pipeline orchestrator
│       │   ├── questionnaire.py    # Conversational goal extraction
│       │   ├── scene_generator.py  # Goals → Scenes conversion
│       │   └── cost_estimator.py   # Cost calculations
│       │
│       ├── assets/
│       │   ├── __init__.py
│       │   ├── generator.py        # Asset generation orchestrator
│       │   ├── video_generator.py  # Veo video generation
│       │   ├── voiceover_generator.py  # TTS generation
│       │   └── music_generator.py  # Optional music generation
│       │
│       ├── video/
│       │   ├── __init__.py
│       │   ├── composer.py         # Final video assembly
│       │   ├── effects.py          # Transitions, fades
│       │   └── text_overlay.py     # Affirmation text rendering
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── base.py             # Base client protocol
│       │   ├── anthropic_client.py # Claude API wrapper
│       │   ├── veo_client.py       # Google Veo wrapper
│       │   ├── openai_tts_client.py# OpenAI TTS wrapper
│       │   └── google_tts_client.py# Google Cloud TTS wrapper
│       │
│       ├── state/
│       │   ├── __init__.py
│       │   ├── manager.py          # State persistence
│       │   └── models.py           # State data models
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py         # Pydantic settings
│       │   └── loader.py           # Config file loading
│       │
│       └── models/
│           ├── __init__.py
│           ├── goals.py            # Goal & category models
│           ├── scenes.py           # Scene & affirmation models
│           └── movie.py            # Mind movie specification
│
└── tests/
    ├── conftest.py                 # Pytest fixtures
    ├── unit/
    │   ├── test_questionnaire.py
    │   ├── test_scene_generator.py
    │   ├── test_cost_estimator.py
    │   ├── test_composer.py
    │   └── test_state_manager.py
    ├── integration/
    │   ├── test_cli_commands.py
    │   ├── test_pipeline.py
    │   └── test_api_clients.py
    └── fixtures/
        ├── sample_goals.json
        ├── sample_scenes.json
        └── sample_config.yaml
```

---

## 4. Data Models

### 4.1 Configuration Models (`config/settings.py`)

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class APISettings(BaseSettings):
    """API key configuration loaded from environment."""
    anthropic_api_key: SecretStr = Field(..., alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr = Field(..., alias="GEMINI_API_KEY")
    openai_api_key: SecretStr | None = Field(None, alias="OPENAI_API_KEY")
    google_cloud_project: str | None = Field(None, alias="GOOGLE_CLOUD_PROJECT")

class VideoSettings(BaseSettings):
    """Video generation settings."""
    model: str = "veo-3.1-fast-generate-preview"
    resolution: str = "1080p"
    aspect_ratio: str = "16:9"
    generate_audio: bool = True  # Use Veo's native audio
    max_concurrent: int = 5
    max_retries: int = 3

class TTSSettings(BaseSettings):
    """Text-to-speech settings."""
    provider: str = "openai"  # openai | google
    model: str = "tts-1-hd"
    voice: str = "nova"
    speed: float = 0.9

class MovieSettings(BaseSettings):
    """Mind movie structure settings."""
    scene_duration: int = 8
    num_scenes: int = 12
    title_duration: int = 5
    closing_duration: int = 5
    crossfade_duration: float = 0.5
    fps: int = 24

class Settings(BaseSettings):
    """Root settings aggregating all configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore"
    )

    api: APISettings = Field(default_factory=APISettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    movie: MovieSettings = Field(default_factory=MovieSettings)
    build_dir: str = "build"
    output_path: str = "mind_movie.mp4"
```

### 4.2 Goal Models (`models/goals.py`)

```python
from enum import Enum
from pydantic import BaseModel, Field

class LifeCategory(str, Enum):
    HEALTH = "health"
    WEALTH = "wealth"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    GROWTH = "growth"
    LIFESTYLE = "lifestyle"

class CategoryGoal(BaseModel):
    """Extracted goal for a single life category."""
    category: LifeCategory
    vision: str = Field(..., description="User's described vision")
    visual_details: str = Field(..., description="What it looks like")
    actions: str = Field(..., description="What user is doing")
    emotions: str = Field(..., description="How it feels")
    skipped: bool = False

class ExtractedGoals(BaseModel):
    """Complete goals extracted from questionnaire."""
    title: str = Field(default="My Vision", description="Custom title if provided")
    categories: list[CategoryGoal]
    conversation_id: str = Field(..., description="ID for resume tracking")
```

### 4.3 Scene Models (`models/scenes.py`)

```python
from pydantic import BaseModel, Field, field_validator

class Scene(BaseModel):
    """A single scene in the mind movie."""
    index: int = Field(..., ge=0)
    category: LifeCategory
    affirmation: str = Field(..., min_length=5, max_length=100)
    video_prompt: str = Field(..., min_length=50)
    voiceover_text: str
    mood: str = Field(..., description="Scene mood: warm, energetic, peaceful, etc.")

    @field_validator("affirmation")
    @classmethod
    def validate_affirmation(cls, v: str) -> str:
        """Ensure affirmation follows proper format."""
        if not any(v.lower().startswith(p) for p in ["i am", "i have", "i feel", "i live"]):
            raise ValueError("Affirmation must start with 'I am/have/feel/live...'")
        return v

class MindMovieSpec(BaseModel):
    """Complete specification for a mind movie."""
    title: str
    scenes: list[Scene] = Field(..., min_length=10, max_length=15)
    music_mood: str = Field(..., description="Overall mood for background music")
    closing_affirmation: str = Field(default="I Am Grateful For My Beautiful Life")

    def total_duration(self, scene_duration: int = 8,
                       title_duration: int = 5,
                       closing_duration: int = 5) -> int:
        """Calculate total video duration in seconds."""
        return title_duration + (len(self.scenes) * scene_duration) + closing_duration
```

### 4.4 State Models (`state/models.py`)

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class PipelineStage(str, Enum):
    QUESTIONNAIRE = "questionnaire"
    SCENE_GENERATION = "scene_generation"
    VIDEO_GENERATION = "video_generation"
    VOICEOVER_GENERATION = "voiceover_generation"
    COMPOSITION = "composition"
    COMPLETE = "complete"

class AssetStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"

class SceneAsset(BaseModel):
    """Tracking for a single scene's generated assets."""
    scene_index: int
    video_status: AssetStatus = AssetStatus.PENDING
    video_path: str | None = None
    voiceover_status: AssetStatus = AssetStatus.PENDING
    voiceover_path: str | None = None
    error_message: str | None = None

class PipelineState(BaseModel):
    """Complete pipeline state for resume capability."""
    id: str = Field(..., description="Unique pipeline run ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    current_stage: PipelineStage = PipelineStage.QUESTIONNAIRE

    # Stage outputs
    goals_path: str | None = None
    scenes_path: str | None = None
    music_path: str | None = None
    output_path: str | None = None

    # Asset tracking
    scene_assets: list[SceneAsset] = Field(default_factory=list)

    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float = 0.0

    def is_resumable(self) -> bool:
        """Check if pipeline can be resumed."""
        return self.current_stage != PipelineStage.COMPLETE

    def pending_videos(self) -> list[int]:
        """Get indices of scenes needing video generation."""
        return [a.scene_index for a in self.scene_assets
                if a.video_status in (AssetStatus.PENDING, AssetStatus.FAILED)]

    def pending_voiceovers(self) -> list[int]:
        """Get indices of scenes needing voiceover generation."""
        return [a.scene_index for a in self.scene_assets
                if a.voiceover_status in (AssetStatus.PENDING, AssetStatus.FAILED)]
```

---

## 5. API Client Interfaces

### 5.1 Base Protocol (`api/base.py`)

```python
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class VideoGeneratorProtocol(Protocol):
    """Protocol for video generation clients."""

    async def generate_video(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 8,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True
    ) -> Path:
        """Generate a video clip from a text prompt."""
        ...

    def estimate_cost(self, duration: int, with_audio: bool) -> float:
        """Estimate cost for generating a video of given duration."""
        ...

@runtime_checkable
class TTSGeneratorProtocol(Protocol):
    """Protocol for text-to-speech clients."""

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice: str = "nova",
        speed: float = 1.0
    ) -> Path:
        """Generate speech audio from text."""
        ...

    def estimate_cost(self, text: str) -> float:
        """Estimate cost for generating speech."""
        ...

@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM chat clients."""

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> str:
        """Send chat messages and get response."""
        ...

    async def generate_structured(
        self,
        messages: list[dict],
        schema: type,
        system_prompt: str | None = None
    ) -> dict:
        """Generate structured JSON output matching schema."""
        ...
```

### 5.2 Veo Client (`api/veo_client.py`)

```python
import asyncio
from pathlib import Path
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

class VeoClient:
    """Google Veo video generation client."""

    # Cost per second by model
    COSTS = {
        "veo-3.1-fast-generate-preview": {"with_audio": 0.15, "no_audio": 0.10},
        "veo-3.1-generate-preview": {"with_audio": 0.40, "no_audio": 0.30},
    }

    def __init__(self, api_key: str, model: str = "veo-3.1-fast-generate-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def generate_video(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 8,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True
    ) -> Path:
        """Generate video clip using Veo."""
        operation = self.client.models.generate_videos(
            model=self.model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                generate_audio=generate_audio,
                person_generation="allow_adult",
                number_of_videos=1,
            ),
        )

        # Poll for completion
        while not operation.done:
            await asyncio.sleep(10)
            operation = self.client.operations.get(operation)

        if not operation.response.generated_videos:
            raise RuntimeError("Video generation failed: no videos returned")

        video = operation.response.generated_videos[0]
        video.video.save(str(output_path))
        return output_path

    def estimate_cost(self, duration: int, with_audio: bool = True) -> float:
        """Calculate estimated cost for video generation."""
        cost_key = "with_audio" if with_audio else "no_audio"
        rate = self.COSTS.get(self.model, self.COSTS["veo-3.1-fast-generate-preview"])
        return duration * rate[cost_key]
```

### 5.3 OpenAI TTS Client (`api/openai_tts_client.py`)

```python
from pathlib import Path
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAITTSClient:
    """OpenAI Text-to-Speech client."""

    # Cost per 1M characters
    COST_PER_MILLION_CHARS = {
        "tts-1": 15.0,
        "tts-1-hd": 30.0,
    }

    def __init__(self, api_key: str, model: str = "tts-1-hd"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice: str = "nova",
        speed: float = 1.0
    ) -> Path:
        """Generate speech audio from text."""
        response = await self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            speed=speed,
            response_format="mp3"
        )

        response.stream_to_file(str(output_path))
        return output_path

    def estimate_cost(self, text: str) -> float:
        """Calculate estimated cost for TTS generation."""
        char_count = len(text)
        rate = self.COST_PER_MILLION_CHARS.get(self.model, 30.0)
        return (char_count / 1_000_000) * rate
```

---

## 6. Core Components

### 6.1 Pipeline Orchestrator (`core/pipeline.py`)

The pipeline orchestrator coordinates all stages, manages state persistence, and handles interrupts:

```python
class PipelineOrchestrator:
    """Orchestrates the complete mind movie generation pipeline."""

    def __init__(
        self,
        settings: Settings,
        state_manager: StateManager,
        console: Console
    ):
        self.settings = settings
        self.state = state_manager
        self.console = console

        # Initialize components
        self.questionnaire = QuestionnaireEngine(...)
        self.scene_generator = SceneGenerator(...)
        self.asset_generator = AssetGenerator(...)
        self.composer = VideoComposer(...)

    async def run(self, resume: bool = True) -> Path:
        """Execute the complete pipeline with resume support."""

        # Check for existing state
        if resume and self.state.exists():
            if not self.console.confirm_resume():
                self.state.clear()

        pipeline_state = self.state.load_or_create()

        try:
            # Stage 1: Questionnaire
            if pipeline_state.current_stage == PipelineStage.QUESTIONNAIRE:
                goals = await self.questionnaire.run()
                pipeline_state = self.state.complete_questionnaire(goals)

            # Stage 2: Scene Generation
            if pipeline_state.current_stage == PipelineStage.SCENE_GENERATION:
                scenes = await self.scene_generator.generate(
                    self.state.load_goals()
                )
                pipeline_state = self.state.complete_scene_generation(scenes)

            # Stage 3: Asset Generation (video + voiceover)
            if pipeline_state.current_stage == PipelineStage.VIDEO_GENERATION:
                await self.asset_generator.generate_all(
                    self.state.load_scenes(),
                    pipeline_state
                )
                pipeline_state = self.state.complete_asset_generation()

            # Stage 4: Composition
            if pipeline_state.current_stage == PipelineStage.COMPOSITION:
                output = await self.composer.compose(
                    self.state.load_scenes(),
                    pipeline_state.scene_assets
                )
                pipeline_state = self.state.complete_composition(output)

            return Path(pipeline_state.output_path)

        except KeyboardInterrupt:
            self.console.print("[yellow]Interrupted. Progress saved.[/yellow]")
            self.state.save(pipeline_state)
            raise
        except Exception as e:
            self.state.save(pipeline_state)
            raise
```

### 6.2 Questionnaire Engine (`core/questionnaire.py`)

Multi-turn conversational goal extraction using Claude:

```python
SYSTEM_PROMPT = """You are a warm, empathetic life vision coach conducting a mind movie questionnaire.

ROLE: Guide users to articulate vivid, specific visions for their ideal life.

WORKFLOW:
1. Greet warmly. Explain you'll explore 6 life areas together.
2. For each area (Health, Wealth, Career, Relationships, Growth, Lifestyle):
   a. Ask ONE open-ended question about their vision
   b. Based on response, ask 1-2 follow-ups to extract VISUAL DETAILS:
      - What does it LOOK like? (setting, environment, colors)
      - What are you DOING? (specific actions, who's with you)
      - How does it FEEL? (emotions, sensations)
   c. Confirm understanding before moving to next area
3. Allow skipping areas ("skip" or "next")
4. After all areas, summarize what you heard and ask for confirmation

BEHAVIOR RULES:
- Ask ONE question at a time
- Be encouraging and supportive
- Never judge or question the feasibility of goals
- Probe for concrete, filmable details (not abstractions)
- Keep responses under 3 sentences

When user says "done" or you've covered all categories, respond with exactly:
[QUESTIONNAIRE_COMPLETE]
followed by a JSON summary of extracted goals."""

class QuestionnaireEngine:
    """Conversational goal extraction using Claude."""

    def __init__(self, anthropic_client: AnthropicClient, console: Console):
        self.client = anthropic_client
        self.console = console
        self.messages: list[dict] = []

    async def run(self) -> ExtractedGoals:
        """Run interactive questionnaire and return extracted goals."""
        self.console.print_welcome()

        # Initial message from Claude
        response = await self.client.chat(
            messages=[],
            system_prompt=SYSTEM_PROMPT
        )
        self.console.print_assistant(response)
        self.messages.append({"role": "assistant", "content": response})

        # Conversation loop
        while True:
            user_input = self.console.prompt_user()
            self.messages.append({"role": "user", "content": user_input})

            response = await self.client.chat(
                messages=self.messages,
                system_prompt=SYSTEM_PROMPT
            )

            if "[QUESTIONNAIRE_COMPLETE]" in response:
                # Extract JSON from response
                goals = self._parse_completion(response)
                return goals

            self.console.print_assistant(response)
            self.messages.append({"role": "assistant", "content": response})

    def _parse_completion(self, response: str) -> ExtractedGoals:
        """Parse the completion marker and extract goals JSON."""
        # Implementation extracts JSON after [QUESTIONNAIRE_COMPLETE]
        ...
```

### 6.3 Scene Generator (`core/scene_generator.py`)

Transforms extracted goals into structured scene specifications:

```python
GENERATION_PROMPT = """Transform the user's life vision goals into a mind movie specification.

Create 10-15 scenes, distributing them across the categories provided. Each scene must have:

1. affirmation: First person, present tense, positive, emotionally charged, 5-12 words
   Examples: "I am radiantly healthy and full of energy", "I earn $15,000 monthly doing work I love"

2. video_prompt: Cinematic prompt following this structure:
   Subject + Action + Scene + Camera Movement + Style/Mood + Lighting
   Example: "A confident person in elegant clothing walks through a sunlit modern penthouse
   with floor-to-ceiling windows overlooking a city skyline. They smile and turn toward the
   panoramic view. Slow dolly forward. Warm golden hour light, cinematic color grading,
   shallow depth of field, aspirational luxury aesthetic."

3. voiceover_text: The affirmation text, possibly with slight variations for natural speech

4. mood: One of: warm, energetic, peaceful, romantic, confident, joyful, serene

AFFIRMATION RULES:
- Must start with "I am", "I have", "I feel", or "I live"
- Present tense only (as if already true)
- No negative words (no "not", "don't", "never")
- Emotionally charged and specific
- 5-12 words

VIDEO PROMPT RULES:
- Describe motion, not static scenes
- Include specific camera movements (dolly, pan, tracking shot)
- Specify lighting (golden hour, soft natural light, warm glow)
- Include style keywords (cinematic, aspirational, film grain)
- Present tense throughout"""

class SceneGenerator:
    """Generates structured scene specifications from goals."""

    def __init__(self, anthropic_client: AnthropicClient):
        self.client = anthropic_client

    async def generate(self, goals: ExtractedGoals) -> MindMovieSpec:
        """Generate complete scene specifications from goals."""
        result = await self.client.generate_structured(
            messages=[{"role": "user", "content": f"Goals:\n{goals.model_dump_json()}"}],
            schema=MindMovieSpec,
            system_prompt=GENERATION_PROMPT
        )
        return MindMovieSpec.model_validate(result)
```

### 6.4 Asset Generator (`assets/generator.py`)

Orchestrates parallel video and voiceover generation with rate limiting:

```python
import asyncio
from asyncio import Semaphore

class AssetGenerator:
    """Orchestrates video and voiceover generation."""

    def __init__(
        self,
        veo_client: VeoClient,
        tts_client: TTSGeneratorProtocol,
        settings: Settings,
        state_manager: StateManager,
        console: Console
    ):
        self.veo = veo_client
        self.tts = tts_client
        self.settings = settings
        self.state = state_manager
        self.console = console

        # Concurrency control
        self.video_semaphore = Semaphore(settings.video.max_concurrent)

    async def generate_all(
        self,
        scenes: MindMovieSpec,
        state: PipelineState
    ) -> None:
        """Generate all video and voiceover assets."""
        build_dir = Path(self.settings.build_dir)

        # Generate voiceovers first (fast, cheap)
        self.console.print_stage("Generating voiceovers...")
        await self._generate_voiceovers(scenes, state, build_dir)

        # Generate videos (slow, expensive)
        self.console.print_stage("Generating videos...")
        await self._generate_videos(scenes, state, build_dir)

    async def _generate_videos(
        self,
        scenes: MindMovieSpec,
        state: PipelineState,
        build_dir: Path
    ) -> None:
        """Generate all pending video clips with progress tracking."""
        pending = state.pending_videos()

        with self.console.progress_bar("Videos", len(pending)) as progress:
            tasks = [
                self._generate_single_video(
                    scenes.scenes[i],
                    state.scene_assets[i],
                    build_dir,
                    progress
                )
                for i in pending
            ]
            await asyncio.gather(*tasks)

    async def _generate_single_video(
        self,
        scene: Scene,
        asset: SceneAsset,
        build_dir: Path,
        progress
    ) -> None:
        """Generate a single video clip with semaphore rate limiting."""
        async with self.video_semaphore:
            output_path = build_dir / f"scene_{scene.index:02d}.mp4"

            try:
                asset.video_status = AssetStatus.GENERATING
                self.state.save_asset(asset)

                await self.veo.generate_video(
                    prompt=scene.video_prompt,
                    output_path=output_path,
                    duration=self.settings.movie.scene_duration,
                    generate_audio=self.settings.video.generate_audio
                )

                asset.video_status = AssetStatus.COMPLETE
                asset.video_path = str(output_path)

            except Exception as e:
                asset.video_status = AssetStatus.FAILED
                asset.error_message = str(e)

            self.state.save_asset(asset)
            progress.advance()
```

### 6.5 Video Composer (`video/composer.py`)

Final assembly using MoviePy:

```python
from moviepy import (
    VideoFileClip, TextClip, ColorClip, CompositeVideoClip,
    CompositeAudioClip, AudioFileClip, concatenate_videoclips, vfx
)

class VideoComposer:
    """Assembles final mind movie from generated assets."""

    def __init__(self, settings: MovieSettings):
        self.settings = settings

    async def compose(
        self,
        spec: MindMovieSpec,
        assets: list[SceneAsset]
    ) -> Path:
        """Compose final mind movie video."""
        clips = []

        # Title card
        title_clip = self._create_title_card(spec.title)
        clips.append(title_clip)

        # Scene clips with overlays
        for scene, asset in zip(spec.scenes, assets):
            scene_clip = self._create_scene_clip(scene, asset)
            clips.append(scene_clip)

        # Closing card
        closing_clip = self._create_closing_card(spec.closing_affirmation)
        clips.append(closing_clip)

        # Concatenate with crossfades
        final = concatenate_videoclips(clips, method="compose")

        # Export
        output_path = Path(self.settings.output_path)
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=self.settings.fps,
            threads=4,
            preset="medium"
        )

        return output_path

    def _create_scene_clip(self, scene: Scene, asset: SceneAsset) -> CompositeVideoClip:
        """Create a single scene with video, text overlay, and voiceover."""
        # Load video
        video = VideoFileClip(asset.video_path).subclipped(0, self.settings.scene_duration)

        # Create text overlay
        text = TextClip(
            font="Arial.ttf",
            text=scene.affirmation,
            font_size=50,
            color="white",
            stroke_color="black",
            stroke_width=2
        ).with_position(("center", 0.85), relative=True).with_duration(
            self.settings.scene_duration
        )

        # Compose video with text
        composed = CompositeVideoClip([video, text])

        # Add voiceover if video has no audio or we want to mix
        if asset.voiceover_path:
            voiceover = AudioFileClip(asset.voiceover_path)
            if video.audio:
                # Mix voiceover with video audio (video audio reduced)
                video_audio = video.audio.with_volume_scaled(0.3)
                mixed_audio = CompositeAudioClip([video_audio, voiceover])
                composed = composed.with_audio(mixed_audio)
            else:
                composed = composed.with_audio(voiceover)

        # Add transitions
        composed = composed.with_effects([
            vfx.FadeIn(self.settings.crossfade_duration),
            vfx.FadeOut(self.settings.crossfade_duration)
        ])

        return composed

    def _create_title_card(self, title: str) -> CompositeVideoClip:
        """Create title card with fade effects."""
        bg = ColorClip((1920, 1080), color=(0, 0, 0)).with_duration(
            self.settings.title_duration
        )
        text = TextClip(
            font="Arial.ttf",
            text=title,
            font_size=90,
            color="white"
        ).with_position("center").with_duration(self.settings.title_duration)

        composed = CompositeVideoClip([bg, text])
        return composed.with_effects([vfx.FadeIn(1), vfx.FadeOut(1)])

    def _create_closing_card(self, affirmation: str) -> CompositeVideoClip:
        """Create closing gratitude card."""
        bg = ColorClip((1920, 1080), color=(0, 0, 0)).with_duration(
            self.settings.closing_duration
        )
        text = TextClip(
            font="Arial.ttf",
            text=affirmation,
            font_size=60,
            color="gold"
        ).with_position("center").with_duration(self.settings.closing_duration)

        composed = CompositeVideoClip([bg, text])
        return composed.with_effects([vfx.FadeIn(1)])
```

---

## 7. State Management

### 7.1 State Manager (`state/manager.py`)

```python
import json
import uuid
from pathlib import Path
from datetime import datetime

class StateManager:
    """Manages pipeline state for resume capability."""

    STATE_FILE = "pipeline_state.json"
    GOALS_FILE = "goals.json"
    SCENES_FILE = "scenes.json"

    def __init__(self, build_dir: str = "build"):
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(exist_ok=True)

    def exists(self) -> bool:
        """Check if resumable state exists."""
        return (self.build_dir / self.STATE_FILE).exists()

    def load_or_create(self) -> PipelineState:
        """Load existing state or create new."""
        state_path = self.build_dir / self.STATE_FILE
        if state_path.exists():
            data = json.loads(state_path.read_text())
            return PipelineState.model_validate(data)
        return PipelineState(id=str(uuid.uuid4()))

    def save(self, state: PipelineState) -> None:
        """Persist current state to disk."""
        state.updated_at = datetime.now()
        state_path = self.build_dir / self.STATE_FILE
        state_path.write_text(state.model_dump_json(indent=2))

    def save_goals(self, goals: ExtractedGoals) -> Path:
        """Save extracted goals and update state."""
        path = self.build_dir / self.GOALS_FILE
        path.write_text(goals.model_dump_json(indent=2))
        return path

    def load_goals(self) -> ExtractedGoals:
        """Load saved goals."""
        path = self.build_dir / self.GOALS_FILE
        return ExtractedGoals.model_validate_json(path.read_text())

    def save_scenes(self, scenes: MindMovieSpec) -> Path:
        """Save generated scenes and update state."""
        path = self.build_dir / self.SCENES_FILE
        path.write_text(scenes.model_dump_json(indent=2))
        return path

    def load_scenes(self) -> MindMovieSpec:
        """Load saved scenes."""
        path = self.build_dir / self.SCENES_FILE
        return MindMovieSpec.model_validate_json(path.read_text())

    def complete_questionnaire(self, goals: ExtractedGoals) -> PipelineState:
        """Mark questionnaire complete and advance stage."""
        state = self.load_or_create()
        self.save_goals(goals)
        state.goals_path = str(self.build_dir / self.GOALS_FILE)
        state.current_stage = PipelineStage.SCENE_GENERATION
        self.save(state)
        return state

    def clear(self) -> None:
        """Remove all state and generated assets."""
        import shutil
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
```

---

## 8. CLI Commands

### 8.1 Main App (`cli/app.py`)

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="mindmovie",
    help="Generate personalized mind movie visualization videos",
    no_args_is_help=True
)
console = Console()

@app.callback()
def callback():
    """Mind Movie Generator - AI-powered visualization videos."""
    pass

# Import and register commands
from .commands import generate, questionnaire, render, compile, config, clean

app.command()(generate.generate)
app.command()(questionnaire.questionnaire)
app.command()(render.render)
app.command()(compile.compile)
app.command()(config.config)
app.command()(clean.clean)
```

### 8.2 Generate Command (`cli/commands/generate.py`)

```python
import asyncio
import typer
from rich.console import Console
from ..ui.prompts import confirm_cost

console = Console()

def generate(
    output: str = typer.Option("mind_movie.mp4", "--output", "-o", help="Output file path"),
    resume: bool = typer.Option(True, "--resume/--no-resume", help="Resume from saved state"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show cost estimate without generating"),
):
    """Run the complete mind movie generation pipeline."""
    from ...config import load_settings
    from ...core.pipeline import PipelineOrchestrator
    from ...state import StateManager

    settings = load_settings()
    settings.output_path = output

    # Check API keys
    if not settings.api.gemini_api_key:
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
        raise typer.Exit(1)

    state_manager = StateManager(settings.build_dir)
    pipeline = PipelineOrchestrator(settings, state_manager, console)

    # Cost estimate
    estimate = pipeline.estimate_cost()
    console.print(f"\n[bold]Estimated cost:[/bold] ${estimate:.2f}")
    console.print(f"[bold]Estimated time:[/bold] {pipeline.estimate_time()} minutes\n")

    if dry_run:
        raise typer.Exit(0)

    if not confirm_cost(console, estimate):
        raise typer.Exit(0)

    try:
        result = asyncio.run(pipeline.run(resume=resume))
        console.print(f"\n[green]✓ Mind movie created:[/green] {result}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Progress saved. Run again to resume.[/yellow]")
        raise typer.Exit(1)
```

---

## 9. Delivery Phases

### Phase 1: Foundation (Core Infrastructure)
- Project setup with pyproject.toml, dependencies, and directory structure
- Configuration management (Settings, environment loading, config.yaml)
- State management system (StateManager with persistence)
- CLI framework with command structure (empty implementations)
- Unit tests for config and state management

### Phase 2: Questionnaire & Scene Generation
- Claude API client with retry logic
- Questionnaire engine with conversational loop
- Scene generator with structured output
- Cost estimator
- Integration tests with mocked API responses
- CLI commands: `questionnaire`, `config`

### Phase 3: Asset Generation
- Veo API client for video generation
- OpenAI TTS client for voiceover
- Asset generator with parallel execution
- Progress tracking and resume capability
- Integration tests with mocked API responses
- CLI command: `render`

### Phase 4: Video Composition
- MoviePy-based video composer
- Title/closing card generation
- Text overlay rendering
- Audio mixing (voiceover + video audio)
- Transition effects
- Integration tests with sample assets
- CLI command: `compile`

### Phase 5: Integration & Polish
- Full pipeline orchestration
- End-to-end testing
- Error handling and user messaging
- Documentation and setup guide
- CLI command: `generate`

---

## 10. Verification Approach

### 10.1 Testing Strategy

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit | Individual functions, models, utilities | pytest, pytest-mock |
| Integration | Component interactions, API clients | pytest, mocked APIs |
| End-to-End | Full pipeline with real assets | pytest (marked slow) |

### 10.2 Lint & Type Check Commands

```bash
# Linting
ruff check src/ tests/

# Formatting
ruff format src/ tests/

# Type checking
mypy src/

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v --run-slow  # Optional, uses real APIs
```

### 10.3 CI/CD Verification

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy src/
      - run: pytest tests/unit/ tests/integration/ -v
```

### 10.4 Manual Verification Checklist

- [ ] `mindmovie --help` displays command help
- [ ] `mindmovie config` shows current configuration
- [ ] `mindmovie questionnaire` runs interactive conversation
- [ ] `mindmovie render` generates assets from saved goals
- [ ] `mindmovie compile` creates video from assets
- [ ] `mindmovie generate` runs full pipeline
- [ ] `mindmovie clean` removes build artifacts
- [ ] Ctrl+C during generation saves state and can resume
- [ ] Missing API keys show clear error messages
- [ ] Cost estimate matches actual API usage

---

## 11. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Veo API rate limits | Semaphore-based concurrency control, exponential backoff |
| API failures mid-pipeline | Save-after-each-asset architecture, resume from checkpoint |
| High costs surprising users | Mandatory cost confirmation before generation |
| MoviePy text rendering issues | Fallback to PIL-based text overlay if ImageMagick fails |
| Long generation times | Clear progress indicators, time estimates, background generation |
| Invalid affirmations from LLM | Pydantic validation with retry on failure |

---

## 12. Dependencies Summary

### pyproject.toml (Core Dependencies)

```toml
[project]
name = "mindmovie"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "anthropic>=0.40.0",
    "google-genai>=1.0.0",
    "openai>=1.0.0",
    "moviepy>=2.2.0",
    "tenacity>=8.0.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
    "pillow>=10.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]

[project.scripts]
mindmovie = "mindmovie.cli.app:app"
```
