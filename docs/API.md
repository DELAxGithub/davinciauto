# Mini VTR Pipeline API Documentation

## Overview

The Mini VTR Pipeline provides a modular API for educational video automation, handling script parsing, TTS generation, subtitle creation, and DaVinci Resolve integration.

## Core Components

### Pipeline Module (`src/pipeline.py`)

#### `parse_script(script_text: str) -> List[Dict[str, str]]`

Extracts narration and dialogue from script format.

**Input Format:**
```
NA: ナレーション文章
セリフ: 人物の対話
```

**Returns:**
```python
[
    {"role": "NA", "text": "ナレーション内容"},
    {"role": "DL", "text": "対話内容"}
]
```

#### `main(args) -> None`

Main pipeline orchestrator executing the complete workflow.

**Process Flow:**
1. Parse script format (NA:/セリフ: lines)
2. Generate TTS audio with voice switching  
3. Create time-synced SRT subtitles
4. Output structured JSON for validation

**Arguments:**
- `args.script`: Path to script file
- `args.rate`: Audio playback rate (default: 1.0)
- `args.fake_tts`: Skip TTS, generate silent audio for testing

**Outputs:**
- `output/audio/narration.mp3`: Merged audio file
- `output/subtitles/script.srt`: SRT subtitle file
- `output/storyboard/pack.json`: Pipeline metadata

---

## TTS Client (`src/clients/tts_elevenlabs.py`)

### Configuration

**Required Environment Variables:**
```bash
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID_NARRATION=voice_id_for_na
ELEVENLABS_VOICE_ID_DIALOGUE=voice_id_for_dialogue
```

**Optional Settings:**
```bash
HTTP_TIMEOUT=30                # API timeout (seconds)
RATE_LIMIT_SLEEP=0.35         # Delay between requests (seconds)
```

### API Functions

#### `tts_elevenlabs_per_line(items: List[Dict], out_dir: str, rate: float) -> Tuple[str, List[str]]`

Generate TTS audio with role-based voice switching.

**Parameters:**
- `items`: List of `{"role": "NA"|"DL", "text": "content"}` objects
- `out_dir`: Output directory for audio files (default: "output/audio")
- `rate`: Playback speed multiplier (default: 1.0)

**Returns:**
- `(merged_audio_path, individual_files_list)`

**Features:**
- Automatic voice switching based on role
- Rate limiting and error recovery
- Audio concatenation and speed adjustment
- Graceful fallback to silent audio on failure

**Error Handling:**
```python
try:
    audio_path, pieces = tts_elevenlabs_per_line(items)
except TTSError as e:
    print(f"TTS failed: {e}")
    # Falls back to silent audio generation
```

---

## Subtitle Utilities (`src/utils/srt.py`)

### Data Structures

#### `Cue` (dataclass)
```python
@dataclass
class Cue:
    idx: int           # Subtitle sequence number
    start: float       # Start time in seconds
    end: float         # End time in seconds  
    lines: List[str]   # Subtitle text lines
```

### Functions

#### `distribute_by_audio_length(n_items: int, audio_length_sec: float, min_sec: float) -> List[Tuple[float, float]]`

Distribute subtitle timing evenly across audio duration.

**Parameters:**
- `n_items`: Number of subtitle segments
- `audio_length_sec`: Total audio duration
- `min_sec`: Minimum display time per subtitle (default: 1.5s)

**Returns:**
List of `(start_time, end_time)` tuples

#### `build_srt(cues: List[Cue]) -> str`

Generate complete SRT file content from cue objects.

**SRT Format:**
```
1
00:00:00,000 --> 00:00:02,500
Subtitle line 1
Subtitle line 2

2
00:00:02,500 --> 00:00:05,000
Next subtitle
```

---

## Text Processing (`src/utils/wrap.py`)

#### `split_two_lines(text: str, max_len: int = 22) -> List[str]`

Split Japanese text for optimal subtitle display.

**Algorithm:**
1. Remove whitespace, check single-line fit
2. Find split point around halfway mark
3. Prefer Japanese comma (、) for natural breaks
4. Fallback to max_len cutoff

