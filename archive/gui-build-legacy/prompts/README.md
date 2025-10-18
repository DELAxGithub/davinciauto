# LLM Prompt Templates

用途別のプロンプト集です。System/Userのテンプレをそのままコピペして使えます。波括弧のプレースホルダを置き換えてください。

- narration_eleven_v3.md … ElevenLabs v3用の音声タグ付きナレーション生成
- subtitles_cards.md … 字幕カード分割（1カード=最大2行/各26文字・合計<=52、句読点は半角スペース）
- storyboard.md … 文字コンテ（outline/shotlist/keywords）
- bgm_prompts.md … BGMの気分・編成・テンポ指示
- telops_annotations.md … 情報・注釈テロップ候補抽出

変数例
- {TEXT}: セグメント本文
- {ROLE}: NA（ナレーション）/DL（セリフ）/QT
- {SPEAKER}: 話者名（DL時）
- {SCENE_ID}: 例 S001
- {MAX_LINE}: 行あたりの最大文字数（既定: 26）

出力整形
- JSON指定があるテンプレは、余計な説明なしでJSONのみを返すこと
- 句読点置換は「、」「。」→半角スペース（連続スペースは1つ）
