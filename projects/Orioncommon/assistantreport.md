### 1\) シリーズ俯瞰（要約）

  * **全体テーマ要約（300–400字）**
    本シリーズ『オリオンの会議室』は、現代ビジネスパーソンが直面する普遍的な悩みに対し、古代ギリシャ、ローマ、中国、さらには近代哲学や現代科学といった時代と場所を超えた知恵の「星座」を結びつけ、新たな視座を提供する知的探求プログラムである。各話は「転職」「孤独」「習慣」などの身近なテーマを入り口に、歴史上の偉人や思想家の洞察を紐解き、単なるノウハウではない、より根源的な思考のフレームワークを提示する。視聴者は8分間の思索の旅を通じて、日々の課題を乗り越えるための内なる羅針盤を見出すことを目的とする。

  * **シリーズで多用すべき統制タグ TOP10（理由つき1行ずつ）**

    1.  `S:夜景` - シリーズ全体のトーンである「深夜の思索」を象徴する基本背景。
    2.  `M:星空` - 「知の星座を結ぶ」という中心的な比喩表現を視覚化する最重要モチーフ。
    3.  `M:ネットワーク` - 思想や概念の「繋がり」を抽象的に表現するPlexusエフェクトの素材。
    4.  `E:孤独` - 現代人の悩みの根源にある感情。視聴者の共感を促す導入のキートーン。
    5.  `M:窓` - 内面（悩み）と外面（世界）を繋ぐ境界のメタファーとして多用。
    6.  `S:社内` - 現代の悩みが生まれる主戦場。リアルな共感性を担保する舞台設定。
    7.  `M:書物` - 古代の知恵や歴史的背景を象徴するビジュアルの基本要素。羊皮紙も含む。
    8.  `T:歴史` - 各話の論拠となる過去の思想家や出来事を示すための必須カテゴリ。
    9.  `C:望遠` - 都市の孤独感や客観的な視点を表現する上で効果的なカメラワーク。
    10. `E:静寂` - 思考が深まる瞬間や、ナレーションに集中させるための空間を演出する。

### 2\) 各話の「まずやること」チェックリスト（EP01〜EP13）

```json
{
 "episode": "EP01",
 "logline": "転職は『脱出』か『逃避』か？古代イスラエルの民の放浪から、本当の『約束の地』を見出す旅。",
 "core_tags": ["S:夜景", "M:窓", "E:孤独", "T:組織", "M:砂丘"],
 "first_actions": [
  "冒頭アバン、ナレに『深夜オフィスの窓（望遠/孤独）』を12秒あて、シリーズのトーンを確立する。",
  "星座提示パートに『星空＋ネットワークPlexus（低密度/青）』を15秒尺で確保、テンプレ化する。",
  "古代パートの導入に『砂丘/荒野の空撮（C:空撮）』を挟み、現代からの時間的飛躍を明確にする。"
 ],
 "smartbin_queries": [
  {"name": "孤独な夜のオフィス", "condition": "S:夜景 AND S:社内 AND (M:窓 OR E:孤独)"},
  {"name": "知の星座（抽象線）", "condition": "M:ネットワーク OR M:脳HUD"},
  {"name": "古代の風景（砂漠）", "condition": "S:自然 AND M:砂丘 AND C:空撮"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "単窓のみ点灯する高層ビル", "count": 2, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "SNS画面のスクロール（ボケ）", "count": 1, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "荒野を歩く人々のシルエット（遠景）", "count": 2, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "orion constellation timelapse minimal dark",
  "office window night telephoto lonely businessman",
  "desert caravan silhouette aerial drone sunset"
 ],
 "risks": [
  "宗教的人物（モーセ）の顔は直接描写せず、光や杖、羊皮紙などで示唆する。",
  "字幕の可読性：青基調のネットワーク映像を優先し、白背景は避ける。"
 ]
}
```

