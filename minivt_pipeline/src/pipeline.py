import argparse, json, os, pathlib, re
from dotenv import load_dotenv
from utils.wrap import split_two_lines
from utils.srt import Cue, distribute_by_audio_length, build_srt
from pydub import AudioSegment
from clients.tts_elevenlabs import tts_elevenlabs_per_line, TTSError
from utils.cost_tracker import CostTracker
from config.voice_presets import VoicePresetManager

def _write(path: str, content: str):
    """
    Write content to file, creating parent directories if needed.
    
    Args:
        path: Target file path
        content: Content to write
    """
    pathlib.Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(content)

def parse_script(script_text: str):
    """
    台本の 'NA:' / 'セリフ:' を抽出し、[{role, text}] を返す（登場順）。
    """
    items = []
    for line in script_text.splitlines():
        s = line.strip()
        if not s: 
            continue
        if s.startswith("NA:"):
            items.append({"role":"NA", "text": s.replace("NA:", "", 1).strip()})
        elif s.startswith("セリフ:"):
            items.append({"role":"DL", "text": s.replace("セリフ:", "", 1).strip()})
        # それ以外（見出しなど）は無視
    return items

def main(args):
    """
    Main pipeline execution: script → TTS → subtitles → DaVinci output.
    
    Process flow:
    1. Parse script format (NA:/セリフ: lines)
    2. Generate TTS audio with voice switching
    3. Create time-synced SRT subtitles
    4. Output structured JSON for validation
    
    Args:
        args: Command line arguments with script path, rate, and flags
    """
    load_dotenv()
    script_text = open(args.script, "r", encoding="utf-8").read()
    items = parse_script(script_text)
    if not items:
        raise RuntimeError("台本から 'NA:' または 'セリフ:' の行が見つかりませんでした。")
    
    # コスト追跡初期化
    cost_tracker = CostTracker()

    # 1) TTS（行ごとボイス切替） or 無音
    try:
        if args.fake_tts:
            est = max(2.5 * len(items), 3.0)
            audio_path = os.path.join("output","audio","narration.mp3")
            pathlib.Path(os.path.dirname(audio_path)).mkdir(parents=True, exist_ok=True)
            AudioSegment.silent(duration=int(est*1000), frame_rate=44100).export(audio_path, format="mp3")
            piece_files = []
        else:
            audio_path, piece_files = tts_elevenlabs_per_line(
                items, 
                out_dir="output/audio", 
                rate=args.rate, 
                cost_tracker=cost_tracker,
                enable_voice_parsing=not args.disable_voice_parsing,
                voice_preset=args.voice_preset
            )
    except TTSError as e:
        print(f"[WARN] TTS failed: {e}\n--> Falling back to silent audio.")
        audio_path = os.path.join("output","audio","narration.mp3")
        AudioSegment.silent(duration=int(max(2.5*len(items),3.0)*1000), frame_rate=44100).export(audio_path, format="mp3")
        piece_files = []

    # 2) 字幕（各行テキストを2行化）
    subs = [{"text_2line": split_two_lines(it["text"])} for it in items]

    # 3) タイムコード（音声尺から均等割り）→SRT
    audio_len = AudioSegment.from_file(audio_path).duration_seconds
    times = distribute_by_audio_length(len(subs), audio_len, 1.8)
    cues=[Cue(idx=i,start=tt[0],end=tt[1],lines=sub["text_2line"]) for i,(sub,tt) in enumerate(zip(subs,times),1)]
    srt=build_srt(cues)
    _write("output/subtitles/script.srt", srt)

    # aeneas用プレーン
    plain_lines = ["".join(x["text_2line"]) for x in subs]
    _write("output/subtitles_plain.txt", "\n".join(plain_lines))

    # JSON（検証用に簡易構造を保存）
    pack = {
        "items": items,
        "audio_path": audio_path,
        "pieces": piece_files,
        "subtitles": subs
    }
    pathlib.Path("output/storyboard").mkdir(parents=True, exist_ok=True)
    with open("output/storyboard/pack.json","w",encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    # コスト情報表示と保存
    if not args.fake_tts:
        print(cost_tracker.get_cost_summary())
        log_file = cost_tracker.save_usage_log()
        print(f"- Usage log: {log_file}")
        
        # 累積使用量表示
        total_usage = cost_tracker.get_total_usage()
        if total_usage["total_requests"] > len(cost_tracker.session_requests):
            print(f"📊 Total usage: ¥{total_usage['estimated_total_cost_jpy']} ({total_usage['total_requests']} total requests)")
    
    print("✅ Completed.")
    print("- Audio:   ", audio_path)
    print("- SRT:     output/subtitles/script.srt")
    print("- Plain:   output/subtitles_plain.txt")
    print("- JSON:    output/storyboard/pack.json")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--script", help="入力スクリプトファイル")
    ap.add_argument("--rate", type=float, default=1.0, help="再生速度倍率")
    ap.add_argument("--fake-tts", action="store_true", help="TTSをスキップして無音を生成（デバッグ用）")
    ap.add_argument("--voice-preset", choices=["narration", "dialogue", "emotional", "documentary", "commercial"], 
                    help="音声品質プリセット")
    ap.add_argument("--list-presets", action="store_true", help="利用可能なプリセット一覧を表示")
    ap.add_argument("--disable-voice-parsing", action="store_true", help="音声指示解析を無効化")
    args=ap.parse_args()
    
    # プリセット一覧表示
    if args.list_presets:
        preset_manager = VoicePresetManager()
        print("🎤 利用可能な音声プリセット:")
        for name, info in preset_manager.list_presets().items():
            print(f"  {name}: {info['name']} - {info['description']}")
        exit(0)
    
    # スクリプトファイルが必要
    if not args.script:
        ap.error("--script is required unless using --list-presets")
    
    main(args)
