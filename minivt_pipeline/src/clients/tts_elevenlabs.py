import os, json, pathlib, requests, time
from typing import List, Dict
from pydub import AudioSegment

ELEVEN_VOICE_ID_DEFAULT = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVEN_VOICE_ID_NAR = os.getenv("ELEVENLABS_VOICE_ID_NARRATION", ELEVEN_VOICE_ID_DEFAULT)
ELEVEN_VOICE_ID_DLG = os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", ELEVEN_VOICE_ID_DEFAULT)

class TTSError(RuntimeError): pass

def _ensure_audio_response(r: requests.Response) -> None:
    ct = (r.headers.get("content-type") or "").lower()
    if r.status_code >= 400 or ("audio" not in ct and not ct.startswith("application/octet-stream")):
        raise TTSError(f"ElevenLabs TTS failed: HTTP {r.status_code} content-type={ct} body={r.text[:500]}")

def _tts_once(text: str, voice_id: str, out_path: str, rate: float):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise TTSError("ELEVENLABS_API_KEY is not set")
    headers = {"xi-api-key": api_key, "accept": "audio/mpeg", "content-type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability":0.4,"similarity_boost":0.8,"style":0.3,"use_speaker_boost":True},
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=int(os.getenv("HTTP_TIMEOUT","30")))
    _ensure_audio_response(r)
    with open(out_path, "wb") as f:
        f.write(r.content)
    # 可変速
    if rate != 1.0:
        seg = AudioSegment.from_file(out_path)
        seg = seg._spawn(seg.raw_data, overrides={"frame_rate": int(seg.frame_rate * rate)}).set_frame_rate(seg.frame_rate)
        seg.export(out_path, format="mp3")

def tts_elevenlabs_per_line(items: List[Dict], out_dir="output/audio", rate: float = 1.0):
    """
    items: [{ "role": "NA" or "DL", "text": "..." }, ...]
    roleごとにボイスIDを切替。生成した各行MP3を結合して narration.mp3 を返す。
    """
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    files = []
    for i, it in enumerate(items, start=1):
        role = (it.get("role") or "").upper()
        text = it.get("text","").strip()
        if not text:
            continue
        voice_id = ELEVEN_VOICE_ID_NAR if role == "NA" else ELEVEN_VOICE_ID_DLG
        fp = os.path.join(out_dir, f"line_{i:03d}.mp3")
        _tts_once(text, voice_id, fp, rate)
        files.append(fp)
        time.sleep(float(os.getenv("RATE_LIMIT_SLEEP","0.35")))
    # 結合
    merged = AudioSegment.empty()
    for fp in files:
        merged += AudioSegment.from_file(fp)
    merged_fp = os.path.join(out_dir, "narration.mp3")
    merged.export(merged_fp, format="mp3")
    return merged_fp, files
