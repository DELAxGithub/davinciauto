# AutoCut プロジェクト

Premiere Pro の文字起こし CSV とテンプレート XML をもとに、Google Sheets + GAS と Python で粗編集（ラフカット）を自動生成するツール群です。

含まれるファイル:
- `csv_premiere.js`: Google Apps Script（スプレッドシート用）。CSV 整形/抽出/書き出しの 3 ステップ UI を提供。
- `csv_xml_cutter.py`: Python スクリプト。テンプレート XML と最終 CSV を入力に、タイムライン XML を生成。
- `autocut_progress.md`: ワークフローの背景と進捗ノート。

使い方（概要）:
1. Premiere から対象シーケンスの「文字起こし CSV」と「テンプレート XML」を書き出す。
2. Google Sheets に CSV を貼付け、`csv_premiere.js` を（スクリプトエディタに貼り付けて）実行。
   - Step1: 整形 → Step2: 色抽出（必要なら並べ替え/空行） → Step3: 最終 CSV ダウンロード
3. Python で XML を生成:
   - GUI で選ぶ: `python projects/autocut/csv_xml_cutter.py` を実行して案内に従う
   - 直接指定: `python projects/autocut/csv_xml_cutter.py <final_csv> <template_xml>`

補足:
- 30fps 前提のタイムコード処理です。
- ギャップ（間）は 20 秒相当になるよう GAS 側でダミークリップ長を調整しています。

詳細は `projects/autocut/autocut_progress.md` を参照してください。

