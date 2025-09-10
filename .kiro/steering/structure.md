# Project Structure

## Root Directory Organization

```
davinciauto/
├── minivt_pipeline/          # 🎯 Core Pipeline - Main automation system
├── gui_steps/                # 🖥️  GUI Components - Step-by-step interface
├── .kiro/                    # 📋 Spec-Driven Development
├── docs/                     # 📚 Documentation Suite
├── *.md                      # 📄 Project Documentation
├── *.py                      # 🔧 Utility Scripts (CSV/XML processing)
└── *.js                     # 🌐 Adobe Premiere Pro integration
```

### Directory Purposes
- **`minivt_pipeline/`**: メインの自動化パイプライン（本体システム）
- **`gui_steps/`**: GUIベースの段階的処理インターフェース
- **`.kiro/`**: 仕様駆動開発（specs/steering）
- **`docs/`**: 包括的なドキュメント群
- **Root utilities**: CSVカッター、Premiereスクリプト等

## Core Pipeline Structure (`minivt_pipeline/`)

```
minivt_pipeline/
├── src/
│   ├── pipeline.py           # 🎯 Main Orchestrator
│   ├── resolve_import.py     # 🎬 DaVinci Resolve Integration
│   ├── clients/              # 🔌 External API Clients
│   │   ├── tts_elevenlabs.py # 🎤 ElevenLabs TTS Client
│   │   ├── gpt_client.py     # 🤖 GPT Client (Stub)
│   │   └── stock_search.py   # 🎨 Stock Media Search (Placeholder)
│   └── utils/                # 🛠️ Processing Utilities
│       ├── srt.py           # 📺 Subtitle Generation
│       ├── wrap.py          # 📝 Japanese Text Wrapping
│       └── net.py           # 🌐 Network Utilities
├── data/                    # 📄 Input Scripts
├── output/                  # 📤 Generated Files
│   ├── audio/              # 🎵 Generated Audio Files
│   ├── subtitles/          # 📺 SRT & Plain Text Subtitles
│   └── storyboard/         # 📋 JSON Metadata
├── .venv/                  # 🐍 Python Virtual Environment
├── requirements.txt        # 📦 Python Dependencies
├── .env                   # 🔐 Environment Configuration
└── README.md              # 📖 Pipeline Documentation
```

## GUI Components Structure (`gui_steps/`)

```
gui_steps/
├── common/                  # 🧩 Shared GUI Components
│   ├── gui_base.py         # 🏗️ Base GUI Framework
│   └── data_models.py      # 📊 Data Structures
├── step1_script_editor.py   # ✏️ Script Input Interface
├── step2_tts_generation.py  # 🎤 TTS Generation GUI
├── step2_minimal_test.py    # 🧪 TTS Testing Interface
├── step3_subtitle_timing.py # ⏱️ Subtitle Timing Control
├── step4_davinci_export.py  # 🎬 DaVinci Export Interface
├── integrated_workspace.py  # 🎯 Unified Workspace
├── run_all_steps.py        # 🚀 Automated Pipeline Runner
└── README.md               # 📖 GUI Documentation
```

### GUI Architecture Pattern
- **Common Base**: 共通のGUIフレームワーク（`gui_base.py`）
- **Step-by-Step**: 各処理段階に対応する独立GUI
- **Integrated Workspace**: 全機能統合インターフェース
- **Data Models**: 共通データ構造定義

## Code Organization Patterns

### Functional Separation
```python
# Client Layer Pattern
src/clients/
├── tts_elevenlabs.py    # External API integration
├── gpt_client.py        # Future AI integration
└── stock_search.py      # Media search integration

# Utility Layer Pattern  
src/utils/
├── srt.py              # Subtitle processing
├── wrap.py             # Text formatting
└── net.py              # Network operations
```

### Processing Pipeline Pattern
```python
# Main Pipeline Flow
pipeline.py:
    1. Script parsing (NA:, セリフ: recognition)
    2. TTS generation (multi-voice switching)
    3. Subtitle creation (time-synced SRT)
    4. Output packaging (JSON metadata)
```

### Error Handling Pattern
```python
# Consistent error handling across modules
try:
    result = external_api_call()
    validate_result(result)
    return process_result(result)
except APIError as e:
    logger.error(f"API failure: {e}")
    return fallback_behavior()
except ValidationError as e:
    logger.error(f"Data validation failed: {e}")
    raise ProcessingError(f"Invalid input: {e}")
```

