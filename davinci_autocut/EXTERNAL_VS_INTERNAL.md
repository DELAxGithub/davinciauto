# DaVinci Resolve スクリプティング：「外部用」vs「内部用」

**スーパーバイザーの教え**: 「家の中にいるのにインターホンを押そうとしてもダメ」

## 🏠 基本概念

### 家の比喩で理解する

| 場所 | 外部（VSCode等） | 内部（DaVinciコンソール） |
|------|------------------|---------------------------|
| **状況** | 🔔 家の外からインターホン | 🏠 家の中で執事と直接対話 |
| **接続方法** | `scriptapp("Resolve")` | `resolve`（既に存在） |
| **import** | `import DaVinciResolveScript` | 不要（モジュール未対応） |
| **エラー例** | 接続失敗、タイムアウト | `NameError`, `ModuleNotFoundError` |

## 📝 実際のコード例

### ❌ 間違い：内部で外部用コードを使用

```python
# DaVinci Resolveコンソール内で実行 → エラー
import DaVinciResolveScript as dvr  # ModuleNotFoundError
resolve = scriptapp("Resolve")       # NameError: name 'scriptapp' is not defined
```

### ✅ 正解：内部は直接アクセス

```python
# DaVinci Resolveコンソール内で実行 → 成功
print(resolve)  # Timeline (0x...) のようなオブジェクト情報が表示
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
```

## 🛠️ 環境別実装パターン

### 外部スクリプト（VSCode、ターミナル等）

```python
#!/usr/bin/env python3
"""外部スクリプトファイル（main.py等）"""

import sys
import DaVinciResolveScript as dvr  # 外部接続用モジュール

def main():
    # インターホンで呼び出し
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        print("DaVinci Resolveに接続できません")
        return
    
    # 以下、通常の処理
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    # ...

if __name__ == "__main__":
    main()
```

### 内部コンソール（DaVinci Resolve内）

```python
# DaVinci Resolve → Workspace → Console で実行

# resolveオブジェクトは既に存在（執事が待機中）
print(f"Resolve: {resolve}")

# 直接使用開始
timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
print(f"タイムライン: {timeline.GetName()}")

# マーカー追加（実証済み）
current_tc = timeline.GetCurrentTimecode()
result = timeline.AddMarker(current_tc, "Cyan", "コンソールテスト", "直接実行", 60)
print(f"結果: {result}")
```

## 🚨 よくあるエラーとその原因

### ModuleNotFoundError: No module named 'DaVinciResolveScript'

**原因**: 内部コンソールで外部用モジュールをimportしようとした
**解決**: 内部コンソールでは不要、`resolve`を直接使用

### NameError: name 'scriptapp' is not defined

**原因**: 内部コンソールで外部用接続関数を使おうとした
**解決**: `resolve`オブジェクトが既に利用可能

### 接続タイムアウト・失敗（外部スクリプト）

**原因**: DaVinci Resolve未起動、API無効化
**解決**: Resolve起動、設定でRemote Scripting有効化

## 🎯 使い分けのガイドライン

### 内部コンソールを使う場合
- **目的**: 素早いテスト、デバッグ、ワンショット作業
- **メリット**: 接続不要、即座に実行
- **デメリット**: スクリプト保存不可、複雑な処理に不向き

### 外部スクリプトを使う場合  
- **目的**: 本格運用、自動化、CSV一括処理
- **メリット**: ファイル保存、バージョン管理、エラーハンドリング
- **デメリット**: 接続設定が必要、API有効化必要

## 💡 スーパーバイザーの金言

> **「家の中にいるのにインターホンを押そうとしても意味がない」**
> 
> - 内部コンソール：`resolve`が既に存在、直接対話
> - 外部スクリプト：`scriptapp()`でインターホン、接続確立後に対話
> 
> **環境に応じた正しい作法を使い分けることが、Resolveと上手に「対話」する第一歩**

## 📚 関連ファイル

- `CONSOLE_COMMANDS.md`: 内部コンソール用コマンド集
- `main.py`: 外部スクリプト用メイン実装
- `scripts/`: 外部実行用テストスクリプト群