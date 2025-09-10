# Technology Stack

## Architecture Overview

Mini VTR Automation Pipelineは、モジュラーなPythonアーキテクチャを採用し、各処理ステップを独立したコンポーネントとして実装しています。

```
Script Input → TTS Generation → Subtitle Creation → DaVinci Integration
     ↓              ↓               ↓                    ↓
  Parser        ElevenLabs       SRT Generator      Resolve API
```

## Core Technology Stack

### Primary Language & Runtime
- **Python**: 3.11以上（メイン開発言語）
- **Virtual Environment**: `.venv` による依存関係分離
- **Package Management**: pip + requirements.txt

### External APIs & Services
- **ElevenLabs TTS**: 高品質音声合成サービス
  - Multi-voice support (ナレーション・対話別音声)
  - Rate limiting対応（0.35s間隔）
  - Error recovery & retry機能
- **OpenAI GPT**: JSON生成・テキスト処理（将来拡張用）
- **DaVinci Resolve API**: タイムライン・メディア統合

### Key Python Libraries

#### Core Processing
```python
# Audio & Media Processing
import requests          # HTTP API通信
import json             # データ構造処理
import os, sys          # システム操作
import time             # レート制限・タイミング

# Text Processing
import re               # 正規表現（テキスト解析）
# Custom modules for Japanese text wrapping

# File I/O & Data
import pathlib          # ファイルパス操作
import tempfile         # 一時ファイル管理
```

#### Specialized Modules
- **`src/clients/tts_elevenlabs.py`**: TTS API統合
- **`src/clients/gpt_client.py`**: GPT API統合（スタブ）
- **`src/utils/srt.py`**: SRT字幕生成
- **`src/utils/wrap.py`**: 日本語テキスト整形
- **`src/utils/net.py`**: ネットワークユーティリティ

## Development Environment

### Required Tools
```bash
# Core Requirements
python >= 3.11
pip (Python package manager)

# Development Tools
git                    # Version control
vscode/ide            # Code editor with Python support

# System Dependencies
curl/wget             # API testing tools
DaVinci Resolve 18+   # Video editing integration
```

### Environment Setup
```bash
# Virtual Environment
cd minivt_pipeline
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Dependencies
pip install -r requirements.txt
```

## Configuration Management

### Environment Variables
```bash
# Required - ElevenLabs TTS
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=default_voice_id
ELEVENLABS_VOICE_ID_NARRATION=narration_voice
ELEVENLABS_VOICE_ID_DIALOGUE=dialogue_voice

# Optional - OpenAI (Future Use)
OPENAI_API_KEY=your_openai_key

# Performance Tuning
HTTP_TIMEOUT=30
RATE_LIMIT_SLEEP=0.35
```

### Configuration Files
- **`.env`**: 環境変数（ローカル開発）
- **`requirements.txt`**: Python依存関係
- **`output/`**: 生成ファイル格納ディレクトリ

## Common Development Commands

### Pipeline Execution
```bash
# Complete Pipeline
python src/pipeline.py --script data/script.txt

# Development/Testing
python src/pipeline.py --script data/script.txt --fake-tts
python src/pipeline.py --script data/script.txt --rate 1.2

# Debug Mode
python debug_split.py
```

### Development Workflow
```bash
# Environment Setup
cd minivt_pipeline
source .venv/bin/activate

# Testing
python -m pytest tests/        # Unit tests (if implemented)
python src/pipeline.py --fake-tts  # Integration test

# DaVinci Integration
# Copy src/resolve_import.py to DaVinci Scripts folder
# Run from DaVinci: Workspace → Scripts → Edit → resolve_import
```

### GUI Development
```bash
# GUI Components Testing
cd gui_steps
python step1_script_editor.py      # Script editor GUI
python step2_tts_generation.py     # TTS generation GUI
python step3_subtitle_timing.py    # Subtitle timing GUI
python step4_davinci_export.py     # DaVinci export GUI
python integrated_workspace.py     # Complete GUI workspace
python run_all_steps.py           # Automated pipeline
```

## Architecture Patterns

### Modular Design
- **Separation of Concerns**: 各処理ステップが独立したモジュール
- **Client-Server Pattern**: 外部API（ElevenLabs, OpenAI）はクライアント経由
- **Pipeline Pattern**: 順次処理フローの実装
- **Error Handling**: 各ステップでのエラー回復機能

### Data Flow Architecture
```
Input: Text Script (.txt)
    ↓
Parse: Role-based content extraction (NA:, セリフ:)
    ↓
TTS: Multi-voice audio generation (MP3)
    ↓
Subtitle: Time-synced SRT generation
    ↓
Output: DaVinci Resolve import-ready files
```

### File Organization Strategy
- **Functional Grouping**: `src/clients/`, `src/utils/` による機能別分割
- **Output Separation**: `output/audio/`, `output/subtitles/` による出力種別管理
- **Configuration Separation**: Environment variables for sensitive data

## Performance Characteristics

### Processing Performance
- **TTS Generation**: ~2-3秒/行（API制限によるシーケンシャル処理）
- **Subtitle Generation**: ~0.1秒（ローカル処理）
- **File I/O**: Minimal overhead（小サイズファイル中心）

### Optimization Opportunities
- **Parallel TTS Processing**: 70%高速化可能（API制限内での並列処理）
- **Caching**: TTS結果キャッシュによる再処理高速化
- **Batch Processing**: 複数スクリプト一括処理

### Resource Usage
- **Memory**: 軽量（音声セグメント一時保持のみ）
- **Storage**: 出力ファイルサイズ = 音声時間 × 品質設定
- **Network**: ElevenLabs API帯域幅に依存

## Integration Points

### DaVinci Resolve Integration
- **Python API**: DaVinci Resolve 18+ Fusion Scripts
- **Import Methods**: Timeline import, Media Pool fallback
- **File Formats**: SRT字幕, MP3音声ファイル

### External Service Dependencies
- **ElevenLabs**: TTS生成（必須）
- **OpenAI**: テキスト処理（オプション、将来拡張）
- **DaVinci Resolve**: 動画編集統合（推奨）

## Quality Assurance

### Testing Strategy
- **Integration Testing**: `--fake-tts` フラグによる高速テスト
- **API Testing**: ElevenLabs接続・レート制限テスト
- **Output Validation**: 生成ファイル形式・内容検証

### Error Handling
- **Network Resilience**: API timeout・retry logic
- **Input Validation**: スクリプト形式・文字エンコーディング検証
- **Resource Management**: 一時ファイル自動クリーンアップ