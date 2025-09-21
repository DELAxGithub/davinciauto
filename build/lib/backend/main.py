import asyncio
import json
import uuid
import random
import os
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs

try:
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    speechsdk = None  # type: ignore

from .models import (
    LLMGenerateRequest,
    RowData,
    SrtExportRequest,
    TimelineRebuildRequest,
    TTSRequest,
)
from .mcp_routes import router as mcp_router
from .projects_api import router as projects_router
from typing import List, Optional
from pydantic import BaseModel
from core.paths import telop_srt_file

# --- FastAPIアプリケーションの初期化 ---

app = FastAPI(title="DaVinci Auto Backend")

# --- 静的ファイルとCORSの設定 ---

# ElevenLabs クライアントの初期化
# 環境変数 ELEVENLABS_API_KEY が自動的に使用されます
eleven_client = ElevenLabs()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "")
DEFAULT_AZURE_VOICE = os.getenv("AZURE_SPEECH_VOICE", "ja-JP-NanamiNeural")
ELEVEN_DEFAULT_MODEL = "eleven_v3_alpha"


static_dir = Path(__file__).parent / "static"

# CORS (Cross-Origin Resource Sharing) を許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中は "*" で許可。本番ではフロントエンドのドメインに限定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント (llm_workspace.html を配信)
if not static_dir.exists():
    static_dir.mkdir()

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount MCP proxy routes
app.include_router(mcp_router)
app.include_router(projects_router)

@app.get("/")
async def read_index():
    """ルートパスでllm_workspace.htmlを返す"""
    html_path = static_dir / "llm_workspace.html"
    if html_path.is_file():
        return FileResponse(html_path)
    return {"message": "llm_workspace.html not found in static directory."}


# --- APIエンドポイントの定義 ---

@app.post("/api/llm/generate")
async def generate_llm_text(request: LLMGenerateRequest):
    """単一のLLM生成タスクを実行する（モック）"""
    await asyncio.sleep(random.uniform(0.3, 1.0))  # ネットワーク遅延をシミュレート
    
    # ここで実際のLLM呼び出しロジックを実装します
    # from minivt_pipeline.src.clients.gpt_client import GPTClient
    # gpt_client = GPTClient()
    # result = gpt_client.generate(...)
    
    mock_result = f"[{request.task}] {request.row.original[:20]}... の生成結果 (model: {request.params.model})"
    return {"result": mock_result}

@app.post("/api/timeline/rebuild")
async def rebuild_timeline(request: TimelineRebuildRequest):
    """タイムラインのタイムコードを再計算する（モック）"""
    cursor = request.offset_ms / 1000.0
    updated_rows = []
    
    for row in request.rows:
        # ここで実際の音声長推定ロジックを呼び出す
        # from ... import estimate_narr_seconds
        # duration = estimate_narr_seconds(row.narr or row.original)
        duration = row.tDur or random.uniform(2.0, 5.0)
        
        row.tStart = cursor
        row.tEnd = cursor + duration
        row.tDur = duration
        cursor = row.tEnd + (request.gap_ms / 1000.0)
        updated_rows.append(row)
        
    return {"updated_rows": updated_rows}

@app.post("/api/srt/export")
async def export_srt(request: SrtExportRequest):
    """SRTファイルを生成して返す"""
    
    # ここで minivt_pipeline/src/utils/srt.py の build_srt を呼び出す
    # from utils.srt import Cue, build_srt
    
    def srt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    idx = 1
    for r in request.rows:
        text = getattr(r, request.source, "")
        if text and r.tDur > 0:
            start = r.tStart + (request.offset_ms / 1000.0)
            end = r.tEnd + (request.offset_ms / 1000.0)
            lines.append(str(idx))
            lines.append(f"{srt_time(start)} --> {srt_time(end)}")
            lines.append(text)
            lines.append("")
            idx += 1
    
    srt_content = "\n".join(lines)
    
    return StreamingResponse(
        iter([srt_content.encode("utf-8")]),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=subtitles.srt"}
    )


class SrtFileExportRequest(BaseModel):
    rows: List[RowData]
    source: str = "follow"
    offset_ms: int = 0
    project_dir: str
    filename: Optional[str] = None  # default: exports/subtitles/script.srt