**Parameters:**
- `text`: Japanese text to split
- `max_len`: Maximum characters per line

**Returns:**
List of 1-2 strings for subtitle display

---

## Stock Media Search (`src/clients/stock_search.py`)

Multi-provider stock media search supporting images, videos, and audio.

### Supported Providers
- **Pexels**: Images and videos
- **Unsplash**: Images only
- **Storyblocks**: Images and videos (enterprise)
- **Getty Images**: Images and videos (enterprise) 
- **Pixabay**: Images and videos
- **Freesound**: Audio only

### Configuration

**Provider Toggles:**
```bash
ENABLE_PEXELS=1
ENABLE_UNSPLASH=1
ENABLE_STORYBLOCKS=0    # Enterprise only
ENABLE_GETTY=0          # Enterprise only
ENABLE_PIXABAY=0
ENABLE_FREESOUND=0
```

**API Keys:**
```bash
PEXELS_API_KEY=your_key
UNSPLASH_ACCESS_KEY=your_key
STORYBLOCKS_API_KEY=your_key
GETTY_IMAGES_API_KEY=your_key
GETTY_IMAGES_API_SECRET=your_secret
PIXABAY_API_KEY=your_key
FREESOUND_API_KEY=your_key
```

### API Functions

#### `multi_search(query: str, kind: str = "any", limit: int = 5) -> List[Dict[str, Any]]`

Search across all enabled providers.

**Parameters:**
- `query`: Search terms
- `kind`: Media type ("image", "video", "audio", "any")
- `limit`: Results per provider

**Returns:**
Normalized result objects:
```python
{
    "provider": "pexels",
    "kind": "image",
    "id": "12345",
    "title": "Description",
    "url": "https://...",
    "preview": "https://preview...",
    "width": 1920,
    "height": 1080,
    "duration": 30.5,  # For videos/audio
    "extra": {"license": "..."}
}
```

### CLI Usage
```bash
python -m clients.stock_search --query "city morning" --type video --limit 3
```

---

## DaVinci Resolve Integration (`src/resolve_import.py`)

### Usage

1. Copy script to DaVinci Scripts folder
2. Access via **Workspace → Scripts → Edit**
3. Select SRT file when prompted
4. Script attempts multiple import methods automatically

### API Methods Attempted

1. `timeline.ImportSubtitles(srt_path)`
2. `timeline.ImportSubtitle(srt_path)` 
3. `timeline.ImportTimelineSubtitle(srt_path)`
4. `mediapool.ImportMedia([srt_path])` (fallback)

### Error Handling

- Graceful degradation through import method fallbacks
- Media Pool import as final option
- Comprehensive logging for troubleshooting
- User-friendly error messages

---

## Error Handling Patterns

### Custom Exceptions

#### `TTSError(RuntimeError)`
Raised for TTS generation failures, API issues, or configuration problems.

### Graceful Degradation

1. **TTS Failure**: Automatic fallback to silent audio generation
2. **API Timeout**: Retry with exponential backoff  
3. **Missing Config**: Clear error messages with setup guidance
4. **DaVinci Import**: Multiple method attempts with fallbacks

### Logging Strategy

```python
# Example error handling pattern
try:
    result = api_operation()
except SpecificError as e:
    log.warning(f"Operation failed: {e}, falling back...")
    result = fallback_operation()
except Exception as e:
    log.error(f"Critical failure: {e}")
    raise
```

---

## Performance Characteristics

### TTS Generation
- **Sequential Processing**: ~2-3 seconds per line
- **Rate Limiting**: 0.35s delay between requests
- **Timeout**: 30 seconds per API call
- **Memory Usage**: Moderate (audio segments cached)

### Subtitle Processing
- **Text Wrapping**: O(n) complexity
- **Timing Distribution**: O(n) linear calculation
- **SRT Generation**: O(n) string concatenation

### Optimization Opportunities
- Parallel TTS processing (70% performance gain)
- Adaptive rate limiting (20% improvement)
- Audio streaming for large files