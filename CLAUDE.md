# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Active Specifications
- **davinci-fusion-script-integration**: DaVinci Resolve Fusionスクリプト統合 - SRT自動インポート、レンダリング設定、Export Queue追加機能
- Use `/kiro:spec-status [feature-name]` to check progress

## Project Overview

This is a Mini VTR (Video) Automation Pipeline for creating 8-minute educational videos. The system automates the workflow from script input to DaVinci Resolve import, handling TTS generation, subtitle creation, and timeline integration.

**Core Flow**: Script → JSON generation → TTS audio → Automatic SRT → DaVinci Resolve import

## Development Commands

### Setup
```bash
cd minivt_pipeline
pip install -r requirements.txt
```

### Main Pipeline Execution
```bash
# Run the complete pipeline
python src/pipeline.py --script data/script.txt

# With custom playback rate
python src/pipeline.py --script data/script.txt --rate 1.2

# Debug mode (skip TTS, generate silent audio)
python src/pipeline.py --script data/script.txt --fake-tts
```

### Environment Configuration
Required environment variables:
- `ELEVENLABS_API_KEY` - ElevenLabs TTS API key
- `ELEVENLABS_VOICE_ID` - Default voice ID
- `ELEVENLABS_VOICE_ID_NARRATION` - Voice for narration (NA:)
- `ELEVENLABS_VOICE_ID_DIALOGUE` - Voice for dialogue (セリフ:)
- `OPENAI_API_KEY` - For GPT client (currently stubbed)
- `HTTP_TIMEOUT` - API timeout (default: 30)
- `RATE_LIMIT_SLEEP` - TTS request delay (default: 0.35)

## Architecture

### Pipeline Core (`src/pipeline.py`)
Main orchestrator that:
1. Parses script format (`NA:` for narration, `セリフ:` for dialogue)
2. Generates TTS audio with role-based voice switching
3. Creates time-synced SRT subtitles
4. Outputs structured JSON for validation

### Client Layer (`src/clients/`)
- **`tts_elevenlabs.py`**: ElevenLabs TTS integration with voice switching, rate control, and error handling
- **`gpt_client.py`**: GPT client stub for future JSON generation features
- **`stock_search.py`**: Placeholder for stock media search

### Utilities (`src/utils/`)
- **`srt.py`**: SRT subtitle generation with time distribution and formatting
- **`wrap.py`**: Japanese text wrapping for 2-line subtitle display
- **`net.py`**: Network utilities

### DaVinci Integration (`src/resolve_import.py`)
Standalone script for importing SRT files into DaVinci Resolve timelines. Handles multiple API methods and provides Media Pool fallback.

## Key Data Structures

### Script Format
```
NA: ナレーション文章
セリフ: 人物の対話
```

### Internal Item Structure
```python
{"role": "NA"|"DL", "text": "content"}
```

### Output Structure
- `output/audio/` - Individual line MP3s and merged narration
- `output/subtitles/` - SRT files and plain text for aeneas
- `output/storyboard/` - JSON metadata for validation

## Development Notes

### TTS Voice Management
The system uses role-based voice switching:
- `NA:` lines use `ELEVENLABS_VOICE_ID_NARRATION`
- `セリフ:` lines use `ELEVENLABS_VOICE_ID_DIALOGUE`
- Rate limiting and error recovery are built-in

### Subtitle Generation Strategy
- Text automatically wrapped to 2 lines using Japanese punctuation
- Time codes distributed evenly across audio duration
- Minimum 1.8-second display duration per subtitle

### DaVinci Resolve Integration
- Use `resolve_import.py` from DaVinci Scripts menu
- Multiple import methods attempted automatically
- Falls back to Media Pool import if timeline import fails

## Testing Strategy

### Pipeline Testing
```bash
# Test with fake TTS (fast execution)
python src/pipeline.py --script data/script.txt --fake-tts
```

### Manual Verification Points
1. Audio files generated in `output/audio/`
2. SRT timing accuracy in `output/subtitles/script.srt`
3. JSON structure validation in `output/storyboard/pack.json`
4. DaVinci Resolve import success

## Documentation

### Comprehensive Documentation Suite
- **[User Guide](docs/USER_GUIDE.md)**: Complete usage instructions, troubleshooting, and best practices
- **[API Documentation](docs/API.md)**: Detailed function references, parameters, and examples
- **Inline Documentation**: Function docstrings for all core components

### Quick References
- **Environment Setup**: See `docs/USER_GUIDE.md#environment-setup`
- **Script Format**: See `docs/USER_GUIDE.md#script-writing-guidelines`
- **API Functions**: See `docs/API.md` for complete function signatures
- **Troubleshooting**: See `docs/USER_GUIDE.md#troubleshooting`

## Code Quality Standards

### Documentation Coverage
- ✅ All public functions documented with docstrings
- ✅ Comprehensive type hints throughout
- ✅ Error handling patterns documented
- ✅ Usage examples provided

### Security Considerations
- ⚠️ API keys properly externalized via environment variables
- ⚠️ Error messages sanitized to prevent information leakage
- ✅ Input validation for file paths and user content
- ✅ Timeout and rate limiting for external API calls

### Performance Characteristics
- **TTS Generation**: ~2-3 seconds per line (sequential processing)
- **Rate Limiting**: 0.35s delay between API requests
- **Memory Usage**: Moderate (audio segments cached during processing)
- **Optimization Potential**: 70% speed improvement via parallel TTS processing