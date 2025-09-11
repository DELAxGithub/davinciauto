#!/usr/bin/env python3
"""
Generate ElevenLabs v3 TTS from pre-tagged (audio-tag) lines

Usage:
  python gui_steps/tts_from_tagged_text.py                 # use built-in sample
  python gui_steps/tts_from_tagged_text.py --in file.txt   # lines separated by blank lines
  python gui_steps/tts_from_tagged_text.py --out output/audio/tagged --prefix NAR-

Env:
  ELEVENLABS_API_KEY (required)
  ELEVENLABS_VOICE_ID_NARRATION (fallback voice ID)
"""
import os
import argparse
from pathlib import Path
from typing import List

# Allow importing enhanced client
import sys
try:
    from dotenv import load_dotenv as _load_dotenv  # optional
except Exception:
    def _load_dotenv(path=None):
        return False
from enhanced_tts_client import EnhancedTTSClient, TTSRequest, TTSError
from api_limiter import LimitMode

SAMPLE_LINES = [
    '<narration><emotional mood="pensive">転職した同期の投稿を見て、<break time="300ms"/>焦りを感じたことはありませんか？</emotional></narration>',
    '<narration><emotional mood="serious">転職は『脱出』なのか、<break time="400ms"/>それとも『逃避』なのか？</emotional></narration>',
    '<narration><emotional mood="wonder">古代の民の40年の放浪と、<break time="200ms"/>現代の哲学者の洞察から、<break time="400ms"/>本当の『約束の地』を見つける8分間の旅。</emotional></narration>',
    '<narration><emotional mood="calm">深夜0時。<break time="400ms"/>オフィスビルの窓に、まだポツポツと明かりが灯っています。</emotional></narration>',
    '<narration><emotional mood="pensive">その一室で、あなたはビジネス系SNSの画面を見つめている。<break time="500ms"/>元同期の転職報告。<break time="300ms"/>「新しいチャレンジ」「素晴らしい環境」——<break time="400ms"/>そんな言葉が並ぶ投稿に、「いいね！」を押しながら、<break time="300ms"/>胸の奥がざわつく。</emotional></narration>',
    '<narration><emotional mood="bittersweet">また一人、<break time="300ms"/>脱出に成功した。</emotional><sigh/></narration>',
    '<narration><emotional mood="mysterious">ようこそ、オリオンの会議室へ。<break time="500ms"/>ここは、時代を超えた知恵が交差する場所。<break time="500ms"/>今夜は「転職の約束」について、<break time="300ms"/>3000年の時を超えた対話を始めましょう。</emotional></narration>',
    '<narration><emotional mood="wonder">今夜結ぶのは、<break time="400ms"/>こんな星座。</emotional></narration>',
    '<narration><emotional mood="serious">エジプトから脱出した古代イスラエルの民、<break time="400ms"/>「神は死んだ」と宣言したニーチェ、<break time="400ms"/>組織論を研究する現代の学者たち、<break time="400ms"/>そして迷宮に閉じ込められたカフカの主人公——</emotional></narration>',
    '<narration><emotional mood="wonder">時代も場所も違う星々が、「脱出」と「約束」という糸で結ばれて、<break time="400ms"/>ひとつの物語を紡ぎ始めます。</emotional></narration>',
]


def load_lines_from_file(path: Path) -> List[str]:
    text = path.read_text(encoding='utf-8')
    blocks = []
    cur = []
    for line in text.splitlines():
        s = line.rstrip('\n')
        if not s.strip():
            if cur:
                blocks.append('\n'.join(cur).strip())
                cur = []
        else:
            cur.append(s)
    if cur:
        blocks.append('\n'.join(cur).strip())
    # Filter empties
    return [b for b in blocks if b]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', help='Input text (blocks separated by blank lines)')
    ap.add_argument('--out', dest='outdir', default='output/audio/tagged', help='Output folder')
    ap.add_argument('--prefix', dest='prefix', default='NAR-', help='Output filename prefix')
    ap.add_argument('--start', dest='start', type=int, default=1, help='Start index')
    args = ap.parse_args()

    # Load .env from typical locations
    try:
        # current repo root
        env_candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent / "minivt_pipeline" / ".env",
            Path(__file__).resolve().parent / ".env",
        ]
        for p in env_candidates:
            if p.exists():
                try:
                    _load_dotenv(p)
                except Exception:
                    # fallback: simple parse
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
                break
    except Exception:
        pass

    if args.infile:
        lines = load_lines_from_file(Path(args.infile))
    else:
        lines = SAMPLE_LINES

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Voice
    voice_id = os.getenv('ELEVENLABS_VOICE_ID_NARRATION', os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL'))

    # Client
    client = EnhancedTTSClient(LimitMode.DEVELOPMENT)

    print(f"Generating {len(lines)} files → {out_dir}")
    success = 0
    for i, text in enumerate(lines, start=args.start):
        out = out_dir / f"{args.prefix}{i:03d}.mp3"
        req = TTSRequest(text=text, voice_id=voice_id, output_file=str(out), speaker_type='NA', apply_pronunciation=False)
        def cb(msg: str):
            print(f"[{i:03d}] {msg}")
        res = client.generate_tts(req, cb)
        if res.success:
            success += 1
            print(f"✅ {out.name} ({res.duration_sec:.1f}s)")
        else:
            print(f"❌ {out.name}: {res.error_message}")

    print(f"Done. success={success}/{len(lines)}")


if __name__ == '__main__':
    try:
        main()
    except TTSError as e:
        print(f"TTS client error: {e}")
        print("Set ELEVENLABS_API_KEY and voice IDs in .env")
