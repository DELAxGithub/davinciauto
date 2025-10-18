# Archive - GUI & Build Legacy

GUI アプリケーション、ビルドシステム、旧実装のアーカイブ

## 内容

### GUI アプリケーション
- `gui_app/` - PySide6 GUI メインアプリケーション
- `gui_steps/` - GUI ステップコンポーネント
- `EditAutoApp/` - 編集自動化アプリ
- `backend/` - バックエンドサービス

### 旧CLI・コア
- `davinciauto_cli/` - 旧CLIツール
- `davinciauto_core/` - 旧コアライブラリ
- `davinciauto_core.egg-info/` - ビルド成果物
- `editautoerror/` - エラー処理モジュール

### ビルド・配布
- `build/` - ビルドディレクトリ
- `dist/` - 配布パッケージ
- `pyinstaller/` - PyInstallerビルドスクリプト

### リソース・サンプル
- `resources/` - 画像、アイコンなどのリソース
- `samples/` - サンプルファイル
- `thumbnails/` - サムネイル画像
- `terop/` - テロップ関連

### 設定・ツール
- `ci/` - CI/CD設定
- `config/` - 旧設定ファイル
- `core/` - 旧コアモジュール
- `output/` - 旧出力ディレクトリ
- `prompts/` - LLMプロンプト
- `tools/` - 旧ツール
- `yaml/` - YAML設定ファイル
- `--model/` - 不明なディレクトリ

## 廃止理由

### GUI アプリケーションの課題
1. **複雑な依存関係**: PySide6、PyInstaller、多数のPythonパッケージ
2. **保守コスト**: GUIフレームワークのアップデートに追従困難
3. **機能の重複**: CLI パイプラインで十分な自動化を実現
4. **クロスプラットフォーム問題**: macOS、Windows、Linuxでの動作差異

### 旧CLI・コアの課題
1. **アーキテクチャの複雑さ**: 複数ディレクトリに散在した実装
2. **テスト不足**: 自動テストがなく品質保証困難
3. **ドキュメント不足**: APIドキュメントが未整備

## 新パイプラインへの移行

**Orion Pipeline v2 (`orion/`)** は以下の利点があります：
- シンプルなPythonスクリプト（依存最小限）
- 2コマンドで完結する自動化
- 包括的なドキュメント（WORKFLOW.md）
- テスト可能な設計

## 参照方法

### GUI アプリケーションの再起動
このアーカイブ内のコードは動作保証されません。必要な場合：

1. 依存関係の再インストール
```bash
pip install PySide6 PyInstaller
```

2. アプリケーション起動
```bash
python gui_app/main.py
```

**注意**: 環境によっては動作しない可能性があります。

### 旧CLI の使用
```bash
python davinciauto_cli/main.py
```

**推奨**: 新パイプライン (`orion/`) を使用してください。

## 削除について

このディレクトリは **完全に削除可能** です。
- 新パイプラインはこのアーカイブに依存しません
- Git履歴には完全に保存されています
- 必要な場合は Git 履歴から復元可能

```bash
# 削除する場合（慎重に実行）
rm -rf archive/gui-build-legacy/
```

---

**アーカイブ日**: 2024年10月18日
**理由**: Orion Pipeline v2への完全移行、シンプルな構成への統一
