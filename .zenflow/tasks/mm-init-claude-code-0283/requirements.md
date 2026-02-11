# Product Requirements Document: Mind Movie Generator CLI

## Overview

A CLI tool that generates personalized 3-minute visualization videos ("mind movies") by orchestrating an AI-powered pipeline. The tool guides non-technical users through a friendly conversational questionnaire about their life goals, then automatically generates video clips with synchronized audio/music using Google's Veo 3.1, and compiles them into a polished final video.

## Problem Statement

Mind movies are powerful visualization tools popularized by Joe Dispenza and MindMovies.com, but creating them traditionally requires:
- Video editing skills
- Stock footage subscriptions
- Music licensing knowledge
- Hours of manual assembly

This tool automates the entire process, making personalized mind movies accessible to anyone who can answer questions about their goals.

## Target Users

Non-technical individuals interested in:
- Personal development and visualization practices
- Joe Dispenza / Law of Attraction methodologies
- Creating digital vision boards
- Daily meditation and affirmation routines

**Key user characteristic**: Users may not be comfortable with command-line tools, so the CLI must be exceptionally clear, friendly, and guide them through every step.

## Core User Journey

```
1. User runs: mindmovie generate
2. CLI displays welcome message explaining the process
3. CLI asks for API key (or reads from config/env)
4. Conversational questionnaire begins (5-10 minutes)
   - Warm, coach-like AI guides through 6 life areas
   - User types natural language responses
   - AI probes for visual/emotional details
5. CLI shows summary of what will be generated
   - Lists all scenes with affirmations
   - Shows estimated cost and time
   - User confirms or requests changes
6. Generation begins with clear progress display
   - Each scene shows: generating video... done ✓
   - Clips saved immediately after generation
   - Resume capability if interrupted
7. Final compilation with progress bar
8. Output: mind_movie.mp4 ready for daily viewing
```

## Functional Requirements

### FR1: Interactive Questionnaire

| Requirement | Description |
|-------------|-------------|
| FR1.1 | Conversational AI guides user through 6 life categories: Health, Wealth, Career, Relationships, Personal Growth, Lifestyle |
| FR1.2 | One question at a time, warm and encouraging tone |
| FR1.3 | Follow-up questions extract visual details (what it looks like, what user is doing, how it feels) |
| FR1.4 | Allow skipping categories ("skip" or "next") |
| FR1.5 | Summary and confirmation before proceeding |
| FR1.6 | Save questionnaire results to resumable state file |

### FR2: Scene & Affirmation Generation

| Requirement | Description |
|-------------|-------------|
| FR2.1 | Generate 10-15 scenes from questionnaire responses |
| FR2.2 | Each scene has: affirmation text, video prompt, category, mood |
| FR2.3 | Affirmations follow rules: first person, present tense, positive, emotionally charged, 5-12 words |
| FR2.4 | Video prompts include: subject, action, scene, camera movement, style, lighting |
| FR2.5 | Display generated scenes to user for review before video generation |
| FR2.6 | Allow user to regenerate or edit specific scenes |

### FR3: Video Generation (Veo 3.1)

| Requirement | Description |
|-------------|-------------|
| FR3.1 | Use Google Veo 3.1 (or Veo 3.1 Fast for cost savings) |
| FR3.2 | Generate 8-second clips at 1080p, 16:9 aspect ratio |
| FR3.3 | Enable native audio generation (music synchronized with video) |
| FR3.4 | Save each clip immediately upon successful generation |
| FR3.5 | Display real-time progress for each scene |
| FR3.6 | Respect rate limits (~10 requests/minute) |
| FR3.7 | Retry failed generations with exponential backoff |

### FR4: Voiceover Generation

| Requirement | Description |
|-------------|-------------|
| FR4.1 | Generate TTS voiceover for each affirmation |
| FR4.2 | Use calm, meditative voice appropriate for visualization |
| FR4.3 | One audio file per scene for synchronization |
| FR4.4 | Support OpenAI TTS (default) or Google Cloud TTS |

### FR5: Video Composition

| Requirement | Description |
|-------------|-------------|
| FR5.1 | Assemble all clips into single 3-minute MP4 |
| FR5.2 | Add title card (5 seconds) at start |
| FR5.3 | Add closing gratitude card (5 seconds) at end |
| FR5.4 | Overlay affirmation text on each scene (white text, shadow, bottom-centered) |
| FR5.5 | Apply crossfade transitions (0.5-1 second) between scenes |
| FR5.6 | Mix voiceover audio with Veo-generated background audio |
| FR5.7 | Output 1080p MP4 at 24fps |

### FR6: State Management & Resume

| Requirement | Description |
|-------------|-------------|
| FR6.1 | Save state after each pipeline stage to `build/` directory |
| FR6.2 | Detect existing state and offer to resume |
| FR6.3 | State includes: goals.json, scenes.json, individual video/audio files |
| FR6.4 | Never re-generate already-saved assets |
| FR6.5 | Clear state with explicit command (`mindmovie clean`) |

### FR7: Configuration

| Requirement | Description |
|-------------|-------------|
| FR7.1 | Support config file (`config.yaml`) and environment variables |
| FR7.2 | API keys: GEMINI_API_KEY (required), OPENAI_API_KEY (for TTS) |
| FR7.3 | Configurable: scene duration, number of scenes, output path |
| FR7.4 | Show current configuration with `mindmovie config` |
| FR7.5 | First-run setup wizard if no API key configured |

