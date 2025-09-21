# resolve_import.py
# DaVinci Resolve に字幕（SRT）をインポートするスクリプト
# GUIでSRTファイルを選択 → タイムラインにインポート
# Workspace → Scripts → Edit から呼び出して使う

import os
import sys
from tkinter import Tk, filedialog

def log(msg):
    try:
        print(msg)
    except Exception:
        pass

def choose_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select SRT file",
        filetypes=[("SubRip Subtitle", "*.srt"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path

def main():
    srt_path = choose_file()
    if not srt_path:
        log("[INFO] Cancelled by user.")
        return

    if not os.path.exists(srt_path):
        log(f"[ERROR] File not found: {srt_path}")
        return

    try:
        import DaVinciResolveScript as dvr
    except Exception as e:
        log(f"[ERROR] DaVinciResolveScript import failed: {e}")
        return

    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        log("[ERROR] Resolve scripting app not available.")
        return

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    if not project:
        log("[ERROR] No active project.")
        return

    timeline = project.GetCurrentTimeline()
    if not timeline:
        log("[ERROR] No active timeline.")
        return

    imported = False
    for fn in ("ImportSubtitles", "ImportSubtitle", "ImportTimelineSubtitle"):
        if hasattr(timeline, fn):
            try:
                getattr(timeline, fn)(srt_path)
                log(f"[DONE] Subtitle imported via {fn}: {srt_path}")
                imported = True
                break
            except Exception as e:
                log(f"[WARN] timeline.{fn} failed: {e}")

    if not imported:
        mp = project.GetMediaPool()
        try:
            mp.ImportMedia([srt_path])
            log("[INFO] SRT imported to Media Pool. Right-click → 'Import Subtitle' if needed.")
        except Exception as e:
            log(f"[ERROR] MediaPool.ImportMedia failed: {e}")
            return

if __name__ == "__main__":
    main()
