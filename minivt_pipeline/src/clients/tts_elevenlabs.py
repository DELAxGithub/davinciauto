import os, json, pathlib, requests, time
from typing import List, Dict, Optional
from pydub import AudioSegment
from utils.cost_tracker import CostTracker
from utils.voice_parser import VoiceInstructionParser
from config.voice_presets import VoicePresetManager

ELEVEN_VOICE_ID_DEFAULT = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVEN_VOICE_ID_NAR = os.getenv("ELEVENLABS_VOICE_ID_NARRATION", ELEVEN_VOICE_ID_DEFAULT)
ELEVEN_VOICE_ID_DLG = os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", ELEVEN_VOICE_ID_DEFAULT)

class TTSError(RuntimeError): pass

def _ensure_audio_response(r: requests.Response) -> None:
    """
    Validate ElevenLabs API response contains audio data.
    
    Args:
        r: requests.Response object from ElevenLabs API
        
    Raises:
        TTSError: If response is not valid audio content
    """
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code >= 400 or ("audio" not in ct and not ct.startswith("application/octet-stream")):
        raise TTSError(f"ElevenLabs TTS failed: HTTP {r.status_code} content-type={ct} body={r.text[:500]}")

def _tts_once(text: str, voice_id: str, out_path: str, rate: float, cost_tracker: Optional[CostTracker] = None, voice_settings: Optional[Dict] = None):
    """
    Generate single TTS audio file from text using ElevenLabs API.
    
    Features:
    - Uses eleven_v3 model for enhanced Japanese support
    - Applies playback rate adjustment if rate != 1.0
    - Validates audio response and handles errors
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID
        out_path: Output MP3 file path
        rate: Playback speed multiplier (1.0 = normal)
        cost_tracker: Optional cost tracking instance
        voice_settings: Optional custom voice settings
        
    Raises:
        TTSError: If API key missing or TTS generation fails
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise TTSError("ELEVENLABS_API_KEY is not set")
    headers = {"xi-api-key": api_key, "accept": "audio/mpeg", "content-type": "application/json"}
    
    # デフォルト音声設定
    default_voice_settings = {"stability":0.5,"similarity_boost":0.8,"style":0.3,"use_speaker_boost":True}
    if voice_settings:
        default_voice_settings.update(voice_settings)
    
    payload = {
        "text": text,
        "model_id": "eleven_v3_alpha",  # 最高品質モデル固定
        "voice_settings": default_voice_settings,
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=int(os.getenv("HTTP_TIMEOUT","60")))
    _ensure_audio_response(r)
    
    # コスト追跡
    if cost_tracker:
        cost_tracker.track_request(text, payload["model_id"], voice_id)
    with open(out_path, "wb") as f:
        f.write(r.content)
    # 可変速
    if rate != 1.0:
        seg = AudioSegment.from_file(out_path)
        seg = seg._spawn(seg.raw_data, overrides={"frame_rate": int(seg.frame_rate * rate)}).set_frame_rate(seg.frame_rate)
        seg.export(out_path, format="mp3")

def tts_elevenlabs_per_line(items: List[Dict], out_dir="output/audio", rate: float = 1.0, cost_tracker: Optional[CostTracker] = None, enable_voice_parsing: bool = True, voice_preset: Optional[str] = None):
    """
    items: [{ "role": "NA" or "DL", "text": "..." }, ...]
    roleごとにボイスIDを切替。音声指示解析により動的にボイス選択。
    生成した各行MP3を結合して narration.mp3 を返す。
    
    Args:
        items: スクリプトアイテムリスト
        out_dir: 出力ディレクトリ
        rate: 再生速度
        cost_tracker: コスト追跡インスタンス
        enable_voice_parsing: 音声指示解析の有効/無効
        voice_preset: 音声品質プリセット名
    """
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    voice_parser = VoiceInstructionParser() if enable_voice_parsing else None
    preset_manager = VoicePresetManager() if voice_preset else None
    files = []
    
    for i, it in enumerate(items, start=1):
        role = (it.get("role") or "").upper()
        text = it.get("text","").strip()
        if not text:
            continue
            
        # 音声指示解析
        if voice_parser:
            clean_text, voice_id, voice_settings = voice_parser.process_script_line(text, role)
            # 解析されたテキストでアイテムを更新
            it["text"] = clean_text
        else:
            # 従来の方式
            clean_text = text
            voice_id = ELEVEN_VOICE_ID_NAR if role == "NA" else ELEVEN_VOICE_ID_DLG
            voice_settings = None
            
        # プリセット適用
        if preset_manager:
            preset_settings = preset_manager.apply_preset_to_role(voice_preset, role)
            if voice_settings:
                # 音声指示の設定とプリセットをマージ（音声指示優先）
                merged_settings = preset_settings.copy()
                merged_settings.update(voice_settings)
                voice_settings = merged_settings
            else:
                voice_settings = preset_settings
            
        fp = os.path.join(out_dir, f"line_{i:03d}.mp3")
        _tts_once(clean_text, voice_id, fp, rate, cost_tracker, voice_settings)
        files.append(fp)
        time.sleep(float(os.getenv("RATE_LIMIT_SLEEP","1.0")))
    # 結合
    merged = AudioSegment.empty()
    for fp in files:
        merged += AudioSegment.from_file(fp)
    merged_fp = os.path.join(out_dir, "narration.mp3")
    merged.export(merged_fp, format="mp3")
    return merged_fp, files