```json
{
 "episode": "EP02",
 "logline": "リモートワーク時代の「帰れない」感覚。英雄オデュッセウスの漂流から本当の『居場所』を問う。",
 "core_tags": ["S:社内", "M:海", "E:孤独", "T:自己", "C:空撮"],
 "first_actions": [
  "冒頭アバン、カフェや自宅でのリモート風景に『心の距離』を示すフォーカス送り（C:マクロ）を多用する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "古代ギリシャパートへの転換に、『嵐の海（C:空撮）』を挟み、オデュッセウスの漂流を象徴させる。"
 ],
 "smartbin_queries": [
  {"name": "漂流・航海", "condition": "M:海 AND (C:空撮 OR S:自然)"},
  {"name": "孤独なリモートワーク", "condition": "S:屋内 AND E:孤独 AND (M:窓 OR A:読書)"},
  {"name": "古代ギリシャの象徴", "condition": "S:寺社 OR M:羊皮紙 OR T:歴史"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "嵐の中の帆船（CG/VFX）", "count": 1, "seconds_each": 12, "priority": "A"},
  {"need": "ブリッジ", "motif": "古い地図の上を移動する光点", "count": 2, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "灯台の光が回転する（夜）", "count": 1, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "ancient greek ship storm sea 3d animation",
  "lonely man working from home cafe window rain",
  "lighthouse beam night dark ocean"
 ],
 "risks": [
  "「ノスタルジア」の表現で、過度に感傷的なセピア調映像は避け、現代的なカラーグレーディングで統一する。",
  "神話の怪物は直接描写せず、波や影で暗示するに留める。"
 ]
}
```

```json
{
 "episode": "EP03",
 "logline": "炎上プロジェクトで動じない上司の秘密。ローマ皇帝の『自省録』から、内なる平静を保つ術を学ぶ。",
 "core_tags": ["S:社内", "E:静寂", "T:倫理", "M:書物", "A:会議"],
 "first_actions": [
  "日常パートの炎上描写は、高速TL（C:TL）と手持ちカメラ（C:パン）で混乱を表現し、部長の固定カット（C:固定）と対比させる。",
  "星座提示パートはEP01のテンプレを使用する。",
  "古代ローマパートへの転換には、『インクが羊皮紙に染みる（C:マクロ）』映像を使い、思索への没入感を示す。"
 ],
 "smartbin_queries": [
  {"name": "混乱したオフィス", "condition": "S:社内 AND A:会議 AND (C:TL OR C:パン)"},
  {"name": "執筆・思索", "condition": "M:書物 AND M:インク AND (A:筆記 OR C:マクロ)"},
  {"name": "ローマ/ストア哲学", "condition": "S:寺社 AND T:歴史 AND (E:静寂 OR M:光芒)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "戦場のテント内で日記を書く手元（再現）", "count": 1, "seconds_each": 12, "priority": "A"},
  {"need": "ブリッジ", "motif": "コーヒーカップの湯気が立ち上る（C:スロモ）", "count": 2, "seconds_each": 8, "priority": "A"},
  {"need": "象徴カット", "motif": "荒波が岩に当たるも岩は動かない（固定）", "count": 1, "seconds_each": 10, "priority": "B"}
 ],
 "istock_queries": [
  "stoic roman emperor writing diary tent candlelight",
  "chaotic office meeting timelapse stress",
  "steam rising from coffee cup slow motion dark"
 ],
 "risks": [
  "「アパテイア」の誤解を避けるため、無表情ではなく「内なる静けさ」を感じさせる俳優・モデルの映像を選ぶ。",
  "東西思想の比較パートでは、安易なオリエンタリズムに陥らないよう、インドの風景は象徴的に使用する。"
 ]
}
```

```json
{
 "episode": "EP04",
 "logline": "パワハラと寛容の境界線とは？暴君ネロに仕えたセネカの哲学から、真の『優しさと厳しさ』を探る。",
 "core_tags": ["S:社内", "A:会議", "T:倫理", "E:苦悩", "M:群集"],
 "first_actions": [
  "冒頭アバン、「言葉を飲み込む」表現として、口元のアップとフォーカスアウトを効果的に使用する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "心理実験パートは、モノクロや低彩度の映像で再現し、客観的・科学的なトーンを演出する。"
 ],
 "smartbin_queries": [
  {"name": "緊張感のある会議", "condition": "S:社内 AND A:会議 AND E:苦悩"},
  {"name": "群集心理", "condition": "M:群集 AND (C:俯瞰 OR C:TL)"},
  {"name": "古代ローマの権力", "condition": "T:歴史 AND (S:寺社 OR M:群集)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "一人だけ違う方向を向いている群衆の中の人物", "count": 1, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "天秤が揺れ動く（C:マクロ）", "count": 2, "seconds_each": 6, "priority": "B"},
  {"need": "再現映像", "motif": "心理実験風の被験者の表情（困惑）", "count": 3, "seconds_each": 8, "priority": "A"}
 ],
 "istock_queries": [
  "tense business meeting conflict silence",
  "conformity psychology experiment vintage look",
  "roman senator nero court intrigue"
 ],
 "risks": [
  "セネカとネロの関係は、単純な善悪二元論で描かず、権力構造の複雑さを示唆する構図（玉座を見上げる、など）を選ぶ。",
  "孔子の「仁」のパートは、中国の伝統的映像に寄りすぎず、普遍的な人間関係の映像で表現する。"
 ]
}
```

