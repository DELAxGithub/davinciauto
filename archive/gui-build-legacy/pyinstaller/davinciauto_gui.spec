# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the davinciauto GUI bundle."""
from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path.cwd()
resources_dir = project_root / "Resources"

hiddenimports = sorted(
    set(["azure.cognitiveservices.speech"] + collect_submodules("elevenlabs"))
)

def resource(path: str) -> str:
    return str((resources_dir / path).resolve())

datas = [
    (resource("bin/ffmpeg"), "Resources/bin"),
    (resource("bin/ffprobe"), "Resources/bin"),
]

binaries: list[tuple[str, str]] = []

block_cipher = None


a = Analysis(
    [str(project_root / "pyinstaller/gui_entry.py")],
    pathex=[str(project_root)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="davinciauto_gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

cli_analysis = Analysis(
    [str(project_root / "pyinstaller/cli_entry.py")],
    pathex=[str(project_root)],
    datas=[],
    binaries=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
cli_pyz = PYZ(cli_analysis.pure, cli_analysis.zipped_data, cipher=block_cipher)
cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    cli_analysis.binaries,
    cli_analysis.zipfiles,
    cli_analysis.datas,
    [],
    name="davinciauto_cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

bundle_identifier = os.environ.get("DAVINCIAUTO_BUNDLE_ID", "jp.orionroom.davinciauto.gui")
bundle_version = os.environ.get("DAVINCIAUTO_GUI_VERSION", "0.1.0")
info_plist = {
    "CFBundleDisplayName": "DaVinciAuto GUI",
    "CFBundleName": "DaVinciAuto GUI",
    "CFBundleShortVersionString": bundle_version,
    "CFBundleVersion": bundle_version,
    "NSHighResolutionCapable": True,
    "LSBackgroundOnly": False,
}

app = BUNDLE(
    exe,
    cli_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="DaVinciAuto GUI.app",
    info_plist=info_plist,
    bundle_identifier=bundle_identifier,
)
