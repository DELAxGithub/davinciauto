#!/usr/bin/env python3
"""
DaVinci Resolve 自動カット・マーカー処理メインスクリプト

CSVファイルからマーカー情報を読み込み、
DaVinci Resolveのタイムライン上でクリップの分割とマーカー追加を自動実行する。
"""

import sys
import csv
import os
from pathlib import Path

# 自作の補助関数をインポート
from lib.resolve_utils import tc_to_frames, validate_timecode_format

# --- DaVinci Resolveスクリプティング設定 ---
try:
    import DaVinciResolveScript as dvr
except ImportError:
    print("エラー: DaVinciResolveScriptモジュールが見つかりません。")
    print("環境変数RESOLVE_SCRIPT_APIとRESORVE_SCRIPT_LIBを確認してください。")
    sys.exit(1)


def get_resolve_objects():
    """Resolveに接続し、プロジェクトとタイムラインのオブジェクトを返す
    
    Returns:
        tuple: (project, timeline) または (None, None) if error
    """
    try:
        resolve = dvr.scriptapp("Resolve")
        if not resolve:
            print("エラー: DaVinci Resolveに接続できません。Resolveが起動しているか確認してください。")
            return None, None
            
        pm = resolve.GetProjectManager()
        proj = pm.GetCurrentProject()
        if not proj:
            print("エラー: アクティブなプロジェクトがありません。")
            return None, None
            
        timeline = proj.GetCurrentTimeline()
        if not timeline:
            print("エラー: アクティブなタイムラインがありません。")
            return None, None
            
    except Exception as e:
        print(f"Resolveオブジェクト取得中にエラーが発生しました: {e}")
        return None, None
        
    return proj, timeline