```json
{
 "episode": "EP05",
 "logline": "SNSの「頑張ってる投稿」への焦燥感。老子の『無為自然』から、頑張らずに成果を出す逆説の知恵を学ぶ。",
 "core_tags": ["S:自然", "M:竹林", "E:静寂", "T:自己", "M:脳HUD"],
 "first_actions": [
  "日常パートのアジャイル開発の描写は、ホワイトボードの付箋が増えるTL（C:TL）で「空回りする努力」を表現する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "古代中国パートは、『水が岩を避けて流れる（C:マクロ/スロモ）』映像をキービジュアルとして使用し、「無為」を視覚化する。"
 ],
 "smartbin_queries": [
  {"name": "老荘思想・禅", "condition": "S:自然 AND E:静寂 AND (M:竹林 OR M:禅庭)"},
  {"name": "フロー体験", "condition": "A:筆記 OR (M:脳HUD AND T:脳科学)"},
  {"name": "空回りする努力", "condition": "S:社内 AND C:TL AND A:会議"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "川の流れ、水の流れ（ドローン/マクロ）", "count": 3, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "深呼吸する人物の横顔（スロモ）", "count": 2, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "オフィス街の公園で空を見上げる人", "count": 1, "seconds_each": 12, "priority": "A"}
 ],
 "istock_queries": [
  "taoism water flowing around rocks drone",
  "zen garden bamboo forest serene calm",
  "flow state brain activity HUD animation"
 ],
 "risks": [
  "「頑張らない」が「怠惰」と誤解されないよう、映像はリラックスしつつも知的・創造的な雰囲気のものを選ぶ。",
  "物理学のパートは、CGやHUDを多用しすぎず、自然現象の美しい実写映像を主体に構成する。"
 ]
}
```

```json
{
 "episode": "EP06",
 "logline": "エース社員はなぜ孤立するのか？最強の戦士アキレウスの孤独から、個と集団の最適なバランスを探る。",
 "core_tags": ["S:社内", "E:孤独", "T:組織", "M:群鳥", "C:俯瞰"],
 "first_actions": [
  "冒頭、飲み会に向かう同僚たちをガラス越しに見送るエース社員の構図で、「見えない壁」を表現する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "古代ギリシャパート、アキレウスの強さは一人で多数を相手にする戦闘シーン（ただし抽象的に）で、孤独さは一人きりの野営シーンで対比させる。"
 ],
 "smartbin_queries": [
  {"name": "孤立したエース", "condition": "S:社内 AND E:孤独 AND (C:望遠 OR M:窓)"},
  {"name": "群れの調和", "condition": "M:群鳥 OR M:群集 AND (C:俯瞰 OR C:空撮)"},
  {"name": "古代の戦闘（象徴）", "condition": "T:歴史 AND (C:スロモ OR M:光芒)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "群鳥の murmuration（統率された動き）", "count": 1, "seconds_each": 15, "priority": "A"},
  {"need": "ブリッジ", "motif": "綱引きで一人だけ力が入りすぎている（比喩）", "count": 1, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "オーケストラの指揮者と演奏者たち", "count": 2, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "starling murmuration aerial drone sunset",
  "isolated successful businessman looking out window office",
  "ancient greek hero achilles solitary camp"
 ],
 "risks": [
  "アキレウスの戦闘シーンは、暴力性を強調せず、様式美やスローモーションを使い「神話的な強さ」として表現する。",
  "リンゲルマン効果の綱引き実験は、文字通りの再現ではなく、比喩的な映像（歯車が噛み合わない、など）も検討する。"
 ]
}
```

