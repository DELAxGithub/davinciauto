# BGM Prompts (Mood / Tempo / Instruments)

## User
以下のセグメントのBGM方針をJSONで出力してください。説明やコードフェンスは禁止。

制約:
- mood は 2–4語の英語（例: mysterious, hopeful, warm, contemplative）
- tempo_bpm は整数（60–140）
- instruments は 2–5件（例: felt piano, airy pad, strings, soft percussion）
- intensity は 0.0–1.0 の小数（映像の強度感）
- tags は検索用の英語タグ 4–10語

出力形式:
{"music_prompts":[{"cue_id":"{SCENE_ID}","mood":"mysterious, hopeful","tempo_bpm":78,"instruments":["felt piano","airy pad"],"intensity":0.4,"tags":["cinematic","soft","ambient","warm"]}]}

テキスト:
{TEXT}
