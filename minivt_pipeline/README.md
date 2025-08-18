# Mini VTR Automation Pipeline (8-min 教養VTR)

このリポジトリは、**台本 → JSON一括出力 → TTS → 自動SRT → DaVinci取込**の半自動パイプライン骨格です。

## フロー
1. `pipeline.py` に台本 (`data/script.txt`) を投入
2. GPTでJSON一括生成
3. ElevenLabs TTSで音声生成
4. 自動字幕整形＋暫定タイムコードでSRT生成
5. DaVinci ResolveでSRTを自動取り込み