```json
{
 "episode": "EP07",
 "logline": "会議の前に結論が決まっている『根回し』。非効率な悪習か、日本の叡智か。孫子や千利休からその本質を読み解く。",
 "core_tags": ["A:会議", "S:社内", "T:組織", "M:禅庭", "S:寺社"],
 "first_actions": [
  "冒頭アバン、淡々と進む会議の様子を固定カメラ（C:固定）で撮影し、裏のダイナミズムとの対比を際立たせる。",
  "星座提示パートはEP01のテンプレを使用する。",
  "東洋パート、孫子は竹簡や水墨画風のアニメーション、千利休は茶室や禅庭の静かな映像で表現する。"
 ],
 "smartbin_queries": [
  {"name": "根回し・交渉", "condition": "S:社内 AND A:握手 AND NOT A:会議"},
  {"name": "日本の伝統美", "condition": "M:禅庭 OR S:寺社 OR M:竹林"},
  {"name": "形式的な会議", "condition": "A:会議 AND C:固定 AND E:静寂"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "茶室のにじり口から入るシーン（象徴）", "count": 1, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "将棋や囲碁の駒を置く手元（C:マクロ）", "count": 2, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "水面下の水鳥の足の動き（見えない努力）", "count": 1, "seconds_each": 12, "priority": "A"}
 ],
 "istock_queries": [
  "japanese tea ceremony room serene empty",
  "sun tzu art of war bamboo scroll animation",
  "pre-meeting handshake secret deal office corridor"
 ],
 "risks": [
  "「根回し」をネガティブなだけで描かない。調和や事前準備のポジティブな側面も示唆する映像（円滑な握手など）を混ぜる。",
  "高コンテクスト/低コンテクスト文化の比較では、特定の国を戯画化しないよう、抽象的なイメージ映像を主とする。"
 ]
}
```

```json
{
 "episode": "EP08",
 "logline": "なぜ朝活は続かない？アリストテレスの『中庸』と禅の『守破離』から、画一的な習慣の呪いを解き放つ。",
 "core_tags": ["T:自己", "T:時間", "M:砂時計", "S:自然", "T:脳科学"],
 "first_actions": [
  "冒頭、二度寝のシーンは主観視点とスローモーションで罪悪感を表現する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "時間生物学のパートでは、ヒバリとフクロウの映像を対比的に使い、「クロノタイプ」の概念を分かりやすく示す。"
 ],
 "smartbin_queries": [
  {"name": "朝活・自己啓発", "condition": "A:読書 OR S:屋外 AND (T:自己 OR T:時間)"},
  {"name": "体内時計・クロノタイプ", "condition": "T:脳科学 AND (M:砂時計 OR T:時間)"},
  {"name": "禅・守破離", "condition": "S:寺社 OR M:禅庭 OR M:インク"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "朝日を浴びるヒバリと、夜の森のフクロウの対比", "count": 1, "seconds_each": 12, "priority": "A"},
  {"need": "ブリッジ", "motif": "様々なデザインの時計が異なる速度で回る（TL）", "count": 2, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "自分のペースで走るランナー（集団ではない）", "count": 1, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "chronotype biological clock animation brain",
  "lark bird sunrise and owl bird night forest",
  "breaking the mold abstract concept shattered glass"
 ],
 "risks": [
  "フーコーの規律訓練のパートは、監視カメラや工場の映像を使いすぎると陰謀論的に見えるため、自己啓発書の山など、より身近な素材で「見えない権力」を示唆する。",
  "特定の習慣（朝活）を全否定するのではなく、「多様性」を肯定するトーンの映像を選ぶ。"
 ]
}
```

```json
{
 "episode": "EP09",
 "logline": "コンプライアンスは完璧、でも息苦しい。プラトンの理想国家とオーウェルの警告から、『正しい会社』の幻想を問う。",
 "core_tags": ["T:組織", "T:倫理", "E:苦悩", "S:社内", "M:群集"],
 "first_actions": [
  "冒頭アバン、分厚いマニュアルと、それを読む社員の疲れた表情を対比させるカットで問題提起する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "プラトンの理想国家とル・コルビュジエの都市は、CGや設計図、画一的な建物の空撮で「完璧だが人間味のない」雰囲気を表現する。"
 ],
 "smartbin_queries": [
  {"name": "管理社会・ディストピア", "condition": "M:群集 AND C:俯瞰 AND (S:社内 OR S:夜景)"},
  {"name": "無機質な建築", "condition": "S:夜景 AND C:空撮 AND NOT S:自然"},
  {"name": "アリの巣・群知能", "condition": "M:ネットワーク OR (C:マクロ AND S:自然)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "画一的な団地やビル群の空撮（C:空撮/俯瞰）", "count": 2, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "ハンコが次々と押される書類（C:TL）", "count": 1, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "巣の中で働くアリと働かないアリ（C:マクロ）", "count": 1, "seconds_each": 12, "priority": "A"}
 ],
 "istock_queries": [
  "dystopian society uniform crowd marching cctv",
  "brutalist architecture aerial drone cold concrete",
  "ant colony macro working lazy ants"
 ],
 "risks": [
  "『1984』の描写は、プロパガンダ映像風の加工を施し、フィクションであることを明確にする。",
  "企業のコンプライアンス自体を否定する印象を与えないよう、「人間味」とのバランスを問うニュアンスの映像を選ぶ。"
 ]
}
```

