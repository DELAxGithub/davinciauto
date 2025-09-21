# -*- mode: python ; coding: utf-8 -*-

# NOTE: PyInstaller executes this spec via exec without __file__ defined.
# Use current working directory, assuming build is invoked from repo root.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_root = Path(os.getcwd()).resolve()
entry_script = project_root / "davinciauto_cli" / "__main__.py"
bundle_name = os.environ.get("DAVINCIAUTO_CLI_BUNDLE", "davinciauto-cli")

hiddenimports = (
    collect_submodules("davinciauto_cli")
    + collect_submodules("davinciauto_core")
)

resources = []
resources.append((str(project_root / "davinciauto_core" / "prompts" / "main.jsonl"), "davinciauto_core/prompts"))
resources.append((str(project_root / "README.md"), "."))
resources.append((str(project_root / "LICENSE"), "."))
resources.append((str(project_root / "resources" / "README_FIRST.txt"), "."))
resources.append((str(project_root / "samples" / "sample_script.txt"), "samples"))
licenses_dir = project_root / "licenses"
if licenses_dir.exists():
    resources.append((str(licenses_dir), "licenses"))

bin_items = []
ffmpeg_env = os.environ.get("DAVINCIAUTO_FFMPEG_BUNDLE")
if ffmpeg_env:
    ffmpeg_path = Path(ffmpeg_env).expanduser()
    if ffmpeg_path.exists():
        bin_items.append((str(ffmpeg_path), "bin"))
ffprobe_env = os.environ.get("DAVINCIAUTO_FFPROBE_BUNDLE")
if ffprobe_env:
    ffprobe_path = Path(ffprobe_env).expanduser()
    if ffprobe_path.exists():
        bin_items.append((str(ffprobe_path), "bin"))

block_cipher = None
excludes = [
    "tkinter",
    "tcl",
    "tk",
    "lib2to3",
    "distutils",
    "unittest",
    "sqlite3",
    "matplotlib",
    "PIL.ImageTk",
    "numpy.f2py",
]

a = Analysis(
    [str(entry_script)],
    pathex=[str(project_root)],
    binaries=bin_items,
    datas=resources,
    hiddenimports=hiddenimports,
    hookspath=["pyinstaller/hooks"],
    runtime_hooks=["pyinstaller/runtime_hook_davinciauto.py"],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="davinciauto-cli",
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=bundle_name,
    distpath=str(project_root / "dist"),
)
