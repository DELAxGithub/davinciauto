# SPEC-010: PyInstaller バンドル方針

## MUST
- 配布形態は PyInstaller **OneDir** を採用し、`dist/davinciauto_gui/` に以下を同梱する。
  - GUI 実行ファイル `davinciauto_gui`。
  - CLI 実行ファイル `Resources/bin/davinciauto_cli`。
  - PySide6 のプラグイン (`platforms/`, `imageformats/`, `styles/`, `iconengines/`, `networkinformation/`)。
  - `ffmpeg` / `ffprobe` バイナリ（実行権限付き）。
  - 必要な静的アセット（フォント等）。
- spec ファイルで `collect_all('PySide6')` を利用し、`datas`/`binaries`/`hiddenimports` を漏れなく指定する。
- `hiddenimports` に `azure.cognitiveservices.speech` などネイティブ依存を明示する。
- すべてのリソース参照は `resource_path()` を経由し、`sys._MEIPASS` を考慮する。

## SHOULD
- 起動時 Self-check で Qt プラグイン、ffmpeg、Speech SDK が使用可能か検証する。
- macOS では署名→公証→Staple の手順を README / CI ドキュメントに明記する。

## DoD
- `pyinstaller/build_gui.sh` から macOS / Windows の OneDir ビルドが成功する。
- 新規ユーザー環境（ネットワーク遮断）でも GUI が起動し Self-check が緑（任意項目は黄色）になる。
- OneDir フォルダを空白・日本語を含むパスへ移動しても起動する。

## spec スケルトン
```python
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

pyside_datas, pyside_bins, pyside_hidden = collect_all('PySide6')
hiddenimports = list(set(pyside_hidden + ['azure.cognitiveservices.speech']))

resources = Path('Resources')
cli_exe = Path('build/cli_exe')

datas = pyside_datas + [
    (str(resources / 'fonts'), 'Resources/fonts'),
    (str(resources / 'bin' / 'ffmpeg'), 'Resources/bin'),
    (str(resources / 'bin' / 'ffprobe'), 'Resources/bin'),
    (str(cli_exe), 'Resources/bin'),
]

binaries = pyside_bins
```

`resource_path()` のユーティリティ例:
```python
import sys
from pathlib import Path

def resource_path(relative: str) -> str:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return str((base / relative).resolve())
```