```json
{
 "episode": "EP10",
 "logline": "カリスマ創業者亡き後の組織の停滞。ウェーバーの分析とアレクサンドロス大王の死から、『カリスマ後の時代』を考える。",
 "core_tags": ["T:組織", "T:歴史", "M:群集", "E:孤独", "M:ネットワーク"],
 "first_actions": [
  "冒頭、神棚のように飾られた創業者の肖像画と、それを見上げる現在の役員たちの困惑した表情を対比させる。",
  "星座提示パートはEP01のテンプレを使用する。",
  "ウェーバーの分析パートでは、「カリスマ」「伝統」「合法」を象徴する映像（預言者風の人物、王冠、法典）をテンポよく見せる。"
 ],
 "smartbin_queries": [
  {"name": "カリスマと群衆", "condition": "M:群集 AND E:高揚 AND NOT A:会議"},
  {"name": "システムの歯車", "condition": "S:社内 AND C:俯瞰 AND T:組織"},
  {"name": "分散型ネットワーク", "condition": "M:ネットワーク AND NOT M:脳HUD"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "中心のない鳥の群れ（群知能）", "count": 1, "seconds_each": 12, "priority": "A"},
  {"need": "ブリッジ", "motif": "古い肖像画に埃が積もっている（C:マクロ）", "count": 1, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "崩れ落ちる砂の城", "count": 1, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "charismatic leader speech crowd adoring",
  "decentralized network animation no central hub",
  "alexander the great death empire collapse map animation"
 ],
 "risks": [
  "河合隼雄の「空虚な中心」論は非常に抽象的なため、皇居など具体的な映像と、禅庭の円相など象徴的な映像を組み合わせて補足する。",
  "特定のカリスマ経営者（ジョブズ等）の映像は権利関係が複雑なため、一般的な「リーダー」のシルエット映像などで代替する。"
 ]
}
```

```json
{
 "episode": "EP11",
 "logline": "専門性を深めるべきか、視野を広げるべきか。ダ・ヴィンチの万能性とマキャヴェリの戦略から、キャリアの最適解を探る。",
 "core_tags": ["T:自己", "T:組織", "M:羅針盤", "A:筆記", "S:図書館"],
 "first_actions": [
  "冒頭アバン、デスクに並ぶ専門書と教養書の間で迷う人物の手元をアップで撮り、選択の葛藤を象徴させる。",
  "星座提示パートはEP01のテンプレを使用する。",
  "ダ・ヴィンチのパートでは、彼の手稿（解剖図、機械設計図）をモーショングラフィックスで動かし、知の越境性をダイナミックに見せる。"
 ],
 "smartbin_queries": [
  {"name": "知の探求", "condition": "S:図書館 OR M:書物 OR A:読書"},
  {"name": "ダヴィンチの手稿", "condition": "M:羊皮紙 AND A:筆記 AND T:歴史"},
  {"name": "キャリアの岐路", "condition": "M:羅針盤 OR (S:自然 AND T:自己)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "ダ・ヴィンチ手稿のモーショングラフィックス", "count": 1, "seconds_each": 15, "priority": "A"},
  {"need": "ブリッジ", "motif": "螺旋階段を上から見下ろす（C:俯瞰）", "count": 2, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "ダーウィンフィンチのくちばしの違いが分かる図解/CG", "count": 1, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "leonardo da vinci notebook animation anatomy machine",
  "career crossroads signpost fork in the road",
  "lion and fox concept strategic thinking"
 ],
 "risks": [
  "「T型人材」などのビジネス用語を図解する際は、陳腐なテンプレートは避け、本編のトーンに合わせたミニマルなデザインで作成する。",
  "獅子と狐の比喩は、実際の動物の映像を使いすぎると教育番組っぽくなるため、あくまで象徴的に短く使用する。"
 ]
}
```

