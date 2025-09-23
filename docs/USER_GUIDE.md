# Mini VTR Pipeline User Guide

## Quick Start

### 1. Installation

```bash
cd minivt_pipeline
pip install -r requirements.txt
```

### 2. Environment Setup

Create `.env` file in the project root:

```bash
# Required - Azure Speech Service
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_azure_region

# Optional - Voice tuning
# AZURE_SPEECH_VOICE=ja-JP-NanamiNeural
# AZURE_SPEECH_VOICE_NARRATION=ja-JP-NanamiNeural
# AZURE_SPEECH_VOICE_DIALOGUE=ja-JP-KeitaNeural
# AZURE_SPEECH_VOICE_FEMALE=ja-JP-MayuNeural
# AZURE_SPEECH_VOICE_MALE=ja-JP-KeitaNeural

# Optional - Performance tuning
HTTP_TIMEOUT=30
RATE_LIMIT_SLEEP=0.35

# Optional - Stock media search (for future features)
ENABLE_PEXELS=1
PEXELS_API_KEY=your_pexels_key
```

### 3. Create Your Script

Create a script file in `data/` folder with this format:

```
NA: ナレーション文章がここに入ります。
セリフ: キャラクターの対話がここに入ります。
NA: 次のナレーション部分です。
セリフ: 別の対話です。
```

**Format Rules:**
- `NA:` = Narration (uses NARRATION voice)
- `セリフ:` = Dialogue (uses DIALOGUE voice)
- Empty lines and other content are ignored
- Text should be natural Japanese for best TTS results

### 4. Run the Pipeline

```bash
# Basic usage
python src/pipeline.py --script data/your_script.txt

# With custom playback speed
python src/pipeline.py --script data/your_script.txt --rate 1.2

# Debug mode (fast testing, no actual TTS)
python src/pipeline.py --script data/your_script.txt --fake-tts
```

### 5. Import to DaVinci Resolve

1. Open DaVinci Resolve with your project
2. Copy `src/resolve_import.py` to DaVinci Scripts folder
3. Go to **Workspace → Scripts → Edit**
4. Run the import script
5. Select the generated SRT file (`output/subtitles/script.srt`)

---

## Detailed Workflow

### Script Writing Guidelines

#### Content Structure
- **8-minute target**: Plan for approximately 1,200-1,600 Japanese characters
- **Natural pacing**: TTS works best with natural sentence structure
- **Clear roles**: Distinct narration vs. dialogue sections
- **Punctuation**: Use Japanese punctuation (。、) for natural TTS pauses

#### Example Script
```
NA: 人工知能の発展により、私たちの日常生活は大きく変化しています。
セリフ: でも、AIって本当に人間の代わりになるんでしょうか？
NA: この疑問に答えるため、最新の研究を見てみましょう。
セリフ: 確かに、一部の作業は自動化できそうですね。
```

### Audio Generation Process

#### Voice Configuration
1. **Narration Voice**: Professional, clear delivery for educational content
2. **Dialogue Voice**: Conversational, engaging tone for character speech
3. **Rate Control**: Adjust playback speed (0.8-1.3 recommended range)

#### Quality Settings
The pipeline targets Azure Speech neural voices:
- **Narration voice**: `ja-JP-NanamiNeural` by default
- **Dialogue voice**: `ja-JP-KeitaNeural` (configurable via env vars)
- **Expressive style**: `narration-professional` for narration, `chat` for dialogue
- **Rate control**: optional playback speed multiplier (`--rate`)

#### Processing Flow
1. **Text Analysis**: Parse roles and content
2. **Voice Switching**: Automatic voice selection by role
3. **TTS Generation**: Sequential processing with rate limiting
4. **Audio Merging**: Seamless concatenation
5. **Speed Adjustment**: Optional rate modification

### Subtitle Generation

#### Text Processing
- **Automatic Wrapping**: Optimized for 2-line display
- **Character Limits**: 22 characters per line (adjustable)
- **Natural Breaks**: Prefers Japanese comma (、) splits
- **Timing Distribution**: Even allocation across audio duration

#### Timing Strategy
- **Minimum Duration**: 1.8 seconds per subtitle (readable)
- **Audio Sync**: Distributed evenly across total duration
- **Display Overlap**: None (clean transitions)

### Output Files

After successful execution, find these files:

```
output/
├── audio/
│   ├── line_001.mp3          # Individual line audio
│   ├── line_002.mp3
│   ├── ...
│   └── narration.mp3         # Merged final audio
├── subtitles/
│   └── script.srt            # SRT subtitle file
├── subtitles_plain.txt       # Plain text for aeneas
└── storyboard/
    └── pack.json             # Pipeline metadata
```

---

## DaVinci Resolve Integration

### Setup Instructions

#### Option 1: Scripts Menu (Recommended)
1. Locate DaVinci Scripts folder:
   - **Windows**: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit`
   - **macOS**: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit`
   - **Linux**: `~/.local/share/DaVinciResolve/Fusion/Scripts/Edit`

2. Copy `src/resolve_import.py` to this folder
3. Restart DaVinci Resolve
4. Access via **Workspace → Scripts → Edit → resolve_import**

#### Option 2: Direct Execution
1. Open DaVinci Resolve with your project
2. Ensure timeline is active
3. Run: `python src/resolve_import.py`
4. Select SRT file when prompted

### Import Process

The script automatically tries multiple import methods:

1. **Timeline.ImportSubtitles()** - Direct timeline import
2. **Timeline.ImportSubtitle()** - Alternative method
3. **Timeline.ImportTimelineSubtitle()** - Legacy method  
4. **MediaPool.ImportMedia()** - Fallback to Media Pool

