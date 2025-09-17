#!/usr/bin/env python3
import csv
import os
import pathlib
from typing import Dict, List, Tuple


PROJECT = 'OrionEp2'
FPS = 30
PRE_ROLL = 0.50  # seconds

# Gap rules
BASE_GAP_NA = 0.35
BASE_GAP_DL = 0.60
SCENE_GAP = 1.80
QUESTION_BONUS = 0.30
LONG_TEXT_COEF = 0.004  # s per char
LONG_TEXT_MAX = 0.40


def mp3_duration_seconds(path: pathlib.Path, kbps: int = 128) -> float:
    # Estimate duration by file size and bitrate (assume CBR)
    try:
        size = path.stat().st_size
        return round((size * 8.0) / (kbps * 1000.0), 3)
    except Exception:
        return 0.0


def load_entries() -> List[Dict[str, str]]:
    # Consolidated line metadata for 1..63
    e1_27 = [
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
        {"num":"027","role":"NA","character":"NA","text":"紀元前5世紀、釈迦は「諸行無常」を説いたとされます。すべては流転し、同じものは二度とないという教えです。"},
    ]
    e28_63 = [
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
        {"num":"063","role":"NA","character":"NA","text":"どこにいても、どこへ行っても、星はいつも、あなたの居場所を照らしています。"},
    ]
    return e1_27 + e28_63


def compute_gap(role: str, text: str, is_scene_end: bool) -> float:
    role_u = (role or '').upper()
    base = BASE_GAP_DL if role_u in ('DL', 'Q', 'DIALOGUE') else BASE_GAP_NA
    bonus = 0.0
    if '？' in (text or '') or '?' in (text or ''):
        bonus += QUESTION_BONUS
    if text:
        bonus += min(LONG_TEXT_MAX, len(text) * LONG_TEXT_COEF)
    gap = base + bonus
    if is_scene_end:
        gap = max(gap, SCENE_GAP)
    return round(gap, 3)


def main() -> int:
    proj_dir = pathlib.Path('projects') / PROJECT
    audio_dir = proj_dir / 'サウンド類' / 'Narration'
    export_dir = proj_dir / 'exports' / 'timelines'
    export_dir.mkdir(parents=True, exist_ok=True)
    out_csv = export_dir / f'{PROJECT}_timeline_v1.csv'

    entries = load_entries()

    # Scene boundaries (apply SCENE_GAP after these line numbers)
    scene_end_nums = {
        '006',  # end of アバン
        '009',  # end of 星座の提示
        '015',  # end of 日常
        '024',  # end of 古代ギリシャ
        '033',  # end of 東洋の響き
        '039',  # end of 近代の病
        '045',  # end of 現代科学
        '051',  # end of 実践への架橋
        '056',  # end of 現代への帰還
        '063',  # end of エンディング (no next clip, but kept for clarity)
    }

    rows: List[Dict[str, str]] = []
    cur_time = PRE_ROLL
    for e in entries:
        num = e['num']
        role = e['role']
        character = e['character']
        text = e['text']
        fname = f"{PROJECT}-{num}-{role}.mp3"
        fpath = audio_dir / fname
        dur = mp3_duration_seconds(fpath)
        is_scene_end = num in scene_end_nums
        gap = compute_gap(role, text, is_scene_end)

        rows.append({
            'filename': str(fpath),
            'start_sec': f"{cur_time:.3f}",
            'duration_sec': f"{dur:.3f}",
            'role': role,
            'character': character,
            'text': text,
            'gap_after_sec': f"{gap:.3f}",
        })
        cur_time += dur + gap

    # Write CSV
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['filename','start_sec','duration_sec','role','character','text','gap_after_sec'])
        w.writeheader()
        w.writerows(rows)

    print(f'WROTE: {out_csv}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