```json
{
 "episode": "EP12",
 "logline": "瞑想アプリのスコアに感じる違和感。般若心経の『空』と現代の批判から、数値化できない価値と向き合う。",
 "core_tags": ["T:自己", "E:静寂", "S:自然", "T:脳科学", "M:禅庭"],
 "first_actions": [
  "冒頭アバン、瞑想アプリのUIと、瞑想しようと苦闘する人物の表情を交互に見せ、テクノロジーと内面のギャップを表現する。",
  "星座提示パートはEP01のテンプレを使用する。",
  "般若心経のパートでは、文字の映像ではなく、水面にインクが一滴落ちて消えていく様など、「空」をイメージさせる映像を用いる。"
 ],
 "smartbin_queries": [
  {"name": "瞑想・静寂", "condition": "E:静寂 AND (S:自然 OR M:禅庭 OR S:寺社)"},
  {"name": "マインドフルネスアプリ", "condition": "T:脳科学 OR (C:マクロ AND T:自己)"},
  {"name": "脳科学イメージ", "condition": "M:脳HUD OR M:ネットワーク"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "水面に落ちる一滴の雫と広がる波紋（C:スロモ）", "count": 2, "seconds_each": 10, "priority": "A"},
  {"need": "ブリッジ", "motif": "スマホ画面の通知が次々と表示される（C:TL）", "count": 1, "seconds_each": 8, "priority": "B"},
  {"need": "象徴カット", "motif": "オフィスビルの屋上で空を眺める人", "count": 1, "seconds_each": 12, "priority": "A"}
 ],
 "istock_queries": [
  "meditation app interface user screen stress score",
  "ink drop in water slow motion black and white",
  "zen buddhism monk meditating temple serene"
 ],
 "risks": [
  "マインドフルネス産業批判のパートで、特定のアプリや企業を攻撃するような印象にならないよう、あくまで「傾向」として論じる。",
  "脳科学のパートは、科学的効果を謳いすぎるのではなく、「測定できるもの」と「できないもの」の対比を主軸に構成する。"
 ]
}
```

```json
{
 "episode": "EP13",
 "logline": "MBAを取得したのに、なぜ決断できない？哲学者カントの『物自体』から、知識の限界と向き合う勇気を学ぶ。",
 "core_tags": ["M:書物", "S:図書館", "E:苦悩", "T:倫理", "M:星空"],
 "first_actions": [
  "冒頭アバン、膨大な資料と空白のモニタースライドを対比させ、「知識の飽和」状態を視覚的に示す。",
  "星座提示パートは、中心にカントを置き、周囲を他の星が回るような特別なモーショングラフィックスを作成する。",
  "カントのパートでは、「我が上なる星空」の言葉に合わせ、壮大な星空のタイムラプス映像を挿入し、畏敬の念を表現する。"
 ],
 "smartbin_queries": [
  {"name": "分析麻痺", "condition": "E:苦悩 AND S:社内 AND (M:書物 OR A:会議)"},
  {"name": "カント・哲学", "condition": "M:星空 AND T:倫理 AND (M:書物 OR A:歩行)"},
  {"name": "禅・不立文字", "condition": "M:インク AND (M:禅庭 OR S:寺社)"}
 ],
 "cut_requirements": [
  {"need": "決め絵", "motif": "圧倒的な星空のタイムラプス（天の川）", "count": 2, "seconds_each": 12, "priority": "A"},
  {"need": "ブリッジ", "motif": "霧の中の道、先が見えない風景", "count": 2, "seconds_each": 10, "priority": "B"},
  {"need": "象徴カット", "motif": "月を指す指、そして月にパンするカメラ", "count": 1, "seconds_each": 10, "priority": "A"}
 ],
 "istock_queries": [
  "immanuel kant philosopher concept animation",
  "milky way timelapse desert night sky stunning",
  "analysis paralysis businessman overwhelmed data charts"
 ],
 "risks": [
  "カントの哲学は非常に難解なため、「物自体」と「現象」の違いを、コーヒーカップの例のように身近で具体的なビジュアルで補足する。",
  "カーネマンの実験は、数字のグラフだけでなく、自信満々な専門家と不安げな素人の表情の対比で、心理的な側面を強調する。"
 ]
}
```

### 3\) スマートビン定義（シリーズ共通・Power Bins）