## File Naming Conventions

### Python Module Naming
- **snake_case**: All Python files (`tts_elevenlabs.py`, `gui_base.py`)
- **Descriptive**: Function-based naming (`resolve_import.py`, `script_editor.py`)
- **Step numbering**: GUI steps use step prefix (`step1_`, `step2_`)

### Directory Naming
- **lowercase**: All directories use lowercase
- **descriptive**: Purpose-based names (`clients/`, `utils/`, `gui_steps/`)
- **plural**: Collections use plural names (`docs/`, `steps/`)

### Output File Structure
```
output/
├── audio/
│   ├── line_001.mp3        # Individual line audio
│   ├── line_002.mp3
│   └── narration.mp3       # Combined narration
├── subtitles/
│   ├── script.srt         # Time-synced subtitles
│   └── subtitles_plain.txt # Plain text for aeneas
└── storyboard/
    └── pack.json          # Metadata & validation
```

### Input File Conventions
```
data/
├── script_name.txt        # Main input scripts
├── test_script.txt        # Testing scripts
└── voice_test_*.txt       # Voice testing scripts
```

## Import Organization

### Standard Import Pattern
```python
# Standard library imports
import os
import sys
import json
import time
from pathlib import Path

# Third-party imports
import requests
from dotenv import load_dotenv

# Local application imports
from src.clients.tts_elevenlabs import ElevenLabsClient
from src.utils.srt import generate_srt
from src.utils.wrap import wrap_japanese_text
```

### Module Dependency Hierarchy
```
pipeline.py (Top Level)
    ├── clients/
    │   ├── tts_elevenlabs.py
    │   └── gpt_client.py
    └── utils/
        ├── srt.py
        ├── wrap.py
        └── net.py
```

## Key Architectural Principles

### 1. Separation of Concerns
- **Pipeline Orchestration**: `pipeline.py` coordinates, doesn't implement
- **External Integration**: Clients handle API specifics
- **Processing Logic**: Utils handle data transformation
- **User Interface**: GUI components handle interaction only

### 2. Configuration Over Code
```python
# Environment-driven configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID_NARRATION = os.getenv('ELEVENLABS_VOICE_ID_NARRATION')
RATE_LIMIT_SLEEP = float(os.getenv('RATE_LIMIT_SLEEP', 0.35))
```

### 3. Error Recovery & Resilience
- **API Failures**: Retry logic with exponential backoff
- **Input Validation**: Early validation with clear error messages
- **Resource Management**: Automatic cleanup of temporary files
- **Fallback Behavior**: Graceful degradation when services unavailable

### 4. Modular Extension Points
```python
# Client Interface Pattern
class TTSClient:
    def generate_speech(self, text: str, voice_id: str) -> bytes:
        raise NotImplementedError

class ElevenLabsClient(TTSClient):
    def generate_speech(self, text: str, voice_id: str) -> bytes:
        # Implementation
```

### 5. Data Flow Transparency
```python
# Clear data transformations
script_text -> parsed_items -> audio_files -> srt_subtitles -> json_metadata
```

### 6. Testing & Development Support
- **Fake Modes**: `--fake-tts` for development without API calls
- **Debug Outputs**: Comprehensive logging and intermediate file outputs
- **Rate Control**: `--rate` parameter for playback speed testing

## Integration Patterns

### DaVinci Resolve Integration
```python
# Standalone script pattern for DaVinci Scripts folder
resolve_import.py:
    - Self-contained execution
    - Multiple import method fallbacks
    - Error reporting to DaVinci console
```

### GUI-Pipeline Integration  
```python
# GUI components delegate to pipeline modules
step2_tts_generation.py:
    from src.clients.tts_elevenlabs import ElevenLabsClient
    # GUI wraps pipeline functionality with UI
```

### External Service Integration
```python
# Consistent client pattern
clients/service_name.py:
    class ServiceClient:
        def __init__(self, api_key, **config)
        def call_api(self, **params)
        def handle_errors(self, response)
```

This structure supports scalable development, clear separation of concerns, and maintainable code organization while enabling both automated pipeline usage and interactive GUI-based workflows.