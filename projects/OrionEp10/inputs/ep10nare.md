# GeminiTTS向けナレーション＆セリフスクリプト
## オリオンの会議室 第10話「カリスマはもういらない」

```yaml
# =============================================================================
# GeminiTTS Production Script
# Episode: 第10話「カリスマはもういらない」
# Total Duration: ~8:00
# =============================================================================

metadata:
  title: "オリオンの会議室 第10話「カリスマはもういらない」"
  episode: 10
  duration: "00:08:35"
  tts_engine: "gemini-2.5-flash-preview-tts"
  default_voice: "kore"

# =============================================================================
# Scene 1: アバン (00:00 - 01:00)
# =============================================================================
scenes:
  - scene_id: 1
    name: "アバン"
    timecode: "00:00:00 - 00:01:00"
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          あの人がいなくなったら終わりだ<break time="1500ms"/>そんな不安を抱えたことはありませんか？<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          この依存は<break time="600ms"/><sub alias="けんぜん">健全</sub>な敬意なのか<break time="600ms"/>それとも組織の脆弱性なのか？<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          ようこそ<break time="600ms"/><sub alias="おりおん">オリオン</sub>の会議室へ<break time="700ms"/>今夜のテーマは<break time="600ms"/>カリスマはもういらない<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          古今東西の<sub alias="えいち">叡智</sub>を星座のように結び<break time="600ms"/>現代の悩みに新しい視座を見つける8分間<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          今夜の星々<break time="1500ms"/><sub alias="にじゅっせいき">20世紀</sub>ドイツの社会学者が分析した<break time="600ms"/>カリスマ的支配の構造<break time="600ms"/>古代マケドニアの大王死後に起きた<break time="600ms"/>帝国分裂の教訓<break time="600ms"/><sub alias="にじゅっせいき">20世紀</sub>社会思想の<break time="600ms"/>脱魔術化の視座<break time="600ms"/>そして現代の複雑系科学が示す<break time="600ms"/>集合知による創発が<break time="600ms"/>一人の天才に頼らない組織の物語を紡ぎ始めます<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 2: 日常への没入 (01:00 - 01:30)
# =============================================================================
  - scene_id: 2
    name: "日常への没入"
    timecode: "00:01:00 - 00:01:30"
    scene_transition: true  # 3000ms break
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          ある中堅メーカーの取締役会<break time="700ms"/>
          </speak>

      - speaker: "専務"
        voice: "gacrux"
        emotion: "困惑して"
        style_prompt: "Deliver in a calm, senior male voice with quiet authority and subtle concern."
        ssml: |
          <speak>
          <break time="120ms"/>会長がいたら<break time="600ms"/>きっとNOと言うはずだ<break time="30ms"/>
          </speak>

      - speaker: "常務"
        voice: "aoede"
        emotion: "ため息"
        style_prompt: "Sound like a slightly nervous but earnest young professional trying to respond politely."
        ssml: |
          <speak>
          <break time="120ms"/>でも<break time="600ms"/>会長ならどうやって解決したか<break time="600ms"/>誰にも分からない<break time="30ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          創業者が築いた暗黙知<break time="600ms"/>属人的なネットワーク<break time="600ms"/>言語化されない判断基準<break time="700ms"/>それらは彼と共に消えてしまった<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          新入社員研修では<break time="600ms"/>今も創業者の<break time="120ms"/>語録<break time="30ms"/>が配られる<break time="700ms"/>でも<break time="600ms"/>時代は変わり<break time="600ms"/>市場も変わった<break time="700ms"/>金言が足枷になっていることに<break time="600ms"/>誰も気づかない<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 3: ウェーバーの分析 (01:30 - 03:00)
# =============================================================================
  - scene_id: 3
    name: "ウェーバーの分析"
    timecode: "00:01:30 - 00:03:00"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          <sub alias="にじゅっせいき">20世紀</sub>初頭のドイツ<break time="700ms"/>社会学者マックス<break time="400ms"/>ウェーバーは<break time="600ms"/>支配の三類型を提示しました<break time="700ms"/>伝統的支配<break time="600ms"/>合法的支配<break time="600ms"/>そして<break time="1500ms"/>カリスマ的支配<break time="700ms"/>
          </speak>

      - speaker: "ウェーバー"
        voice: "kore"
        emotion: "分析的に"
        style_prompt: "Speak in a steady, composed male voice with quiet strength, as though quoting a timeless principle with deep respect."
        ssml: |
          <speak>
          <break time="120ms"/>カリスマとは<break time="600ms"/>ある個人が非凡だと信じられ<break time="600ms"/>超常的<break time="400ms"/>特別な力を帯びるとみなされることに由来する支配の正統性である<break time="30ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          出典<break time="500ms"/>マックス<break time="400ms"/>ウェーバー<break time="600ms"/><break time="120ms"/>経済と社会<break time="1500ms"/>支配の社会学<break time="30ms"/><break time="600ms"/>1922年<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          重要なのは<break time="600ms"/><break time="120ms"/>信じられた<break time="30ms"/>という部分<break time="700ms"/>カリスマは<break time="600ms"/>実際の能力ではなく<break time="600ms"/>人々の信仰という社会的事実によって成立する<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          ウェーバーが指摘した<break time="600ms"/><break time="120ms"/>カリスマの日常化<break time="30ms"/>という問題<break time="700ms"/>カリスマは必ず死ぬ<break time="700ms"/>その後<break time="600ms"/>組織はカリスマの<break time="120ms"/>遺産<break time="30ms"/>を制度化しようとする<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          しかし<break time="600ms"/>カリスマの本質は非日常性<break time="700ms"/>それを日常化した瞬間<break time="600ms"/>形骸化が始まるとウェーバーは指摘しました<break time="700ms"/>創業者の革新性が<break time="600ms"/>後継者の保守性に変わっていく皮肉<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          さらにウェーバーは<break time="600ms"/>近代化とは<break time="120ms"/>脱魔術化<break time="30ms"/>のプロセスだと説きました<break time="700ms"/>神秘やカリスマではなく<break time="600ms"/>合理性と制度による統治への移行<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          でも現代の私たちは<break time="600ms"/>むしろカリスマを渇望している<break time="700ms"/>不確実性が高まるほど<break time="600ms"/>確実な何かにすがりたくなる<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 4: アレクサンドロスの教訓 (03:00 - 04:00)
# =============================================================================
  - scene_id: 4
    name: "アレクサンドロスの教訓"
    timecode: "00:03:00 - 00:04:00"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          <sub alias="きげんぜんごひゃくねん">紀元前323年</sub><break time="600ms"/>バビロン<break time="700ms"/>32歳のアレクサンドロス大王が急死しました<break time="700ms"/>10年でペルシャからインドまで征服した英雄<break time="700ms"/>彼の個人的カリスマが<break time="600ms"/>巨大帝国を一つにまとめていました<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          死の床で後継者を問われ<break time="600ms"/>彼は<break time="120ms"/>最も優れた者に<break time="30ms"/>と言ったという説も伝えられています<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          出典<break time="500ms"/>プルタルコス<break time="600ms"/><break time="120ms"/>英雄伝<break time="30ms"/><break time="600ms"/>1<break time="400ms"/>から<break time="400ms"/>2<sub alias="せいき">世紀</sub><break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          この曖昧な遺言が<break time="600ms"/>帝国の崩壊を招きました<break time="700ms"/>後継者たちによる長い戦乱の時代<break time="600ms"/>ディアドコイ戦争が始まり<break time="600ms"/>帝国は分裂<break time="700ms"/>カリスマなき後の混乱の典型例です<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          興味深いのは<break time="600ms"/>分裂した王国の中で最も長く続いたのが<break time="600ms"/>官僚制と財政制度を整備したプトレマイオス朝エジプトだったこと<break time="700ms"/>カリスマではなく<break time="600ms"/>システムを作った者が生き残ったのです<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 5: 日本的文脈——空虚な中心 (04:00 - 05:00)
# =============================================================================
  - scene_id: 5
    name: "日本的文脈——空虚な中心"
    timecode: "00:04:00 - 00:05:00"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          1970年代<break time="600ms"/>日本の構造をめぐる議論が活発になりました<break time="700ms"/>心理学者の河合隼雄は<break time="600ms"/><break time="120ms"/>中空構造日本の深層<break time="30ms"/>で<break time="600ms"/>日本文化のユニークな特徴を読み解きました<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          日本の統合は<break time="600ms"/><break time="120ms"/>中心が空<break time="30ms"/>である構造に支えられ<break time="600ms"/>その中空が周縁の均衡を生む<break time="1500ms"/>と述べています<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          同様の視点は<break time="600ms"/>フランスの記号学者ロラン<break time="400ms"/>バルトも<break time="600ms"/><break time="120ms"/>表徴の帝国<break time="30ms"/>で示唆しています<break time="700ms"/>彼が論じたのは<break time="600ms"/>皇居という東京の中心が<break time="120ms"/>空虚<break time="30ms"/>であることの象徴性でした<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          この<break time="120ms"/>空虚な中心<break time="30ms"/>という考え方は<break time="600ms"/>一人の強力なリーダーが全体を率いる西洋的なカリスマ支配とは異なる統治原理を示唆します<break time="700ms"/>中心が空だからこそ<break time="600ms"/>周縁が自律的に動ける余地が生まれるというのです<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 6: 複雑系とネットワーク (05:00 - 06:00)
# =============================================================================
  - scene_id: 6
    name: "複雑系とネットワーク"
    timecode: "00:05:00 - 00:06:00"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          <sub alias="にじゅういっせいき">21世紀</sub>のネットワーク科学は<break time="600ms"/>カリスマ組織と似た構造を発見しました<break time="700ms"/>スケールフリーネットワークです<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          ネットワークの研究では<break time="600ms"/><break time="120ms"/>スケールフリー<break time="30ms"/>という型が知られています<break time="700ms"/>ごく少数の<break time="120ms"/>要<break time="30ms"/>が<break time="600ms"/>全体の流れを左右しやすいというものです<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          出典<break time="500ms"/>バラバシ<break time="600ms"/><break time="120ms"/>新ネットワーク思考<break time="30ms"/><break time="600ms"/>2002年<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          そして<break time="600ms"/>頼りどころを一か所に集めない作りにしておくと<break time="600ms"/>どこかが止まっても全体は動き続けやすいことが示されています<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          インターネットも<break time="600ms"/>特定の親玉に任せきりにしない考え方で育ってきました<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          また<break time="600ms"/>生物学の世界では<break time="120ms"/>群知能<break time="600ms"/>スワームインテリジェンス<break time="30ms"/>が研究されています<break time="700ms"/>例えば<break time="600ms"/>渡り鳥の群れのように<break time="600ms"/>明確なリーダーがいなくても全体として高度な秩序を保つ例は自然界に多く見られます<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 7: 実践への架橋 (06:00 - 07:00)
# =============================================================================
  - scene_id: 7
    name: "実践への架橋"
    timecode: "00:06:00 - 00:07:00"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          では<break time="600ms"/>カリスマ後の組織はどうあるべきか<break time="700ms"/>ウェーバーの答えは<break time="120ms"/>合理的<break time="400ms"/>合法的支配<break time="30ms"/>でした<break time="700ms"/>ルールと制度による統治<break time="700ms"/>でも<break time="600ms"/>それだけでは官僚主義の罠に陥る<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          複雑系が示すのは<break time="120ms"/>適応的ガバナンス<break time="30ms"/><break time="700ms"/>状況に応じてリーダーが入れ替わり<break time="600ms"/>組織構造も柔軟に変化する<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="120ms"/>空虚な中心<break time="30ms"/>という考え方も示唆的です<break time="700ms"/>強い個人ではなく<break time="600ms"/>強い<break time="120ms"/>場<break time="30ms"/>を作る<break time="700ms"/>その場から<break time="600ms"/>創発的にリーダーシップが生まれる<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          カリスマを卒業するとは<break time="600ms"/>依存を卒業すること<break time="700ms"/>一人一人が小さな主体性を持ち<break time="600ms"/>それが連鎖して大きな動きを作る<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 8: 現代への帰還 (07:00 - 07:30)
# =============================================================================
  - scene_id: 8
    name: "現代への帰還"
    timecode: "00:07:00 - 00:07:30"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          月曜日の経営会議<break time="700ms"/>創業者の肖像画は<break time="600ms"/>まだ壁にある<break time="700ms"/>でも<break time="600ms"/>視線はもう違う<break time="700ms"/>
          </speak>

      - speaker: "専務"
        voice: "gacrux"
        emotion: "決意を込めて"
        style_prompt: "Deliver in a calm, senior male voice with quiet authority and subtle concern."
        ssml: |
          <speak>
          <break time="120ms"/>会長ならどうしたか<break time="600ms"/>ではなく<break time="600ms"/>我々がどうすべきか<break time="600ms"/>ですね<break time="30ms"/>
          </speak>

      - speaker: "若手"
        voice: "aoede"
        emotion: "提案"
        style_prompt: "Sound like a slightly nervous but earnest young professional trying to respond politely."
        ssml: |
          <speak>
          <break time="120ms"/>各部門からボトムアップで戦略を<break time="900ms"/><break time="30ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          創業者への敬意は変わらない<break time="700ms"/>でも<break time="600ms"/>もう亡霊に縛られない<break time="700ms"/>彼が残した精神を<break time="600ms"/>新しい形で実現していく<break time="700ms"/>
          </speak>

# =============================================================================
# Scene 9: エンディング (07:30 - 08:35)
# =============================================================================
  - scene_id: 9
    name: "エンディング"
    timecode: "00:07:30 - 00:08:35"
    scene_transition: true
    segments:
      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          <break time="3000ms"/>
          夜空を見上げると<break time="600ms"/><sub alias="おりおん">オリオン</sub>座が輝いています<break time="700ms"/>偉大な狩人の星座<break time="700ms"/>でも<break time="600ms"/>それは複数の星が偶然作り出したパターン<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          カリスマもまた<break time="600ms"/>私たちが投影した物語かもしれません<break time="700ms"/>その物語から自由になった時<break time="600ms"/>星々はそれぞれの光で輝き始める<break time="700ms"/>
          </speak>

      - speaker: "ナレーター"
        voice: "kore"
        style_prompt: "知的で落ち着いたドキュメンタリー調のナレーション"
        ssml: |
          <speak>
          知識の星座は<break time="600ms"/>見る人によって違う物語を紡ぎます<break time="700ms"/>あなたは明日<break time="600ms"/>創業者の影を越えて<break time="600ms"/>どんな一歩を踏み出しますか？<break time="1500ms"/>
          </speak>

# =============================================================================
# Production Notes
# =============================================================================
production_notes:
  - "全編Gemini TTS (gemini-2.5-flash-preview-tts) で生成"
  - "デフォルトナレーター声: kore"
  - "配役: 専務=gacrux, 常務/若手=aoede, ウェーバー=kore"
  - "シーン転換時は3000msのbreakを挿入"
  - "引用符の前後に短いbreak (120ms/30ms) を挿入"
  - "pronunciation_hintsに基づき<sub>タグで発音指定"
  - "句読点に応じたbreak時間を適用"
```

---

## 使用上の注意（Gemini TTS全編版）

### 使用する音声

| 役名 | Gemini TTS Voice | 性格・用途 |
|------|------------------|-----------|
| ナレーター | kore | デフォルト。知的で落ち着いたドキュメンタリー調 |
| 専務 | gacrux | 低めで威厳のある男性声。静かな権威と懸念 |
| 常務/若手 | aoede | 若い専門職。やや緊張しながらも真摯に対応 |
| ウェーバー | kore | 重厚で知的な語り（孫子スタイルに準拠） |

### SSML記法のポイント

- `<break time="XXXms"/>`: ポーズ挿入
- `<sub alias="よみがな">漢字</sub>`: 発音指定
- `<speak>...</speak>`: SSMLブロック
- シーン転換: 3000ms break
- 引用符: 開始120ms / 終了30ms
- 句読点: yaml設定に準拠（、=600ms, 。=700ms, ？=800ms等）