```csv
Name;Condition
S-夜景;Keywords contains "S:夜景"
S-社内;Keywords contains "S:社内"
S-自然;Keywords contains "S:自然"
M-星空;Keywords contains "M:星空"
M-ネットワーク;Keywords contains "M:ネットワーク"
M-書物;Keywords contains "M:書物"
M-窓;Keywords contains "M:窓"
A-会議;Keywords contains "A:会議"
E-孤独;Keywords contains "E:孤独"
E-静寂;Keywords contains "E:静寂"
C-空撮;Keywords contains "C:空撮"
C-俯瞰;Keywords contains "C:俯瞰"
C-望遠;Keywords contains "C:望遠"
C-TL;Keywords contains "C:TL"
T-歴史;Keywords contains "T:歴史"
T-組織;Keywords contains "T:組織"
T-自己;Keywords contains "T:自己"
INT-孤独な夜のオフィス;All: "S:夜景","S:社内" Any: "M:窓","E:孤独"
INT-中央の空白会議;All: "A:会議","C:俯瞰" Any: "S:社内"
INT-知の星座;Any: "M:ネットワーク","M:脳HUD"
INT-思索・執筆;Any: "M:書物","M:インク","A:筆記","S:図書館"
INT-禅・静寂;Any: "M:禅庭","M:竹林","S:寺社","E:静寂"
```

### 4\) 自動タグ付けインポート用 CSV（ドラフト）

```csv
Source File,Keywords,Comments
[未確定_後で差替],"S:夜景; S:社内; M:窓; C:望遠; E:孤独","EP01_導入_孤独なオフィス"
[未確定_後で差替],"M:星空; M:ネットワーク; C:パン","EP01_OP_星座提示"
[未確定_後で差替],"S:自然; M:砂丘; C:空撮; E:孤独","EP01_古代パート_放浪"
[未確定_後で差替],"M:書物; M:インク; C:マクロ","EP01_哲学者パート_ニーチェ"
[未確定_後で差替],"S:社内; A:会議; C:固定","EP01_現代パート_月曜の朝"
[未確定_後で差替],"S:屋内; E:孤独; A:読書","EP02_導入_リモートワーク"
[未確定_後で差替],"S:自然; M:海; C:空撮","EP02_古代パート_オデュッセウス"
[未確定_後で差替],"S:寺社; E:静寂; T:歴史","EP02_東洋パート_釈迦"
[未確定_後で差替],"M:脳HUD; T:脳科学","EP02_科学パート_fMRI"
[未確定_後で差替],"S:社内; A:歩行; E:静寂","EP02_現代パート_オフィス出社"
[未確定_後で差替],"S:社内; A:会議; C:TL; E:苦悩","EP03_導入_炎上プロジェクト"
[未確定_後で差替],"M:書物; M:羊皮紙; A:筆記; T:歴史","EP03_古代パート_自省録"
[未確定_後で差替],"S:寺社; M:光芒; E:静寂","EP03_ストア派パート"
[未確定_後で差替],"C:スロモ; E:静寂","EP03_結末_コーヒーの湯気"
[未確定_後で差替],"S:社内; A:会議; E:苦悩","EP04_導入_言えない本音"
[未確定_後で差替],"T:歴史; S:寺社; E:苦悩","EP04_古代パート_セネカ"
[未確定_後で差替],"M:群集; C:俯瞰","EP04_心理実験パート_同調"
[未確定_後で差替],"A:握手; S:社内","EP04_結末_対話の始まり"
[未確定_後で差替],"S:社内; C:TL; A:会議","EP05_導入_空回り"
[未確定_後で差替],"S:自然; M:竹林; E:静寂","EP05_東洋パート_老子"
[未確定_後で差替],"M:脳HUD; T:自己; E:高揚","EP05_科学パート_フロー体験"
[未確定_後で差替],"S:自然; A:歩行; E:静寂","EP05_結末_散歩"
[未確定_後で差替],"S:社内; M:窓; E:孤独; C:望遠","EP06_導入_孤立したエース"
[未確定_後で差替],"T:歴史; C:スロモ; E:高揚","EP06_古代パート_アキレウス"
[未確定_後で差替],"M:群鳥; C:空撮; C:俯瞰","EP06_科学パート_群知能"
[未確定_後で差替],"S:社内; A:握手; E:静寂","EP06_結末_和解"
[未確定_後で差替],"A:会議; C:固定; S:社内","EP07_導入_形式的な会議"
[未確定_後で差替],"M:禅庭; S:寺社; E:静寂","EP07_東洋パート_千利休"
[未確定_後で差替],"M:地図; T:歴史","EP07_西洋パート_マキャベリ"
[未確定_後で差替],"A:会議; T:組織","EP07_結末_透明な根回し"
[未確定_後で差替],"T:時間; M:砂時計; E:苦悩","EP08_導入_二度寝"
[未確定_後で差替],"S:自然; C:TL","EP08_科学パート_クロノタイプ"
[未確定_後で差替],"S:図書館; M:書物; E:苦悩","EP08_フーコーパート_規律"
[未確定_後で差替],"T:自己; S:屋外; E:静寂","EP08_結末_自分のペース"
[未確定_後で差替],"S:社内; M:書物; E:苦悩","EP09_導入_息苦しい規則"
[未確定_後で差替],"M:群集; C:俯瞰; T:歴史","EP09_古代パート_理想国家"
[未確定_後で差替],"C:マクロ; S:自然; M:ネットワーク","EP09_科学パート_アリの巣"
[未確定_後で差替],"A:会議; T:組織; E:静寂","EP09_結末_不完全さの受容"
[未確定_後で差替],"S:社内; T:歴史; E:孤独","EP10_導入_創業者の肖像"
[未確定_後で差替],"M:群集; E:高揚; T:歴史","EP10_古代パート_アレクサンドロス"
[未確定_後で差替],"M:ネットワーク; C:パン","EP10_科学パート_分散型"
[未確定_後で差替],"A:会議; T:組織","EP10_結末_カリスマ後"
[未確定_後で差替],"S:図書館; M:書物; A:読書; E:苦悩","EP11_導入_キャリアの迷い"
[未確定_後で差替],"M:羊皮紙; A:筆記; T:歴史","EP11_ルネサンスパート_ダヴィンチ"
[未確定_後で差替],"S:自然; T:自己","EP11_科学パート_適応放散"
[未確定_後で差替],"A:会議; S:社内; T:自己","EP11_結末_螺旋的キャリア"
[未確定_後で差替],"S:屋内; T:自己; E:苦悩","EP12_導入_瞑想アプリ"
[未確定_後で差替],"S:寺社; M:インク; E:静寂","EP12_東洋パート_般若心経"
[未確定_後で差替],"M:脳HUD; T:脳科学","EP12_科学パート_功罪"
[未確定_後で差替],"S:屋外; S:夜景; E:静寂","EP12_結末_ただ座る"
[未確定_後で差替],"S:社内; M:書物; C:TL; E:苦悩","EP13_導入_分析麻痺"
[未確定_後で差替],"M:星空; C:TL; T:倫理","EP13_哲学パート_カント"
[未確定_後で差替],"T:脳科学; E:苦悩","EP13_科学パート_知識の呪い"
[未確定_後で差替],"A:会議; S:社内; T:倫理","EP13_結末_小さく始める"
```