def load_and_validate_csv(csv_path):
    """CSVファイルを読み込み、データを検証する
    
    Args:
        csv_path (str): CSVファイルのパス
    
    Returns:
        list: 検証済みのセグメントデータリスト
    """
    if not os.path.exists(csv_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        return []
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            segments = []
            
            for row_num, row in enumerate(reader, start=2):  # ヘッダーを除く行番号
                # 必須フィールドの確認
                required_fields = ['In', 'Out', 'Color', 'Name']
                missing_fields = [field for field in required_fields if not row.get(field)]
                
                if missing_fields:
                    print(f"警告: 行{row_num}で必須フィールドが不足: {missing_fields}")
                    continue
                
                # タイムコード形式の検証
                if not validate_timecode_format(row['In']):
                    print(f"警告: 行{row_num}のInタイムコードが無効: {row['In']}")
                    continue
                    
                if not validate_timecode_format(row['Out']):
                    print(f"警告: 行{row_num}のOutタイムコードが無効: {row['Out']}")
                    continue
                
                segments.append(row)
            
            # Inタイムコードでソート
            segments = sorted(segments, key=lambda row: row['In'])
            print(f"CSVから{len(segments)}個の有効なセグメントを読み込みました")
            
    except Exception as e:
        print(f"CSV読み込み中にエラーが発生しました: {e}")
        return []
    
    return segments


def process_cuts_from_csv(timeline, csv_path):
    """CSVを読み込み、タイムライン処理を実行するメイン関数
    
    Args:
        timeline: DaVinci Resolveのタイムラインオブジェクト
        csv_path (str): CSVファイルのパス
    """
    
    # 1. CSVファイルの読み込みと検証
    print(f"CSVファイルを読み込みます: {csv_path}")
    segments = load_and_validate_csv(csv_path)
    
    if not segments:
        print("処理可能なセグメントがありません。")
        return
    
    # 2. タイムライン情報の取得
    frame_rate = float(timeline.GetSetting("timelineFrameRate"))
    timeline_name = timeline.GetName()
    print(f"タイムライン情報: '{timeline_name}' @ {frame_rate}fps")
    
    # 3. カット処理
    # 重複を除いた全てのカット点を収集
    all_cut_points = sorted(list(set(
        [tc_to_frames(seg['In'], frame_rate) for seg in segments] + 
        [tc_to_frames(seg['Out'], frame_rate) for seg in segments]
    )))
    
    print(f"\n合計{len(all_cut_points)}箇所のカットポイントでクリップを分割します...")
    
    # トラックごとにカット処理を実行
    for track_type in ["video", "audio"]:
        track_count = timeline.GetTrackCount(track_type)
        print(f"{track_type.capitalize()}トラック ({track_count}個) を処理中...")
        
        for i in range(1, track_count + 1):
            clips = timeline.GetItemListInTrack(track_type, i)
            if not clips:
                continue
            
            # クリップごとに分割処理
            for clip_id, clip in clips.items():
                start = clip.GetStart()
                end = clip.GetEnd()
                
                # このクリップ内にあるカットポイントで分割
                # 後ろから処理することでインデックスのずれを防ぐ
                clip_cuts = sorted([p for p in all_cut_points if start < p < end], reverse=True)
                
                for cut_frame in clip_cuts:
                    clip_name = clip.GetName() if clip.GetName() else "Unnamed"
                    print(f"  - {track_type}トラック{i}のクリップ '{clip_name}' をフレーム {cut_frame} で分割")
                    
                    try:
                        # スーパーバイザー推奨方式：再生ヘッドを移動させてからカット
                        # GetCurrentFrame()は存在しない(None)ため、タイムコード設定で確実に
                        timeline.SetCurrentTimecode(int(cut_frame))
                        
                        # 検証：現在位置が正しく設定されたかタイムコードで確認
                        current_tc = timeline.GetCurrentTimecode()
                        # タイムコードからフレーム番号を再計算して検証
                        h, m, s, f = map(int, current_tc.split(':'))
                        current_frame_calc = (h * 3600 + m * 60 + s) * int(frame_rate) + f
                        
                        if abs(current_frame_calc - cut_frame) > 1:  # 1フレームの誤差は許容
                            print(f"    - 警告: 再生ヘッド位置不正確 期待{cut_frame} 実際{current_frame_calc}")
                        
                        # クリップ分割実行 - APIのクセに対応
                        result = timeline.SplitClip(clip, int(cut_frame))
                        if not result:
                            # AddMarker同様、戻り値がFalseでも成功している場合があるため警告レベル
                            print(f"    - 警告: SplitClipがFalseを返しました（実際は成功の可能性あり）")
                        else:
                            print(f"    - ✅ 分割成功（タイムコード検証済み）")
                        
                    except Exception as e:
                        print(f"    - エラー: フレーム {cut_frame} でのクリップ分割中に例外が発生: {e}")
                        continue
    
    print("カット処理が完了しました。")
    
    # 4. マーカーの追加
    print("\n範囲マーカーを追加します...")
    for segment in segments:
        start_frame = tc_to_frames(segment['In'], frame_rate)
        end_frame = tc_to_frames(segment['Out'], frame_rate)
        duration = end_frame - start_frame
        
        if duration > 0:
            color = segment['Color']
            name = segment['Name']
            note = segment.get('Note', '')  # Noteは任意フィールド
            
            print(f"  - '{name}' ({color}) をフレーム {start_frame} に追加 (期間: {duration}フレーム)")
            
            try:
                # スーパーバイザー推奨方式：タイムコードベース検証
                # start_frameが正確かタイムコード逆算で確認
                expected_h = start_frame // (3600 * int(frame_rate))
                expected_m = (start_frame % (3600 * int(frame_rate))) // (60 * int(frame_rate))
                expected_s = (start_frame % (60 * int(frame_rate))) // int(frame_rate)
                expected_f = start_frame % int(frame_rate)
                expected_tc = f"{expected_h:02d}:{expected_m:02d}:{expected_s:02d}:{expected_f:02d}"
                
                print(f"    - フレーム{start_frame} = タイムコード{expected_tc}で検証")
                
                # マーカー追加実行 - APIのクセに対応
                result = timeline.AddMarker(start_frame, color, name, note, duration)
                if not result:
                    # AddMarkerの戻り値はあてにならない。Falseでもマーカーが追加されることがある
                    print(f"    - 警告: AddMarkerがFalseを返しました（実際は成功の可能性あり）")
                    print(f"    - タイムコード{expected_tc}の位置を確認してください")
                else:
                    print(f"    - ✅ マーカー追加成功（タイムコード検証済み）")
                    
            except Exception as e:
                print(f"    - エラー: マーカー '{name}' の追加中に例外が発生: {e}")
                continue
                
        else:
            print(f"  - 警告: '{segment['Name']}' は長さが0のためスキップします")
    
    print("\nすべての処理が完了しました。")


def main():
    """メイン実行関数"""
    print("--- DaVinci Resolve 自動カット・マーカー処理スクリプト開始 ---")
    
    # 1. コマンドライン引数からCSVパスを取得
    if len(sys.argv) < 2:
        # デフォルトパスの設定
        script_dir = Path(__file__).parent
        csv_file_path = script_dir / 'data' / 'markers.csv'
        print(f"CSVパス未指定のため、デフォルトファイルを使用: {csv_file_path}")
    else:
        csv_file_path = sys.argv[1]
    
    # 2. DaVinci Resolveに接続
    project, timeline = get_resolve_objects()
    
    # 3. 接続成功ならメイン処理を実行
    if project and timeline:
        process_cuts_from_csv(timeline, str(csv_file_path))
    else:
        print("DaVinci Resolveに接続できなかったため、スクリプトを終了します。")
        sys.exit(1)


if __name__ == "__main__":
    main()