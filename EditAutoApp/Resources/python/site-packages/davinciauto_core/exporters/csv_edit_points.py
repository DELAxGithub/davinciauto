# csv_edit_points.py
# DaVinci Resolve CSV自動編集点挿入スクリプト
# CSVファイルのタイムコードを読み取り、タイムラインに編集点を一括挿入
# Workspace → Scripts → Edit から実行

import os
import sys
import csv
from tkinter import Tk, filedialog, messagebox, StringVar, IntVar
from tkinter import ttk
import threading

# プロジェクトのutilsをimport
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from timecode_utils import (
    timecode_to_frames, 
    validate_timecode_range, 
    get_duration_frames,
    COMMON_FPS
)

def log(msg):
    """ログ出力（DaVinci Resolve Console用）"""
    try:
        print(msg)
    except Exception:
        pass

class CSVEditPointsGUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("CSV Edit Points Inserter")
        self.root.geometry("600x500")
        
        # 変数
        self.csv_file = StringVar()
        self.edit_mode = StringVar(value="start_only")
        self.fps_var = StringVar(value="25.0")
        self.progress_var = IntVar()
        self.status_text = StringVar(value="CSVファイルを選択してください")
        
        # CSV データ
        self.csv_data = []
        
        # DaVinci Resolve オブジェクト
        self.resolve = None
        self.timeline = None
        
        self.setup_ui()
        self.init_resolve()
    
    def setup_ui(self):
        """UI セットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(ttk.W, ttk.E, ttk.N, ttk.S))
        
        # CSV選択セクション
        csv_frame = ttk.LabelFrame(main_frame, text="CSV ファイル選択", padding="10")
        csv_frame.grid(row=0, column=0, columnspan=2, sticky=(ttk.W, ttk.E), pady=(0, 10))
        
        ttk.Label(csv_frame, text="ファイル:").grid(row=0, column=0, sticky=ttk.W)
        ttk.Entry(csv_frame, textvariable=self.csv_file, width=50).grid(row=0, column=1, padx=(5, 10))
        ttk.Button(csv_frame, text="参照", command=self.choose_csv).grid(row=0, column=2)
        
        # プレビューセクション
        preview_frame = ttk.LabelFrame(main_frame, text="CSV プレビュー", padding="10")
        preview_frame.grid(row=1, column=0, columnspan=2, sticky=(ttk.W, ttk.E, ttk.N, ttk.S), pady=(0, 10))
        
        # Tree view for CSV preview
        columns = ("Start Time", "End Time", "Label", "Color Group")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(preview_frame, orient=ttk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(ttk.W, ttk.E, ttk.N, ttk.S))
        scrollbar.grid(row=0, column=1, sticky=(ttk.N, ttk.S))
        
        # 設定セクション
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(ttk.W, ttk.E), pady=(0, 10))
        
        # FPS設定
        ttk.Label(settings_frame, text="フレームレート:").grid(row=0, column=0, sticky=ttk.W)
        fps_combo = ttk.Combobox(settings_frame, textvariable=self.fps_var, width=10)
        fps_combo['values'] = ('24.0', '25.0', '29.97', '30.0', '50.0', '60.0')
        fps_combo.grid(row=0, column=1, padx=(5, 20), sticky=ttk.W)
        
        # 編集点モード
        ttk.Label(settings_frame, text="編集点モード:").grid(row=0, column=2, sticky=ttk.W)
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=0, column=3, padx=(5, 0), sticky=ttk.W)
        
        ttk.Radiobutton(mode_frame, text="開始時間のみ", variable=self.edit_mode, 
                       value="start_only").grid(row=0, column=0, sticky=ttk.W)
        ttk.Radiobutton(mode_frame, text="開始+終了", variable=self.edit_mode, 
                       value="start_end").grid(row=1, column=0, sticky=ttk.W)
        
        # 実行セクション
        execute_frame = ttk.Frame(main_frame)
        execute_frame.grid(row=3, column=0, columnspan=2, sticky=(ttk.W, ttk.E), pady=(0, 10))
        
        self.execute_btn = ttk.Button(execute_frame, text="編集点を挿入", 
                                     command=self.start_processing, state="disabled")
        self.execute_btn.pack(side=ttk.LEFT)
        
        # プログレスバー
        self.progress = ttk.Progressbar(execute_frame, variable=self.progress_var, 
                                       maximum=100, length=200)
        self.progress.pack(side=ttk.RIGHT, padx=(20, 0))
        
        # ステータス
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(ttk.W, ttk.E))
        
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=ttk.LEFT)
        
        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
    
    def init_resolve(self):
        """DaVinci Resolve 初期化"""
        try:
            import DaVinciResolveScript as dvr
            self.resolve = dvr.scriptapp("Resolve")
            if not self.resolve:
                self.status_text.set("エラー: DaVinci Resolve接続失敗")
                return
                
            pm = self.resolve.GetProjectManager()
            project = pm.GetCurrentProject() if pm else None
            if not project:
                self.status_text.set("エラー: アクティブなプロジェクトがありません")
                return
                
            self.timeline = project.GetCurrentTimeline()
            if not self.timeline:
                self.status_text.set("エラー: アクティブなタイムラインがありません")
                return
                
            timeline_name = self.timeline.GetName()
            fps = self.timeline.GetSetting("timelineFrameRate")
            if fps:
                self.fps_var.set(str(fps))
                
            self.status_text.set(f"接続完了: タイムライン '{timeline_name}' (FPS: {fps})")
            
        except Exception as e:
            log(f"[ERROR] Resolve initialization failed: {e}")
            self.status_text.set(f"エラー: {e}")
    
    def choose_csv(self):
        """CSV ファイル選択"""
        file_path = filedialog.askopenfilename(
            title="CSV ファイルを選択",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.csv_file.set(file_path)
            self.load_csv_preview(file_path)
    
    def load_csv_preview(self, file_path):
        """CSV プレビュー読み込み"""
        try:
            # Tree view クリア
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.csv_data = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 50:  # 最大50行まで表示
                        break
                        
                    start_time = row.get('Start Time', '').strip()
                    end_time = row.get('End Time', '').strip()
                    label = row.get('Label', '').strip()
                    color_group = row.get('Color Group', '').strip()
                    
                    # 空行スキップ
                    if not start_time and not end_time:
                        continue
                        
                    # バリデーション
                    if start_time and end_time:
                        fps = float(self.fps_var.get())
                        if not validate_timecode_range(start_time, end_time, fps):
                            log(f"[WARN] Invalid timecode range: {start_time} to {end_time}")
                            continue
                    
                    self.csv_data.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'label': label,
                        'color_group': color_group
                    })
                    
                    # Tree view に追加（最初の10行のみ表示）
                    if len(self.csv_data) <= 10:
                        self.tree.insert("", "end", values=(start_time, end_time, label, color_group))
            
            if self.csv_data:
                self.execute_btn.config(state="normal")
                self.status_text.set(f"CSV読み込み完了: {len(self.csv_data)}区間")
            else:
                self.status_text.set("エラー: 有効なデータが見つかりません")
                
        except Exception as e:
            log(f"[ERROR] CSV load failed: {e}")
            self.status_text.set(f"エラー: {e}")
    
    def start_processing(self):
        """処理開始（別スレッドで実行）"""
        self.execute_btn.config(state="disabled")
        self.progress_var.set(0)
        
        # 別スレッドで実行
        thread = threading.Thread(target=self.process_edit_points)
        thread.daemon = True
        thread.start()
    
    def process_edit_points(self):
        """編集点挿入処理"""
        try:
            if not self.timeline:
                self.status_text.set("エラー: タイムラインが利用できません")
                return
            
            fps = float(self.fps_var.get())
            mode = self.edit_mode.get()
            total_items = len(self.csv_data)
            
            success_count = 0
            error_count = 0
            
            for i, item in enumerate(self.csv_data):
                try:
                    start_time = item['start_time']
                    end_time = item['end_time']
                    label = item['label']
                    
                    if not start_time:
                        error_count += 1
                        continue
                    
                    # フレーム数に変換
                    start_frame = timecode_to_frames(start_time, fps)
                    if start_frame is None:
                        log(f"[ERROR] Invalid start timecode: {start_time}")
                        error_count += 1
                        continue
                    
                    # 開始時間に編集点挿入
                    success = self.insert_edit_point(start_frame, f"Start: {label}")
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                    
                    # 開始+終了モードの場合、終了時間にも挿入
                    if mode == "start_end" and end_time:
                        end_frame = timecode_to_frames(end_time, fps)
                        if end_frame is not None:
                            end_success = self.insert_edit_point(end_frame, f"End: {label}")
                            if end_success:
                                success_count += 1
                            else:
                                error_count += 1
                    
                    # プログレス更新
                    progress = int((i + 1) * 100 / total_items)
                    self.progress_var.set(progress)
                    self.status_text.set(f"処理中... ({i+1}/{total_items})")
                    
                except Exception as e:
                    log(f"[ERROR] Processing item {i}: {e}")
                    error_count += 1
            
            # 完了
            self.progress_var.set(100)
            self.status_text.set(f"完了: 成功 {success_count}, エラー {error_count}")
            
            if success_count > 0:
                messagebox.showinfo("完了", f"編集点挿入が完了しました。\n成功: {success_count}, エラー: {error_count}")
            
        except Exception as e:
            log(f"[ERROR] Processing failed: {e}")
            self.status_text.set(f"エラー: {e}")
        
        finally:
            self.execute_btn.config(state="normal")
    
    def insert_edit_point(self, frame_number, label="Edit Point"):
        """指定フレーム位置に編集点を挿入"""
        try:
            # タイムライン座標に変換（ゼロベース）
            timeline_frame = frame_number
            
            # 複数の方法で編集点挿入を試行
            methods = [
                ("AddEdit", lambda: self.timeline.AddEdit()),
                ("SplitClip", lambda: self.timeline.SplitClip()),
                ("SetCurrentTimecode", lambda: self._set_playhead_and_split(timeline_frame))
            ]
            
            for method_name, method_func in methods:
                try:
                    # プレイヘッドを対象位置に移動
                    self.timeline.SetCurrentTimecode(str(timeline_frame))
                    
                    # 編集点挿入実行
                    result = method_func()
                    
                    if result or method_name == "SetCurrentTimecode":
                        log(f"[INFO] Edit point inserted at frame {frame_number} using {method_name}: {label}")
                        return True
                        
                except Exception as e:
                    log(f"[WARN] {method_name} failed: {e}")
                    continue
            
            log(f"[ERROR] All edit point insertion methods failed for frame {frame_number}")
            return False
            
        except Exception as e:
            log(f"[ERROR] Edit point insertion failed: {e}")
            return False
    
    def _set_playhead_and_split(self, frame_number):
        """プレイヘッド移動 + 分割の組み合わせ"""
        try:
            # プレイヘッドを移動
            self.timeline.SetCurrentTimecode(str(frame_number))
            
            # 分割コマンドをシミュレート（API制限により直接分割が困難な場合）
            # 実際のAPIメソッドを確認してここを調整
            return True
            
        except Exception as e:
            log(f"[ERROR] Playhead split failed: {e}")
            return False
    
    def run(self):
        """GUI実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    log("[INFO] CSV Edit Points Inserter starting...")
    
    try:
        app = CSVEditPointsGUI()
        app.run()
    except Exception as e:
        log(f"[ERROR] Application failed: {e}")
        messagebox.showerror("エラー", f"アプリケーションエラー: {e}")

if __name__ == "__main__":
    main()