### FR8: CLI User Experience

| Requirement | Description |
|-------------|-------------|
| FR8.1 | Rich terminal output with colors, progress bars, spinners |
| FR8.2 | Clear error messages with actionable guidance |
| FR8.3 | Estimated cost displayed before generation starts |
| FR8.4 | Time estimates for each stage |
| FR8.5 | Confirmation prompts before expensive operations |
| FR8.6 | Keyboard interrupt (Ctrl+C) saves current state gracefully |

## CLI Commands

```
mindmovie generate       # Full pipeline: questionnaire → generate → compile
mindmovie questionnaire  # Run only the questionnaire, save goals
mindmovie render         # Generate videos/audio from saved goals
mindmovie compile        # Assemble final video from generated assets
mindmovie config         # View/edit configuration
mindmovie clean          # Clear build directory and state
mindmovie --help         # Show help
mindmovie --version      # Show version
```

## Non-Functional Requirements

### NFR1: Performance
- Video generation: ~2-6 minutes per clip (API-dependent)
- Full pipeline: 40-100 minutes for 15 scenes
- Parallel generation where rate limits allow

### NFR2: Reliability
- Automatic retry with exponential backoff on API failures
- Graceful handling of rate limits
- No data loss on interruption

### NFR3: Cost Transparency
- Display estimated cost before generation
- Show actual cost after completion
- Default to cost-efficient options (Veo 3.1 Fast)

### NFR4: Usability
- No technical knowledge required
- Clear, jargon-free language
- Friendly, encouraging tone throughout

## Technical Constraints

### Required APIs
- Google Gemini API (for Veo 3.1 video generation)
- Anthropic Claude API (for questionnaire and scene generation)
- OpenAI API (for TTS voiceover) - optional, can use Google TTS

### System Dependencies
- Python 3.9+
- FFmpeg (video processing)
- ImageMagick (text rendering)

### Output Specifications
| Property | Value |
|----------|-------|
| Duration | ~3 minutes (180 seconds) |
| Resolution | 1920x1080 (1080p) |
| Aspect Ratio | 16:9 |
| Frame Rate | 24 fps |
| Format | MP4 (H.264 video, AAC audio) |
| Scenes | 10-15 scenes, 8-12 seconds each |

## Mind Movie Structure

```
[Title Card - 5s]
    "My Vision" or custom title
    Fade in/out

[Scene 1-15 - 8s each]
    Video clip (Veo 3.1 generated with music)
    Affirmation text overlay
    Voiceover narration
    Crossfade transition

[Closing Card - 5s]
    "I Am Grateful For My Beautiful Life"
    Fade in
```

## Affirmation Rules

Per Joe Dispenza / MindMovies methodology:
1. First person ("I am...", "I have...")
2. Present tense (as if already true)
3. Positive framing (no negative words)
4. Emotionally charged
5. Specific where possible
6. 5-12 words per affirmation

**Examples:**
- "I am radiantly healthy and full of energy"
- "I earn $15,000 monthly doing work I love"
- "I am surrounded by loving, supportive relationships"
- "I live in my beautiful oceanfront home"

## Cost Estimates

| Component | Cost (15 scenes) |
|-----------|------------------|
| Claude (questionnaire + scenes) | ~$0.07 |
| Veo 3.1 Fast (120s video with audio) | ~$18.00 |
| OpenAI TTS (voiceover) | ~$0.08 |
| **Total** | **~$18-20** |

*Using Veo 3.1 (non-fast) would cost ~$48 for video generation.*

## Success Criteria

1. Non-technical user can generate a mind movie with zero manual editing
2. Total hands-on time < 15 minutes (questionnaire only)
3. Output quality matches professional MindMovies.com examples
4. No data loss on API failures or interruptions
5. Cost per video < $25

## Out of Scope (for MVP)

- Web interface or GUI
- Multiple video provider backends
- Custom music upload (using Veo's native audio)
- Video preview before final render
- Cloud storage integration
- User accounts or history
- Kaleidoscope/binaural beats intro video

## Assumptions

1. User has valid Google Cloud / Gemini API access with Veo 3.1 enabled
2. User has OpenAI API key for TTS (or will use Google TTS alternative)
3. User has Anthropic API key for Claude
4. User's machine has sufficient disk space for video assets (~500MB per mind movie)
5. User has stable internet connection for API calls
6. Veo 3.1's native audio generation produces suitable meditation/ambient music

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Veo 3.1 native audio quality insufficient | Medium | Fall back to separate music generation or user-provided track |
| API rate limits cause long delays | Low | Implement concurrent generation up to limits, show accurate time estimates |
| Video generation fails mid-pipeline | High | Save-after-each-clip architecture, resume capability |
| High cost surprises users | Medium | Mandatory cost estimate + confirmation before generation |
| Veo 3.1 access restricted | High | Document access requirements clearly in setup guide |

## Future Considerations

- Add Runway/MiniMax as fallback video providers
- Custom music upload option
- Scene-by-scene preview and editing
- Template library for common goal types
- Batch generation from saved goal profiles
- Integration with cloud storage (Google Drive, Dropbox)
