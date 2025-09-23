# ElevenLabs MCP Server 統合ガイド

> **Legacy Notice**: The active TTS pipeline now targets Azure Speech Service. ElevenLabs MCP integration is optional/legacy and should only be used for archival workflows.

## 🎯 統合完了

**✅ ElevenLabs MCP サーバーが正常に統合されました！**

Claude Code で ElevenLabs の高度なTTS機能を直接使用できるようになりました。

---

## 🚀 セットアップ手順

### 1. パッケージインストール完了
```bash
pip install elevenlabs-mcp  # ✅ 完了
```

### 2. 設定ファイル作成完了
- `mcp-config.json` - MCPサーバー設定
- 出力パス: `minivt_pipeline/output`
- API Key: 環境変数から自動取得

### 3. 統合テスト完了
```bash
python test_elevenlabs_mcp.py  # ✅ 全テスト通過
```

---

## 🎵 利用可能なMCP機能

### 🎤 基本TTS機能
- **`text_to_speech`** - テキスト→音声変換
- **`search_voices`** - 音声ライブラリ検索
- **`get_voice`** - 特定音声の詳細取得

### 🎭 高度な機能
- **`text_to_voice`** - 音声プレビュー生成（3バリエーション）
- **`create_voice_instant_clone`** - インスタント音声クローニング
- **`transform_voice`** - 音声変換（既存→別音声）
- **`transcribe_audio`** - 音声→テキスト変換

### 📊 管理機能
- **`check_subscription`** - API使用量・制限確認
- **`list_voices`** - 音声ライブラリ一覧

---

## 🖥️ GUI統合の実装方針

### **サイドバー制作フロー統合**
```javascript
// ステップ2: 音声生成でMCP活用
async function generateAudioMCP(text, voiceType) {
    // Claude Code MCP経由で音声生成
    const response = await callClaudeCodeMCP({
        tool: 'text_to_speech',
        text: text,
        voice_id: voiceType === 'narration' ?
            'ELEVENLABS_VOICE_ID_NARRATION' :
            'ELEVENLABS_VOICE_ID_DIALOGUE'
    });
    return response;
}
```

### **リアルタイムプレビュー**
- **音声プレビュー**: `text_to_voice` で3バリエーション生成
- **音声検索**: `search_voices` で最適な声優検索
- **インスタントクローン**: ユーザー音声のリアルタイムクローニング

---

## 💡 活用シナリオ

### 1. **既存パイプライン強化**
```python
# minivt_pipeline/src/pipeline.py と併用
# MCP: 高品質音声生成
# 既存: バッチ処理・字幕同期
```

### 2. **GUI ワークフロー自動化**
```javascript
// ステップ別自動化
step1: スクリプト編集
step2: MCP音声生成 ← NEW!
step3: 字幕調整
step4: DaVinci出力
```

### 3. **Claude Code 連携コマンド**
- `/mcp:tts 'サンプルテキスト' --voice-narration`
- `/mcp:search-voices '映画ナレーター風'`
- `/mcp:clone-voice audio/user_sample.mp3`

---

## 📈 パフォーマンス比較

| 機能 | 従来方式 | MCP方式 | 改善点 |
|------|----------|---------|---------|
| 音声生成 | 直接API呼び出し | Claude Code経由 | 自動化・バッチ処理 |
| 音声検索 | 手動選択 | インテリジェント検索 | AI支援選択 |
| クローニング | 未対応 | インスタント対応 | 新機能追加 |
| 品質管理 | 基本 | 高度な最適化 | プロ品質 |

---

## 🔧 次のステップ

### **すぐできること**
1. **Claude Code でテスト**:
   ```
   /mcp:tts "今日は良い天気ですね"
   ```

2. **音声検索テスト**:
   ```
   /mcp:search-voices "アニメナレーター"
   ```

### **GUI統合実装** (進行中 🔄)
- サイドバーワークフロー統合
- リアルタイム音声プレビュー
- バッチ処理自動化

### **高度な活用**
- 音声クローニングワークフロー
- 多言語対応TTS
- 音声品質自動最適化

---

## 🎉 統合成功！

**ElevenLabs MCP Server が完全に統合され、Claude Code から高度なTTS機能を直接使用可能になりました。**

既存のminivt_pipelineと完璧に連携し、GUI統合で更なる自動化を実現します。

**準備完了 - Claude Code でプロ品質の音声生成を開始してください！** 🚀
