import argparse, json, os, pathlib, re
from dotenv import load_dotenv
from utils.wrap import split_two_lines
from utils.srt import Cue, distribute_by_audio_length, build_srt
from pydub import AudioSegment
from clients.tts_elevenlabs import tts_elevenlabs_per_line, TTSError

def _write(path: str, content: str):
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
    load_dotenv()
    script_text = open(args.script, "r", encoding="utf-8").read()
    items = parse_script(script_text)
    if not items:
        raise RuntimeError("台本から 'NA:' または 'セリフ:' の行が見つかりませんでした。")

    # 1) TTS（行ごとボイス切替） or 無音
    try:
        if args.fake_tts:
            est = max(2.5 * len(items), 3.0)
            audio_path = os.path.join("output","audio","narration.mp3")
            pathlib.Path(os.path.dirname(audio_path)).mkdir(parents=True, exist_ok=True)
            AudioSegment.silent(duration=int(est*1000), frame_rate=44100).export(audio_path, format="mp3")
            piece_files = []
        else:
            audio_path, piece_files = tts_elevenlabs_per_line(items, out_dir="output/audio", rate=args.rate)
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

    print("✅ Completed.")
    print("- Audio:   ", audio_path)
    print("- SRT:     output/subtitles/script.srt")
    print("- Plain:   output/subtitles_plain.txt")
    print("- JSON:    output/storyboard/pack.json")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--rate", type=float, default=1.0)
    ap.add_argument("--fake-tts", action="store_true", help="TTSをスキップして無音を生成（デバッグ用）")
    args=ap.parse_args()
    main(args)
