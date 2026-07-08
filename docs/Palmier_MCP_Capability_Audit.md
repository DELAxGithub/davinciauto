# Palmier MCP Capability Audit

更新日: 2026-06-20

## 目的

Palmier Proでできることのうち、`davinciauto` のDoc/CSV -> DaVinci自動反映へ取り込む価値があるものを判定する。

この文書は競合分析ではなく、商用AI編集ソフトのMCP設計から、実写ポスプロ自動化に効く設計原則と検証テーマだけを抽出するためのメモ。

## Evidence Source

- 対象repo: `/tmp/palmier-pro`
- Git commit: `abf3326aedf7b417f5d9c0fc8807b3d7d881126f`
- GitHub HEADと一致確認済み
- 主な参照ファイル:
  - `Sources/PalmierPro/Agent/Tools/ToolDefinitions.swift`
  - `Sources/PalmierPro/Agent/Tools/AgentInstructions.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+Clips.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+Timeline.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+InspectTimeline.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+Search.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+Texts.swift`
  - `Sources/PalmierPro/Agent/Tools/ToolExecutor+Captions.swift`
  - `Sources/PalmierPro/Agent/MCP/MCPService.swift`

注意: Palmier ProはGPLv3。ここではコードや実装細部を移植せず、能力カテゴリ、設計原則、検証観点だけを抽出する。

## Decision Rules

- `今すぐ採用`: EP40のDoc -> IR -> 新規タイムライン生成を安全に強くするもの
- `V1検証`: 価値は高いが、Resolve API/MCPで実現性確認が必要なもの
- `参考のみ`: UXやagent運用として参考になるが、EP40 V0には不要なもの
- `捨てる`: 現在の事業価値、費用感、実写ポスプロ用途から外れるもの

## Capability Matrix

| Palmier capability | Palmier source evidence | Editor value | davinciauto / Resolve equivalent | 判定 | Reason and next action |
|---|---|---|---|---|---|
| Timeline state read | `ToolDefinitions.swift`, `ToolExecutor+Timeline.swift`, `AgentInstructions.swift` | 編集前にfps、track、clip状態を共有できる | Resolve MCP/CLIのtimeline-info、`desired_timeline_ir` | 今すぐ採用 | EP40 V0でも必須。操作前に状態を読み、IRと照合する前提を維持する |
| Frame-only timing contract | `AgentInstructions.swift`, `ToolDefinitions.swift` | 秒/timecode混在によるズレを防ぐ | `scripts/doc_to_davinci_ir.py` と設計書のframe契約 | 今すぐ採用 | timecode -> frame変換をIR生成時の1回に閉じ込める |
| Media/library state | `get_media`, folder/import tools in `ToolDefinitions.swift` | 素材IDを安定参照し、外部素材を取り込める | Resolve Media Pool、素材ファイルパス、将来のmanifest | V1検証 | EP40 V0では素材は固定WAV中心。将来は素材manifestを作る |
| Batch clip placement | `add_clips`, `ToolExecutor+Clips.swift` | 複数clipを1回の編集単位として配置できる | IRからFCPXML/Resolve scriptで新規timeline生成 | 今すぐ採用 | 既存TLを直接触らず、新規timeline案としてまとめて生成する |
| Clear-before-place overwrite | `add_clips` behavior in `ToolExecutor+Clips.swift` | 再実行時の二重配置を避ける | Resolve既存TLでは危険。新規生成なら不要 | V1検証 | 既存TLへのreconcileでのみ検証。V0には入れない |
| Linked A/V movement | `move_clips`, `set_clip_properties`, `ToolExecutor+Clips.swift` | 映像と音声の同期を維持できる | A1/A2同一source range配置 | V1検証 | EP40ではA1/A2を同じIR rangeで扱う。Resolve linked behaviorは別途確認 |
| Ripple delete ranges | `ripple_delete_ranges`, related tests | フィラー語/無音/不要範囲を一括で詰められる | プラっとのカット/隙間詰め、Resolve script | V1検証 | 価値は高いが既存TL破壊リスクがある。複製timelineで検証する |
| Transcript-driven editing | `inspect_media`, `get_transcript`, `search_media` | 発話内容から該当範囲を探して切れる | Google Doc文字起こし、SRT、将来のword timestamp | V1検証 | プラっとに重要。Doc文字起こしとResolve timeline transcriptの対応表を検証する |
| Visual timeline inspection | `inspect_timeline`, `OverviewRenderer.swift` | 編集後の見た目をagentが確認できる | Resolve screenshot/render確認、timeline thumbnail | V1検証 | V0はレポートまで。V1でResolveから静止画検証を足す |
| Text and captions | `add_texts`, `add_captions`, `ToolExecutor+Texts.swift`, `ToolExecutor+Captions.swift` | 字幕/テロップをタイムラインに自動配置できる | DaVinci subtitle track、SRT import、telop scripts | V1検証 | Doc->字幕/テロップ反映の価値あり。API制限を確認する |
| Agent instruction discipline | `AgentInstructions.swift` | agentの自由編集を小さな操作単位に制限できる | Codex/Resolve運用手順、docs設計規律 | 今すぐ採用 | read-before-write、frame契約、失敗後だけ再読込を運用ルール化する |
| In-app chat and mention UX | Agent panel/mention files | 編集対象をUIで参照しやすい | 現状はCodex/Claude外部運用 | 参考のみ | UI開発の優先度は低い。将来Commander側で参考にする |
| Media folders and organization | folder tools in `ToolDefinitions.swift` | 生成物/素材を整理できる | Resolve bins、project folders | 参考のみ | EP40自動反映の主戦場ではない。素材manifest整備後に再評価 |
| AI generation/upscale | `generate_*`, `upscale_media`, `list_models` | editor内で生成素材を作って置ける | 外部生成物のimport、現状は低優先 | 捨てる | 月額/API費用と用途が合わない。実写ポスプロ自動化では優先しない |

## EP40への反映

EP40 V0へ入れるもの:

- `get_timeline`相当のread-before-write
- frame-only timing
- Doc/CSVからの安定IR
- batch placementを前提にした新規timeline生成
- 限界レポート

EP40 V1で検証するもの:

- transcript-driven cut
- Resolve上のvisual inspection
- subtitle/text placement
- safe ripple behavior
- 既存timelineへの限定reconcile

EP40では捨てるもの:

- editor内の有料生成AIワークフロー
- in-app agent UIそのものの再実装

## 次の検証タスク

1. EP39/EP40形式CSVから生成したIRを、Resolveの複製timelineへ配置する最小実験を作る。
2. A1/A2同期、record frame、source frameが一致しているかレポートで確認する。
3. transcript-driven cutは、Doc文字起こしと実timeline transcriptの対応表が作れるかを先に検証する。
4. visual inspectionは、Resolveから代表frameを書き出してIRの意図と照合できるかを検証する。
