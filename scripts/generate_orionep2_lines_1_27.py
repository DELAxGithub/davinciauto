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

    # Script lines (1..27)
    entries: List[Dict[str, str]] = [
        {"num":"001","role":"NA","character":"NA","text":"リモートワークの実家も、久々のオフィスも、どこか居心地が悪いと感じたことはありませんか？"},
        {"num":"002","role":"NA","character":"NA","text":"「どこにも属せない」感覚は、喪失なのか、それとも解放なのか？"},
        {"num":"003","role":"NA","character":"NA","text":"10年の漂流を終えた英雄と、『ノスタルジア』という名の病、そして本当の『居場所』への8分間の旅。"},
        {"num":"004","role":"NA","character":"NA","text":"都心のカフェ。ノートPCを開く人々。隣のテーブルとの距離は1メートル。でも、心の距離は無限に遠い。"},
        {"num":"005","role":"NA","character":"NA","text":"「今日はどこで仕事する？」——この問いが日常になった時代。私たちは自由を手に入れたはずなのに、なぜか漂流している気がする。"},
        {"num":"006","role":"NA","character":"NA","text":"ようこそ、オリオンの会議室へ。今夜のテーマは「帰れない私たち」。"},
        {"num":"007","role":"NA","character":"NA","text":"今夜結ぶのは、こんな星座。"},
        {"num":"008","role":"NA","character":"NA","text":"10年の漂流を経験した英雄オデュッセウス、無常を説いた釈迦、19世紀に「ノスタルジア」を病名とした医師たち、失われた時を求めたプルースト——"},
        {"num":"009","role":"NA","character":"NA","text":"時代も大陸も越えた星々が、「帰属」という見えない糸で結ばれていきます。"},
        {"num":"010","role":"NA","character":"NA","text":"週に2日の出社日。久しぶりのオフィス。"},
        {"num":"011","role":"DL","character":"同僚A","text":"あれ、コピー機の場所、変わった？"},
        {"num":"012","role":"NA","character":"NA","text":"半年ぶりに会う同僚との会話が、どこかぎこちない。自分のデスクはあるけれど、もう「自分の場所」じゃない気がする。"},
        {"num":"013","role":"NA","character":"NA","text":"実家でのリモートワーク。子供の頃の部屋で仕事をしていると、大人なのか子供なのか、分からなくなる瞬間がある。"},
        {"num":"014","role":"DL","character":"母親","text":"お昼、何か作ろうか？"},
        {"num":"015","role":"NA","character":"NA","text":"優しさが、かえって居心地の悪さを生む。ここは故郷のはずなのに、もう帰る場所じゃないのかもしれない。"},
        {"num":"016","role":"NA","character":"NA","text":"紀元前8世紀、古代ギリシャ。盲目の詩人ホメロスが語る、ある英雄の物語。"},
        {"num":"017","role":"NA","character":"NA","text":"オデュッセウス。トロイア戦争の英雄は、故郷イタケへの帰路で10年もの歳月を費やしました。"},
        {"num":"018","role":"NA","character":"NA","text":"嵐、怪物、魔女。次々と現れる障害。でも、本当にそれは「障害」だったのでしょうか？"},
        {"num":"019","role":"NA","character":"NA","text":"美しい女神カリュプソの島で7年。魔女キルケーの館で1年。オデュッセウスは、なぜそんなに長く留まったのか。"},
        {"num":"020","role":"DL","character":"オデュッセウス","text":"私は故郷を恋い慕う。だが、この冒険もまた、私の一部となった"},
        {"num":"021","role":"NA","character":"NA","text":"帰りたい。でも、帰りたくない。この矛盾した感情を、ホメロスは2700年前に描いていました。"},
        {"num":"022","role":"NA","character":"NA","text":"冒険の中で、オデュッセウスは変わってしまった。もう、出発した時の自分ではない。そして故郷イタケも、10年の間に変わっているはずです。"},
        {"num":"023","role":"NA","character":"NA","text":"ついに帰還を果たした時、妻のペーネロペーは彼を認識できませんでした。彼もまた、成長した息子テレマコスを見て戸惑います。"},
        {"num":"024","role":"NA","character":"NA","text":"帰ってきたのに、帰ってきていない。場所には戻れても、時間は戻せない。"},
        {"num":"025","role":"NA","character":"NA","text":"地球の反対側、古代インドでも、似た洞察が生まれていました。"},
        {"num":"026","role":"DL","character":"釈迦","text":"諸行は無常なり。これ生滅の法なり"},
        {"num":"027","role":"NA","character":"NA","text":"紀元前5世紀、釈迦は「諸行無常」を説いたとされます。すべては流転し、同じものは二度とないという教えです。"}
    ]

    # Decide voice for each entry (explicit mapping wins)
    def resolve_voice_id(role: str, character: str) -> str:
        role = (role or '').strip().upper()
        character = (character or '').strip()
        if character in characters:
            return characters[character]
        if role in default_role:
            return default_role[role]
        return default_role.get('NA') or characters.get('内なる声') or characters.get('同僚A')

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
        # filename: OrionEp2-###-ROLE.mp3 (project-wide MP3 only)
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
