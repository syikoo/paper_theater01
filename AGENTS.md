# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Conversational Drive Navigator - A scenario-based conversational AI application with pluggable display renderers.

**Current Version**: 2.0.0
**Main Entry Point**: `conversation_app.py`
**Python Version**: 3.12+
**UI Framework**: Gradio 6.0+
**LLM**: OpenAI GPT-4o-mini
**Configuration Format**: YAML (prompts/scenario.yaml)

## Build & Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python conversation_app.py
# Or use convenience script:
./run.sh   # Linux/Mac
run.bat    # Windows

# Run tests
uv run python test_scenario.py

# Set custom port
export GRADIO_SERVER_PORT=7861
uv run python conversation_app.py
```

## Architecture

### High-Level Structure

```
conversation_app.py       # Main application entry point
├── renderers/            # Display method abstraction
│   ├── base_renderer.py           # Abstract base class
│   └── paper_theater_renderer.py  # HTML/CSS composition renderer
├── prompts/              # Separated prompt files
│   ├── system_prompt.txt          # Technical instructions (dev-managed)
│   ├── scenario.yaml              # YAML scenario definitions
│   └── data/                      # Mood and background images
├── scenario_manager.py   # Scene/page state management (YAML only)
└── yaml_scenario_loader.py # YAML parser and validator
```

### Key Design Patterns

**1. Renderer Pattern**
- Abstract base class defines display interface
- Concrete renderers implement specific visualization methods
- Programmatic selection: Change one line to switch renderer
- Future-ready for 3D avatars, HTML, etc.

**2. YAML Configuration**
- Hierarchical scenario management
- Scene/page-level prompts
- Natural language transition conditions
- Background image support
- Schema validation

**3. Prompt Separation**
- System prompts: Technical LLM instructions (system_prompt.txt)
- Scenario prompts: Content and behavior (scenario.yaml)
- Dynamic injection of renderer-specific mood descriptions

**4. Scenario Management**
- YAML-based scenario definitions
- Scene → Page hierarchy
- LLM-controlled page transitions
- Mood constraints per page

### Important Implementation Details

**Switching Renderers:**
```python
# In conversation_app.py line ~25
renderer = PaperTheaterRenderer(DEFAULT_PAPER_THEATER_MOODS)
# Future: renderer = Avatar3DRenderer(config)
```

**Mood Names:**
- Remain in Japanese for user customization
- Examples: "基本スタイル", "笑う", "困る", "運転"
- Defined in `prompts/scenario.yaml` configuration section

**File Naming:**
- Source code: English variable names and comments
- User content: Japanese (scenarios, state names)
- Documentation: English (technical), Japanese (user-facing)
