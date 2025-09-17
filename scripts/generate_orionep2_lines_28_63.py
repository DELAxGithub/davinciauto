#!/usr/bin/env python3
import os
import json
import pathlib
import sys
from typing import Dict, List


def load_env_key() -> str | None:
    k = os.getenv('ELEVENLABS_API_KEY')
    if k:
        return k
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for raw in f:
                s = raw.strip()
                if not s or s.startswith('#'):
                    continue
                if s.startswith('ELEVENLABS_API_KEY='):
                    v = s.split('=', 1)[1].strip().strip('"').strip("'")
                    if '#' in v:
                        v = v.split('#', 1)[0].strip()
                    return v
    except Exception:
        return None
    return None


def main() -> int:
    api_key = load_env_key()
    if not api_key:
        print('ERROR: ELEVENLABS_API_KEY not found', file=sys.stderr)
        return 2
    try:
        from elevenlabs import ElevenLabs
    except Exception as e:
        print('ERROR: elevenlabs SDK not available:', e, file=sys.stderr)
        return 3

    proj = pathlib.Path('projects/OrionEp2')
    cfg_path = proj / 'project.json'
    if not cfg_path.exists():
        print(f'ERROR: missing {cfg_path}', file=sys.stderr)
        return 4
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    model_id = cfg.get('model_id', 'eleven_v3')
    output_format = cfg.get('output_format', 'mp3_44100_128')
    cast = cfg.get('voice_cast', {})
    default_role = cast.get('default_role', {})
    characters: Dict[str, str] = cast.get('characters', {})

    # Lines 028..063
    entries: List[Dict[str, str]] = [
        {"num":"028","role":"NA","character":"NA","text":"仏教の「無常観」は、執着からの解放を説きます。「元に戻る」という幻想を手放すこと。それが苦しみから逃れる道だと。すべてのものは移り変わり、永遠に同じ状態に留まるものは何一つない——この真理を受け入れることから、真の安らぎが生まれると説いたのです。"},
        {"num":"029","role":"NA","character":"NA","text":"興味深いことに、古代ギリシャでも、似た洞察が生まれていました。"},
        {"num":"030","role":"NA","character":"NA","text":"紀元前6世紀の哲学者ヘラクレイトスは「万物流転」を説きました。"},
        {"num":"031","role":"DL","character":"ヘラクレイトス","text":"同じ川に二度入ることはできない。川も変わり、入る者も変わる"},
        {"num":"032","role":"NA","character":"NA","text":"西の哲学者と東の覚者。時代も場所も異なる二人が、それぞれの方法で同じ真理に辿り着いていた。人は誰も、同じ場所に帰ることはできない。なぜなら、場所も自分も、常に変化し続けているから。"},
        {"num":"033","role":"NA","character":"NA","text":"釈迦は瞑想を通じてこの真理を体得し、ヘラクレイトスは理性的な観察からこの結論に至った。アプローチは違えど、両者が見つめていたのは、変化こそが世界の本質だという、深遠な事実だったのです。"},
        {"num":"034","role":"NA","character":"NA","text":"17世紀のスイス。若い傭兵たちが、故郷を離れて原因不明の病に倒れていたと記録されています。"},
        {"num":"035","role":"NA","character":"NA","text":"医師ヨハネス・ホーファーは、この症状に「ノスタルジア」という名前を付けます。ギリシャ語の「nostos（帰郷）」と「algos（痛み）」を組み合わせた造語でした。"},
        {"num":"036","role":"NA","character":"NA","text":"当時は本当の「病気」として扱われ、処方箋は「故郷への帰還」でした。"},
        {"num":"037","role":"NA","character":"NA","text":"でも19世紀になると、精神科医たちは気づきます。患者が恋い慕っているのは、実在する故郷ではなく、記憶の中の理想化された故郷だと。"},
        {"num":"038","role":"NA","character":"NA","text":"20世紀、マルセル・プルーストは『失われた時を求めて』で、この感覚を文学に昇華させました。"},
        {"num":"039","role":"NA","character":"NA","text":"紅茶に浸したマドレーヌの香りが呼び起こす、幼少期の記憶。でもそれは、過去そのものではなく、現在の意識が再構築した過去でした。"},
        {"num":"040","role":"NA","character":"NA","text":"21世紀の脳科学が、この謎を解き明かし始めています。"},
        {"num":"041","role":"NA","character":"NA","text":"fMRIで観察すると、懐かしい場所の写真を見た時、海馬と前頭前皮質が同時に活性化します。記憶の想起と、現在の認知が混ざり合う瞬間。"},
        {"num":"042","role":"NA","character":"NA","text":"カナダの地理学者エドワード・レルフは「場所への愛着」を研究し、物理的な場所と心理的な場所は別物だと証明しました。"},
        {"num":"043","role":"NA","character":"NA","text":"私たちが「帰りたい」と思う場所は、GPS座標で示せる場所ではなく、記憶と感情が作り出した心象風景なのです。"},
        {"num":"044","role":"NA","character":"NA","text":"リモートワーク研究のデータによると、「どこでも働ける」自由を得た人ほど、帰属意識の喪失を訴える傾向が見られるという報告があります。"},
        {"num":"045","role":"NA","character":"NA","text":"自由と引き換えに、私たちは「居場所」を失ったのかもしれません。"},
        {"num":"046","role":"NA","character":"NA","text":"では、どこにも属せない感覚とどう向き合えばいいのでしょうか。"},
        {"num":"047","role":"NA","character":"NA","text":"オデュッセウスの物語が教えてくれるのは、「帰還」ではなく「再会」という視点です。"},
        {"num":"048","role":"NA","character":"NA","text":"変わってしまった自分と、変わってしまった場所が、新しく出会い直す。それは「元に戻る」ことではなく、「新しく始める」こと。"},
        {"num":"049","role":"NA","character":"NA","text":"仏教の無常観は、変化を嘆くのではなく、変化そのものを人生の本質として受け入れることを説きます。"},
        {"num":"050","role":"NA","character":"NA","text":"場所論が示すのは、物理的な場所に縛られない、新しい帰属の形。それは特定の座標ではなく、人との関係性の中に見出される「居場所」。"},
        {"num":"051","role":"NA","character":"NA","text":"週2日のオフィス出社も、実家でのリモートワークも、カフェでのノマドワークも——それぞれが「仮の宿」。でも、その仮の宿を転々としながら、私たちは新しい物語を紡いでいく。"},
        {"num":"052","role":"NA","character":"NA","text":"月曜日の朝。今日はオフィス出社の日。"},
        {"num":"053","role":"NA","character":"NA","text":"エレベーターで会った同僚と、ちょっとした会話。それは以前とは違うけれど、悪くない。むしろ、新鮮な発見がある。"},
        {"num":"054","role":"NA","character":"NA","text":"デスクに座って、ノートPCを開く。画面に映るのは、先週実家で作業していたファイル。場所は変わっても、仕事は続いている。"},
        {"num":"055","role":"DL","character":"内なる声","text":"ここも、あそこも、全部が私の場所"},
        {"num":"056","role":"NA","character":"NA","text":"完全な帰属はもうないかもしれない。でも、部分的な帰属をいくつも持つことはできる。それは不安定さではなく、しなやかさかもしれない。"},
        {"num":"057","role":"NA","character":"NA","text":"夜空を見上げると、オリオン座が輝いています。"},
        {"num":"058","role":"NA","character":"NA","text":"3000年前の船乗りも、この同じ星を見ていました。星は動かない。でも、見る人の場所によって、見える角度は変わる。"},
        {"num":"059","role":"NA","character":"NA","text":"オデュッセウスの10年の旅は、単なる回り道ではありませんでした。それは、「帰る」ために必要な、自分自身の変容の時間だったのです。"},
        {"num":"060","role":"NA","character":"NA","text":"現代の私たちの「漂流」も、もしかしたら、新しい帰属の形を見つけるための、必要な旅なのかもしれません。"},
        {"num":"061","role":"NA","character":"NA","text":"知識の星座は、見る人によって違う物語を紡ぎます。"},
        {"num":"062","role":"NA","character":"NA","text":"あなたは今夜、どんな星座を見つけましたか？"},
        {"num":"063","role":"NA","character":"NA","text":"どこにいても、どこへ行っても、星はいつも、あなたの居場所を照らしています。"}
    ]

    def resolve_voice_id(role: str, character: str) -> str:
        role = (role or '').strip().upper()
        character = (character or '').strip()
        if character in characters:
            return characters[character]
        if role in default_role:
            return default_role[role]
        return default_role.get('NA') or characters.get('内なる声')

    out_dir = proj / 'サウンド類' / 'Narration'
    out_dir.mkdir(parents=True, exist_ok=True)

    client = ElevenLabs(api_key=api_key)

    saved: list[str] = []
    errors: list[tuple[str, str]] = []

    for e in entries:
        num = e['num']
        role = e['role']
        character = e['character']
        text = e['text']
        vid = resolve_voice_id(role, character)
        fname = f"OrionEp2-{num}-{role}.mp3"
        fpath = out_dir / fname
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id=vid,
                model_id=model_id,
                output_format=output_format,
            )
            with open(fpath, 'wb') as f:
                if isinstance(audio, (bytes, bytearray)):
                    f.write(audio)
                else:
                    for chunk in audio:
                        if isinstance(chunk, (bytes, bytearray)):
                            f.write(chunk)
            saved.append(str(fpath))
        except Exception as ex:
            errors.append((fname, str(ex)))

    print('SAVED:')
    for p in saved:
        print(p)
    if errors:
        print('ERRORS:')
        for n, err in errors:
            print(n, err)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