### 5\) 追加購入の即応リスト（各話 上位3件）

  * EP01：単窓点灯ビル（望遠/夜）／ 砂漠のキャラバン（空撮/シルエット）／ Plexusネットワーク（青/低密度）
  * EP02：古代ギリシャの帆船（嵐の海/CG）／ 灯台の光（回転/夜）／ 古地図上の移動アニメーション
  * EP03：ローマ皇帝の執筆（テント/再現）／ コーヒーの湯気（スロー/黒背景）／ 荒波と岩（固定/動かない）
  * EP04：群衆の中の孤独な人物（逆光）／ 心理実験風の表情（困惑/モノクロ）／ 天秤の揺れ（マクロ）
  * EP05：川の流れ（岩を避ける/マクロ）／ フロー状態の脳HUD（アニメーション）／ 竹林の光（静寂）
  * EP06：ムクドリの群れ（murmuration/空撮）／ オーケストラの調和（俯瞰）／ オフィスでの孤立（ガラス越し）
  * EP07：茶室のにじり口（象徴）／ 囲碁・将棋を打つ手（マクロ）／ 水面下の水鳥の足（比喩）
  * EP08：ヒバリ（朝日）とフクロウ（夜）の対比映像／ 様々な時計のTL／ 自分のペースで走る人（単独）
  * EP09：画一的なビル群（空撮/冷たい色調）／ アリの巣（働くアリと怠けるアリ/マクロ）／ 監視カメラの映像（ディストピア風）
  * EP10：群知能（中心のない鳥や魚の群れ）／ 崩れる砂の城（スロー）／ カリスマ的リーダーと群衆（高揚感）
  * EP11：ダヴィンチ手稿のモーショングラフィックス／ 螺旋階段（俯瞰）／ ダーウィンフィンチの図解CG
  * EP12：水面に落ちるインク（スロー/無）／ 瞑想アプリUIのアニメーション／ オフィスの屋上で空を見上げる人
  * EP13：天の川のタイムラプス（高精細）／ 霧の中の道（先が見えない）／ 月を指す指から月へのパン