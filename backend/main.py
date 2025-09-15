import asyncio
import json
import random
import os
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs

from .models import (
    LLMGenerateRequest,
    RowData,
    SrtExportRequest,
    TimelineRebuildRequest,
    TTSRequest,
)
from .mcp_routes import router as mcp_router

# --- FastAPIアプリケーションの初期化 ---

app = FastAPI(title="DaVinci Auto Backend")

# --- 静的ファイルとCORSの設定 ---

# ElevenLabs クライアントの初期化
# 環境変数 ELEVENLABS_API_KEY が自動的に使用されます
eleven_client = ElevenLabs()


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

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """
    ElevenLabs APIを使用して音声データを生成して返す。
    eleven_v3_alpha固定で最高品質音声合成。
    """
    try:
        # 品質最優先: eleven_v3_alpha固定
        audio_data = eleven_client.text_to_speech.convert(
            text=request.text,
            voice_id=request.voice_id,
            model_id="eleven_v3_alpha",  # 最高品質モデル固定
            output_format="mp3_44100_128",
        )
        # Handle both bytes and streaming generator
        if isinstance(audio_data, (bytes, bytearray)):
            return Response(content=audio_data, media_type="audio/mpeg")
        return StreamingResponse(audio_data, media_type="audio/mpeg")
    except Exception as e:
        print(f"ElevenLabs API Error: {e}")
        return {"error": str(e)}