@app.post("/api/srt/export_to_file")
async def export_srt_to_file(req: SrtFileExportRequest):
    """Generate SRT and save to project folder (exports/subtitles)."""

    def srt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    idx = 1
    for r in req.rows:
        text = getattr(r, req.source, "")
        if text and r.tDur > 0:
            start = r.tStart + (req.offset_ms / 1000.0)
            end = r.tEnd + (req.offset_ms / 1000.0)
            lines.append(str(idx))
            lines.append(f"{srt_time(start)} --> {srt_time(end)}")
            lines.append(text)
            lines.append("")
            idx += 1

    srt_content = "\n".join(lines)

    base = Path(req.project_dir).expanduser().resolve()
    # If filename is not specified, place under テロップ類/SRT with a generic name
    out_path = base / (req.filename or "テロップ類/SRT/script.srt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(srt_content, encoding="utf-8")
    return {"ok": True, "path": str(out_path), "lines": idx - 1}

@app.websocket("/ws/batch_generate")
async def websocket_batch_generate(websocket: WebSocket):
    """WebSocketでバッチ処理の進捗をリアルタイムに返す"""
    await websocket.accept()
    try:
        # フロントエンドから {"tasks": [...], "rows": [...]} を受け取る想定
        data = await websocket.receive_json()
        tasks = data.get("tasks", [])
        rows = data.get("rows", [])
        total_jobs = len(tasks) * len(rows)
        
        for i in range(total_jobs):
            await asyncio.sleep(0.5) # ダミーの処理時間
            await websocket.send_json({"type": "progress", "done": i + 1, "total": total_jobs})
            # ここで実際の生成処理を行い、結果を返すことも可能
            # await websocket.send_json({"type": "result", ...})
            
        await websocket.send_json({"type": "complete"})
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        await websocket.close(code=1011, reason=str(e))

def _synthesize_with_elevenlabs(request: TTSRequest):
    """Call ElevenLabs TTS and normalize the response object."""
    try:
        audio_data = eleven_client.text_to_speech.convert(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id or ELEVEN_DEFAULT_MODEL,
            output_format="mp3_44100_128",
        )
    except Exception as exc:
        print(f"ElevenLabs API Error: {exc}")
        raise HTTPException(status_code=502, detail=f"ElevenLabs API error: {exc}") from exc

    if isinstance(audio_data, (bytes, bytearray)):
        return Response(content=audio_data, media_type="audio/mpeg")
    return StreamingResponse(audio_data, media_type="audio/mpeg")


async def _synthesize_with_azure(request: TTSRequest):
    """Call Azure Cognitive Services Speech TTS."""
    if speechsdk is None:
        raise HTTPException(status_code=501, detail="Azure Speech SDK is not installed.")
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise HTTPException(status_code=400, detail="Azure Speech credentials are not configured.")

    voice = request.voice_id or DEFAULT_AZURE_VOICE
    text = request.text

    def _run() -> bytes:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        if voice:
            speech_config.speech_synthesis_voice_name = voice
        if hasattr(speech_config, "set_speech_synthesis_output_format"):
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
            )

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        result_future = synthesizer.speak_text_async(text)
        result = result_future.get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)

        if result.reason == getattr(speechsdk.ResultReason, "Canceled", None):
            cancellation = getattr(speechsdk, "CancellationDetails", None)
            details = None
            if cancellation and hasattr(cancellation, "from_result"):
                try:
                    details = cancellation.from_result(result)
                except Exception:
                    details = None
            message = getattr(details, "error_details", None) or "Azure speech synthesis canceled."
            raise RuntimeError(message)

        raise RuntimeError("Azure speech synthesis failed.")

    try:
        audio_bytes = await asyncio.to_thread(_run)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Azure Speech error: {exc}") from exc

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """音声合成ルーター。プロバイダに応じて合成を実行する。"""
    provider = (request.provider or "elevenlabs").lower()

    if provider == "elevenlabs":
        return _synthesize_with_elevenlabs(request)
    if provider == "azure":
        return await _synthesize_with_azure(request)

    raise HTTPException(status_code=400, detail=f"Unsupported TTS provider: {request.provider}")