### Troubleshooting DaVinci Import

#### Common Issues

**"No active project"**
- Solution: Open project and ensure it's the current project

**"No active timeline"**
- Solution: Create timeline and make it active in timeline view

**"Import failed"**
- Solution: Try manual import via Media Pool → right-click → Import Subtitle

#### Manual Import (Fallback)
1. Open Media Pool
2. Right-click → Import Media
3. Select `output/subtitles/script.srt`
4. Drag to timeline subtitle track
5. Right-click subtitle clip → Import Subtitle

---

## Advanced Usage

### Performance Optimization

#### Parallel Processing (Future Enhancement)
Currently sequential TTS processing. For faster generation:
- Consider smaller script chunks
- Use `--fake-tts` for testing layouts
- Pre-generate audio for reusable content

#### Rate Limiting Adjustment
Reduce API delays for faster processing:
```bash
RATE_LIMIT_SLEEP=0.2  # Faster, but respect API limits
```

#### Memory Management
For large scripts:
- Process in chunks if memory issues occur
- Clear audio cache between runs
- Monitor system resources

### Custom Voice Configuration

#### Voice Selection
1. Sign in to the [Azure AI Speech portal](https://speech.microsoft.com/portal)
2. Browse the **Neural voices** catalog for Japanese voices (e.g. Nanami, Keita, Mayu)
3. Update `.env` with any preferred voice overrides (`AZURE_SPEECH_VOICE_*`)
4. Re-run the pipeline; voices are picked automatically by role and gender hints

#### Voice Testing
```bash
# Quick experiment with narration voice override
AZURE_SPEECH_VOICE_NARRATION=ja-JP-AoiNeural \
python src/pipeline.py --script test.txt --fake-tts
```

### Script Variations

#### Multi-Character Dialogue
Currently supports NA/DL roles. For multiple characters:
1. Keep speaker cues consistent in the script
2. Extend role-to-voice mapping in `davinciauto_core/clients/tts_azure.py`
3. Optionally set per-character hints via custom parsing

#### Mixed Language Content
- Azure multilingual voices handle Japanese + English phrases reliably
- For other languages, use language-specific voices through env overrides

---

## Troubleshooting

### Common Errors

#### `AZURE_SPEECH_KEY is not set`
**Solution**: Add your Azure Speech key to `.env`
```bash
AZURE_SPEECH_KEY=your_actual_speech_key_here
```

#### `台本から 'NA:' または 'セリフ:' の行が見つかりませんでした`
**Solution**: Check script format
- Ensure lines start with `NA:` or `セリフ:`
- Verify file encoding is UTF-8
- Check for invisible characters

#### `TTS failed: HTTP 401`
**Solution**: Verify Azure credentials
- Confirm `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`
- Ensure the Speech resource is active
- Test synthesis in the Azure portal

#### `TTS failed: HTTP 429`
**Solution**: Azure rate limiting triggered
- Increase `RATE_LIMIT_SLEEP` value if configured
- Review Azure Speech pricing tier quotas
- Retry after waiting period

### Performance Issues

#### Slow TTS Generation
- **Normal**: 2-3 seconds per line with Azure neural voices
- **Optimize**: Use `--fake-tts` for testing layouts
- **Monitor**: Check network connectivity and Azure status page
- **Scale**: Consider higher pricing tier or regional endpoints

#### Audio Quality Issues
- **Check**: Voice override environment variables
- **Adjust**: Rate setting (0.8-1.2 optimal)
- **Verify**: Input text quality
- **Test**: Alternative Azure voices/styles

### File Issues

#### Permission Errors
```bash
# Ensure write permissions
chmod 755 output/
chmod 644 output/*
```

#### Missing Output Files
- Check error messages in console
- Verify disk space availability
- Ensure parent directories exist

#### Subtitle Sync Issues
- Audio duration affects timing distribution
- Minimum 1.8s display time enforced
- Consider adjusting text length per segment

---

## Best Practices

### Content Creation
1. **Script Length**: Target 200-400 characters per segment
2. **Natural Flow**: Write for spoken delivery, not reading
3. **Pacing**: Allow pauses between major concepts
4. **Clarity**: Use simple, clear sentence structure

### Production Workflow
1. **Draft → Test**: Use `--fake-tts` for layout testing
2. **Voice Check**: Generate single lines for voice validation
3. **Full Generation**: Run complete pipeline
4. **Review**: Check audio and subtitle quality
5. **Import**: Load into DaVinci Resolve
6. **Finalize**: Add visual elements and export

### Quality Assurance
- **Audio Review**: Listen to complete narration
- **Subtitle Check**: Verify timing and readability  
- **Visual Test**: Preview in DaVinci timeline
- **Export Test**: Ensure final video quality

### File Management
```bash
# Organize by project
projects/
├── project_001/
│   ├── script.txt
│   └── output/
├── project_002/
│   ├── script.txt
│   └── output/
└── templates/
    └── script_template.txt
```

---

## Support & Resources

### Documentation
- **API Reference**: `docs/API.md`
- **Code Documentation**: Inline docstrings
- **CLAUDE.md**: Development guidelines

### External Resources
- **Azure Speech Service Documentation**: https://learn.microsoft.com/azure/ai-services/speech-service/
- **DaVinci Resolve Scripting**: Blackmagic Design documentation
- **Japanese TTS Guidelines**: Voice model optimization tips

### Community
- **Issues**: Report bugs via GitHub issues
- **Discussions**: Feature requests and usage questions
- **Contributions**: Pull requests welcome
