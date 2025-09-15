#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess

sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("エラー: DaVinci Resolveのスクリプトモジュールが見つかりません。")
    sys.exit(1)

THUMBNAIL_DIR = "thumbnails"
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mxf', '.avi', '.braw')
FFMPEG_PATH = '/opt/homebrew/bin/ffmpeg'


def timecode_to_seconds(timecode_str, fps):
    """
    タイムコード文字列 (HH:MM:SS:FF or HH:MM:SS;FF) を秒数に変換する。
    """
    try:
        # ドロップフレームのセミコロン';'をコロン':'に統一
        clean_tc = timecode_str.replace(';', ':')
        parts = clean_tc.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        frames = int(parts[3])
        
        total_seconds = (hours * 3600) + (minutes * 60) + seconds + (frames / float(fps))
        return total_seconds
    except (ValueError, IndexError, ZeroDivisionError):
        # 予期しない形式のタイムコードやfps=0の場合
        return None


def extract_thumbnail(clip_path, output_dir, midpoint_seconds):
    base_filename = os.path.basename(clip_path)
    output_filename = os.path.join(output_dir, f"{base_filename}.jpg")

    if os.path.exists(output_filename):
        print(f"✔️  サムネイルは既に存在します: {base_filename}")
        return True

    try:
        print(f"⏳  サムネイルを抽出中: {base_filename} ...")
        
        command = [
            FFMPEG_PATH,
            '-i', clip_path,
            '-ss', str(midpoint_seconds),
            '-vframes', '1',
            '-q:v', '3',
            '-y',
            output_filename
        ]
        
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✅  サムネイルを保存しました: {output_filename}")
        return True

    except FileNotFoundError:
        print(f"!!! エラー: '{FFMPEG_PATH}' が見つかりません。!!!")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌  '{base_filename}' のサムネイル抽出に失敗しました。")
        error_message = e.stderr.decode('utf-8', errors='ignore')
        print(f"   ffmpegエラー: {error_message}")
        return False


def get_media_pool_clips(media_pool):
    clip_list = []
    clips = media_pool.GetClipList()
    if clips:
        clip_list.extend(clips)
    sub_folders = media_pool.GetSubFolderList()
    for sub_folder in sub_folders:
        clip_list.extend(get_media_pool_clips(sub_folder))
    return clip_list


def main():
    try:
        resolve = dvr_script.scriptapp("Resolve")
    except Exception:
        print(f"エラー: DaVinci Resolveに接続できませんでした。")
        return

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        print("エラー: プロジェクトが開かれていません。")
        return

    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    
    project_dir = os.path.dirname(project.GetSetting("ProjectFilePath"))
    if not project_dir:
        home_dir = os.path.expanduser("~")
        project_dir = os.path.join(home_dir, "Desktop", "resolve_thumbnails")
        print(f"警告: プロジェクトが保存されていません。サムネイルは '{project_dir}' に保存されます。")
    
    thumbnail_output_dir = os.path.join(project_dir, THUMBNAIL_DIR)
    os.makedirs(thumbnail_output_dir, exist_ok=True)
    
    print(f"サムネイルは '{thumbnail_output_dir}' に保存されます。")
    print("--- 映像クリップのサムネイル抽出を開始 ---")

    all_clips = get_media_pool_clips(root_folder)
    
    video_clips_found = 0
    for clip in all_clips:
        file_path = clip.GetClipProperty("File Path")
        
        if file_path and file_path.lower().endswith(VIDEO_EXTENSIONS):
            video_clips_found += 1
            clip_name = os.path.basename(file_path)

            duration_tc = clip.GetClipProperty("Duration")
            fps_prop = clip.GetClipProperty("FPS")
            
            if not all([duration_tc, fps_prop]):
                print(f"⚠️  '{clip_name}' のDurationまたはFPSが空です。スキップします。")
                continue

            # タイムコードを秒数に変換
            duration_seconds = timecode_to_seconds(duration_tc, fps_prop)
            
            if duration_seconds is not None and duration_seconds > 0:
                midpoint = duration_seconds / 2.0
                extract_thumbnail(file_path, thumbnail_output_dir, midpoint)
            else:
                print(f"⚠️  '{clip_name}' の時間を計算できませんでした。スキップします。 (Duration: {duration_tc})")

    if video_clips_found == 0:
        print("処理対象の映像クリップが見つかりませんでした。")
        
    print("------------------------------------")
    print("全ての処理が完了しました。")

if __name__ == "__main__":
    main()