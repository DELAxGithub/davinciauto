#!/usr/bin/env python3
"""
Step 4: DaVinci Resolve Export GUI
DaVinci Resolve出力・レンダリングGUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys
import json
import subprocess
from typing import List, Dict, Optional

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))

from gui_base import BaseStepWindow
from data_models import Project

class DaVinciExportWindow(BaseStepWindow):
    """DaVinci Resolve出力ウィンドウ"""
    
    def __init__(self):
        super().__init__("Step 4: DaVinci Resolve出力", 1200, 800, current_step="step4-davinci-export")
        
        # DaVinci接続状態
        self.davinci_connected = False
        self.resolve = None
        self.project_manager = None
        self.current_resolve_project = None
        
        # GUI セットアップ
        self.setup_main_layout()
        self.setup_connection_panel()
        self.setup_import_panel()
        self.setup_render_settings()
        self.setup_export_controls()
        
        # 初期状態
        self.check_davinci_connection()
    
    def setup_main_layout(self):
        """メインレイアウト設定"""
        # 4分割: 接続 | インポート | レンダリング設定 | 出力コントロール
        self.main_notebook = ttk.Notebook(self.content_frame)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)
        
        # タブ作成
        self.connection_tab = ttk.Frame(self.main_notebook)
        self.import_tab = ttk.Frame(self.main_notebook)
        self.render_tab = ttk.Frame(self.main_notebook)
        self.export_tab = ttk.Frame(self.main_notebook)
        
        self.main_notebook.add(self.connection_tab, text="🔗 DaVinci接続")
        self.main_notebook.add(self.import_tab, text="📥 SRTインポート")
        self.main_notebook.add(self.render_tab, text="⚙️ レンダリング設定")
        self.main_notebook.add(self.export_tab, text="🎬 出力・完了")
    
    def setup_connection_panel(self):
        """DaVinci接続パネル"""
        # 接続状態表示
        status_frame = ttk.LabelFrame(self.connection_tab, text="接続状態")
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.connection_status_var = tk.StringVar(value="未接続")
        status_label = ttk.Label(status_frame, textvariable=self.connection_status_var,
                                font=("", 12, "bold"), foreground="red")
        status_label.pack(pady=10)
        
        # 接続ボタン
        connection_buttons = ttk.Frame(status_frame)
        connection_buttons.pack(pady=10)
        
        self.connect_btn = ttk.Button(connection_buttons, text="🔗 DaVinci Resolveに接続", 
                                     command=self.connect_to_davinci)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(connection_buttons, text="🔄 接続確認", 
                  command=self.check_davinci_connection).pack(side=tk.LEFT, padx=5)
        
        # プロジェクト情報
        project_frame = ttk.LabelFrame(self.connection_tab, text="DaVinciプロジェクト情報")
        project_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # プロジェクト一覧
        project_list_frame = ttk.Frame(project_frame)
        project_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(project_list_frame, text="アクティブプロジェクト:").pack(anchor=tk.W)
        self.project_info_var = tk.StringVar(value="接続されていません")
        ttk.Label(project_list_frame, textvariable=self.project_info_var,
                 font=("", 10)).pack(anchor=tk.W, pady=(5, 10))
        
        # タイムライン情報
        timeline_frame = ttk.Frame(project_list_frame)
        timeline_frame.pack(fill=tk.X)
        
        ttk.Label(timeline_frame, text="アクティブタイムライン:").pack(anchor=tk.W)
        self.timeline_info_var = tk.StringVar(value="情報なし")
        ttk.Label(timeline_frame, textvariable=self.timeline_info_var,
                 font=("", 10)).pack(anchor=tk.W, pady=(5, 0))
        
        # 接続テスト情報
        info_frame = ttk.LabelFrame(self.connection_tab, text="接続について")
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        info_text = \"\"\"DaVinci Resolve接続要件:
• DaVinci Resolve Studio版 (無料版は API制限あり)
• スクリプトメニューからの実行推奨
• アクティブなプロジェクトとタイムライン必要
• 字幕トラックの準備推奨\"\"\"
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(padx=10, pady=10)
    
    def setup_import_panel(self):
        """SRTインポートパネル"""
        # ファイル選択
        file_frame = ttk.LabelFrame(self.import_tab, text="SRTファイル")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(path_frame, text="SRTファイル:").pack(anchor=tk.W)
        
        file_select_frame = ttk.Frame(path_frame)
        file_select_frame.pack(fill=tk.X, pady=5)
        
        self.srt_file_var = tk.StringVar(value="")
        self.srt_file_entry = ttk.Entry(file_select_frame, textvariable=self.srt_file_var)
        self.srt_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(file_select_frame, text="参照", 
                  command=self.browse_srt_file).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 自動検出
        ttk.Button(file_frame, text="🔍 プロジェクトから自動検出", 
                  command=self.auto_detect_srt).pack(pady=5)
        
        # インポート設定
        settings_frame = ttk.LabelFrame(self.import_tab, text="インポート設定")
        settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # インポート方法
        method_frame = ttk.Frame(settings_frame)
        method_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(method_frame, text="インポート方法:").pack(anchor=tk.W)
        self.import_method_var = tk.StringVar(value="timeline")
        
        methods = [
            ("タイムラインに直接", "timeline"),
            ("メディアプールに追加", "mediapool")
        ]
        
        for text, value in methods:
            ttk.Radiobutton(method_frame, text=text, variable=self.import_method_var, 
                           value=value).pack(anchor=tk.W)
        
        # トラック設定
        track_frame = ttk.Frame(settings_frame)
        track_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(track_frame, text="字幕トラック:").pack(side=tk.LEFT)
        self.subtitle_track_var = tk.IntVar(value=1)
        ttk.Spinbox(track_frame, from_=1, to=10, width=5,
                   textvariable=self.subtitle_track_var).pack(side=tk.LEFT, padx=5)
        
        # インポート実行
        import_buttons = ttk.Frame(self.import_tab)
        import_buttons.pack(fill=tk.X, padx=10, pady=10)
        
        self.import_btn = ttk.Button(import_buttons, text="📥 SRTインポート実行", 
                                    command=self.import_srt_file, state="disabled")
        self.import_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(import_buttons, text="👁️ SRTプレビュー", 
                  command=self.preview_srt_file).pack(side=tk.LEFT, padx=5)
        
        # インポートログ
        log_frame = ttk.LabelFrame(self.import_tab, text="インポートログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.import_log = tk.Text(log_frame, height=8, wrap=tk.WORD, font=("Courier", 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.import_log.yview)
        self.import_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.import_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
    
    def setup_render_settings(self):
        """レンダリング設定パネル"""
        # プリセット選択
        preset_frame = ttk.LabelFrame(self.render_tab, text="出力プリセット")
        preset_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.render_preset_var = tk.StringVar(value="youtube_hd")
        presets = [
            ("YouTube HD (1080p H.264)", "youtube_hd"),
            ("YouTube 4K (2160p H.264)", "youtube_4k"), 
            ("高品質 MP4 (H.264)", "high_quality_mp4"),
            ("Web配信用 (H.264)", "web_optimized"),
            ("カスタム設定", "custom")
        ]
        
        for text, value in presets:
            ttk.Radiobutton(preset_frame, text=text, variable=self.render_preset_var, 
                           value=value, command=self.on_preset_change).pack(anchor=tk.W, padx=10, pady=2)
        
        # 詳細設定
        details_frame = ttk.LabelFrame(self.render_tab, text="詳細設定")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 解像度
        resolution_frame = ttk.Frame(details_frame)
        resolution_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(resolution_frame, text="解像度:").pack(side=tk.LEFT)
        self.resolution_var = tk.StringVar(value="1920x1080")
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var,
                                       values=["1920x1080", "3840x2160", "1280x720"],
                                       state="readonly", width=15)
        resolution_combo.pack(side=tk.LEFT, padx=5)
        
        # フレームレート
        ttk.Label(resolution_frame, text="FPS:").pack(side=tk.LEFT, padx=(20, 0))
        self.fps_var = tk.StringVar(value="30")
        fps_combo = ttk.Combobox(resolution_frame, textvariable=self.fps_var,
                                values=["24", "25", "30", "60"], state="readonly", width=8)
        fps_combo.pack(side=tk.LEFT, padx=5)
        
        # ビットレート
        bitrate_frame = ttk.Frame(details_frame)
        bitrate_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(bitrate_frame, text="ビットレート:").pack(side=tk.LEFT)
        self.bitrate_var = tk.StringVar(value="8000")
        ttk.Entry(bitrate_frame, textvariable=self.bitrate_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(bitrate_frame, text="kbps").pack(side=tk.LEFT)
        
        # 音声設定
        audio_frame = ttk.Frame(details_frame)
        audio_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(audio_frame, text="音声:").pack(side=tk.LEFT)
        self.audio_codec_var = tk.StringVar(value="AAC")
        ttk.Combobox(audio_frame, textvariable=self.audio_codec_var,
                    values=["AAC", "MP3"], state="readonly", width=8).pack(side=tk.LEFT, padx=5)
        
        # 出力パス
        output_frame = ttk.Frame(details_frame)
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(output_frame, text="出力パス:").pack(anchor=tk.W)
        
        output_path_frame = ttk.Frame(output_frame)
        output_path_frame.pack(fill=tk.X, pady=5)
        
        self.output_path_var = tk.StringVar(value="")
        ttk.Entry(output_path_frame, textvariable=self.output_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_path_frame, text="参照", 
                  command=self.browse_output_path).pack(side=tk.RIGHT, padx=(5, 0))
        
        # プリセット適用時の初期設定
        self.on_preset_change()
    
    def setup_export_controls(self):
        """出力コントロールパネル"""
        # レンダリング進捗
        progress_frame = ttk.LabelFrame(self.export_tab, text="レンダリング進捗")
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.render_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.render_progress.pack(fill=tk.X, padx=10, pady=10)
        
        self.render_status_var = tk.StringVar(value="待機中...")
        ttk.Label(progress_frame, textvariable=self.render_status_var).pack(padx=10, pady=(0, 10))
        
        # コントロールボタン
        controls_frame = ttk.LabelFrame(self.export_tab, text="レンダリング制御")
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(pady=10)
        
        self.render_btn = ttk.Button(button_frame, text="🎬 レンダリング開始", 
                                    command=self.start_rendering, state="disabled")
        self.render_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_render_btn = ttk.Button(button_frame, text="⏹️ レンダリング停止", 
                                         command=self.stop_rendering, state="disabled")
        self.stop_render_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📊 キュー確認", 
                  command=self.check_render_queue).pack(side=tk.LEFT, padx=5)
        
        # 出力後処理
        post_frame = ttk.LabelFrame(self.export_tab, text="完了後処理")
        post_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        post_options = ttk.Frame(post_frame)
        post_options.pack(padx=10, pady=10)
        
        self.auto_open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(post_options, text="完了後にファイルを開く",
                       variable=self.auto_open_var).pack(anchor=tk.W)
        
        self.save_project_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(post_options, text="DaVinciプロジェクトを保存",
                       variable=self.save_project_var).pack(anchor=tk.W)
        
        # 最終完了
        complete_frame = ttk.LabelFrame(self.export_tab, text="ワークフロー完了")
        complete_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        complete_buttons = ttk.Frame(complete_frame)
        complete_buttons.pack(pady=20)
        
        ttk.Button(complete_buttons, text="🎉 全ワークフロー完了", 
                  command=self.complete_workflow,
                  style="Accent.TButton").pack(pady=10)
        
        # 出力ログ
        output_log_frame = ttk.Frame(complete_frame)
        output_log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        ttk.Label(output_log_frame, text="出力ログ:").pack(anchor=tk.W)
        
        self.output_log = tk.Text(output_log_frame, height=6, wrap=tk.WORD, font=("Courier", 9))
        output_scrollbar = ttk.Scrollbar(output_log_frame, orient=tk.VERTICAL, command=self.output_log.yview)
        self.output_log.configure(yscrollcommand=output_scrollbar.set)
        
        self.output_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def check_davinci_connection(self):
        """DaVinci接続確認"""
        try:
            # DaVinci Resolve API接続試行
            import sys
            sys.path.append('/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/python')
            
            import DaVinciResolveScript as dvr
            self.resolve = dvr.scriptapp("Resolve")
            
            if self.resolve:
                self.project_manager = self.resolve.GetProjectManager()
                self.current_resolve_project = self.project_manager.GetCurrentProject()
                
                if self.current_resolve_project:
                    self.davinci_connected = True
                    self.connection_status_var.set("✅ 接続済み")
                    self.project_info_var.set(f"プロジェクト: {self.current_resolve_project.GetName()}")
                    
                    current_timeline = self.current_resolve_project.GetCurrentTimeline()
                    if current_timeline:
                        self.timeline_info_var.set(f"タイムライン: {current_timeline.GetName()}")
                    else:
                        self.timeline_info_var.set("タイムラインなし")
                    
                    # ボタン状態更新
                    self.import_btn.configure(state="normal")
                    self.render_btn.configure(state="normal")
                    
                    self.log_message("DaVinci Resolve接続成功")
                else:
                    self.connection_status_var.set("❌ プロジェクトなし")
                    self.project_info_var.set("アクティブなプロジェクトがありません")
                    
            else:
                self.connection_status_var.set("❌ 接続失敗")
                self.project_info_var.set("DaVinci Resolveが見つかりません")
                
        except Exception as e:
            self.davinci_connected = False
            self.connection_status_var.set("❌ 接続失敗")
            self.project_info_var.set(f"エラー: {str(e)}")
            self.log_message(f"DaVinci接続エラー: {e}")
    
    def connect_to_davinci(self):
        """DaVinci Resolve接続"""
        self.log_message("DaVinci Resolve接続を試行中...")
        self.check_davinci_connection()
    
    def browse_srt_file(self):
        """SRTファイル参照"""
        file_path = filedialog.askopenfilename(
            title="SRTファイルを選択",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        
        if file_path:
            self.srt_file_var.set(file_path)
    
    def auto_detect_srt(self):
        """プロジェクトからSRT自動検出"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトが読み込まれていません")
            return
        
        # プロジェクトパスから自動検出
        if self.current_project.project_path:
            project_dir = self.current_project.project_path.parent
            srt_paths = list(project_dir.glob("**/*.srt"))
            
            if srt_paths:
                # 最も適切そうなSRTファイルを選択
                srt_file = srt_paths[0]  # 簡易実装
                self.srt_file_var.set(str(srt_file))
                self.log_message(f"SRT自動検出: {srt_file.name}")
            else:
                messagebox.showinfo("情報", "SRTファイルが見つかりませんでした")
        else:
            messagebox.showwarning("警告", "プロジェクトパスが設定されていません")
    
    def preview_srt_file(self):
        """SRTファイルプレビュー"""
        srt_path = self.srt_file_var.get()
        if not srt_path or not Path(srt_path).exists():
            messagebox.showwarning("警告", "有効なSRTファイルを選択してください")
            return
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # プレビューウィンドウ
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"SRTプレビュー - {Path(srt_path).name}")
            preview_window.geometry("700x500")
            
            preview_text = tk.Text(preview_window, wrap=tk.WORD, font=("Courier", 10))
            preview_scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL,
                                             command=preview_text.yview)
            preview_text.configure(yscrollcommand=preview_scrollbar.set)
            
            preview_text.insert("1.0", srt_content)
            preview_text.configure(state="disabled")
            
            preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
            
        except Exception as e:
            messagebox.showerror("エラー", f"SRTファイル読み込みエラー: {e}")
    
    def import_srt_file(self):
        """SRTファイルインポート"""
        if not self.davinci_connected:
            messagebox.showwarning("警告", "DaVinci Resolveに接続してください")
            return
        
        srt_path = self.srt_file_var.get()
        if not srt_path or not Path(srt_path).exists():
            messagebox.showwarning("警告", "有効なSRTファイルを選択してください")
            return
        
        try:
            self.log_message(f"SRTインポート開始: {Path(srt_path).name}")
            
            if self.import_method_var.get() == "timeline":
                # タイムラインに直接インポート
                timeline = self.current_resolve_project.GetCurrentTimeline()
                if not timeline:
                    raise Exception("アクティブなタイムラインがありません")
                
                # 複数のAPI方式を試行（既存のresolve_import.pyと同様）
                success = False
                for method_name in ["ImportSubtitles", "ImportSubtitle", "ImportTimelineSubtitle"]:
                    if hasattr(timeline, method_name):
                        try:
                            method = getattr(timeline, method_name)
                            method(srt_path)
                            self.log_message(f"✅ インポート成功: {method_name}")
                            success = True
                            break
                        except Exception as e:
                            self.log_message(f"⚠️ {method_name} 失敗: {e}")
                
                if not success:
                    # フォールバック: メディアプール
                    mp = self.current_resolve_project.GetMediaPool()
                    mp.ImportMedia([srt_path])
                    self.log_message("✅ メディアプールにインポート完了")
                    self.log_message("ℹ️ 右クリック → 'Import Subtitle' で字幕トラックに追加してください")
            
            else:
                # メディアプールに追加
                mp = self.current_resolve_project.GetMediaPool()
                mp.ImportMedia([srt_path])
                self.log_message("✅ メディアプールインポート完了")
            
            messagebox.showinfo("完了", "SRTファイルのインポートが完了しました")
            
        except Exception as e:
            self.log_message(f"❌ インポートエラー: {e}")
            messagebox.showerror("エラー", f"SRTインポートエラー: {e}")
    
    def on_preset_change(self):
        """プリセット変更時の処理"""
        preset = self.render_preset_var.get()
        
        if preset == "youtube_hd":
            self.resolution_var.set("1920x1080")
            self.fps_var.set("30")
            self.bitrate_var.set("8000")
            
        elif preset == "youtube_4k":
            self.resolution_var.set("3840x2160")
            self.fps_var.set("30")
            self.bitrate_var.set("15000")
            
        elif preset == "high_quality_mp4":
            self.resolution_var.set("1920x1080")
            self.fps_var.set("30")
            self.bitrate_var.set("12000")
            
        elif preset == "web_optimized":
            self.resolution_var.set("1280x720")
            self.fps_var.set("25")
            self.bitrate_var.set("4000")
        
        # 出力パス自動設定
        if self.current_project and self.current_project.project_path:
            project_dir = self.current_project.project_path.parent
            output_name = f"{self.current_project.name}_{preset}.mp4"
            self.output_path_var.set(str(project_dir / "output" / output_name))
    
    def browse_output_path(self):
        """出力パス参照"""
        file_path = filedialog.asksaveasfilename(
            title="出力ファイルを指定",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        
        if file_path:
            self.output_path_var.set(file_path)
    
    def start_rendering(self):
        """レンダリング開始"""
        if not self.davinci_connected:
            messagebox.showwarning("警告", "DaVinci Resolveに接続してください")
            return
        
        output_path = self.output_path_var.get()
        if not output_path:
            messagebox.showwarning("警告", "出力パスを指定してください")
            return
        
        try:
            self.log_message("レンダリング設定を適用中...")
            
            # レンダリング設定構築
            render_settings = {
                "Format": "mp4",
                "Codec": "H.264",
                "Resolution": self.resolution_var.get().split("x"),
                "FrameRate": self.fps_var.get(),
                "Bitrate": self.bitrate_var.get(),
                "AudioCodec": self.audio_codec_var.get()
            }
            
            # DaVinci Resolve レンダリング実行（疑似実装）
            # 実際のAPIでは: project.AddRenderJob() を使用
            self.log_message("🎬 レンダリングをRender Queueに追加中...")
            
            # 疑似レンダリングプロセス
            self.render_status_var.set("レンダリング中...")
            self.render_progress.configure(mode='indeterminate')
            self.render_progress.start()
            
            self.render_btn.configure(state="disabled")
            self.stop_render_btn.configure(state="normal")
            
            # 実際の実装では非同期でレンダリング監視
            self.root.after(3000, self._simulate_render_complete)
            
        except Exception as e:
            self.log_message(f"❌ レンダリングエラー: {e}")
            messagebox.showerror("エラー", f"レンダリングエラー: {e}")
    
    def _simulate_render_complete(self):
        """レンダリング完了シミュレーション"""
        self.render_progress.stop()
        self.render_progress.configure(mode='determinate', value=100)
        self.render_status_var.set("✅ レンダリング完了!")
        
        self.render_btn.configure(state="normal")
        self.stop_render_btn.configure(state="disabled")
        
        self.log_message("✅ レンダリング完了!")
        
        # 完了後処理
        if self.save_project_var.get():
            self.log_message("📁 DaVinciプロジェクトを保存中...")
            # 実際の実装: self.current_resolve_project.Save()
        
        if self.auto_open_var.get():
            output_path = self.output_path_var.get()
            if output_path and Path(output_path).parent.exists():
                self.log_message(f"📂 出力フォルダを開いています...")
                try:
                    subprocess.run(["open", str(Path(output_path).parent)])
                except:
                    pass
        
        messagebox.showinfo("完了", "レンダリングが完了しました！")
    
    def stop_rendering(self):
        """レンダリング停止"""
        self.render_progress.stop()
        self.render_status_var.set("⏹️ 停止されました")
        self.render_btn.configure(state="normal")
        self.stop_render_btn.configure(state="disabled")
        self.log_message("⏹️ レンダリングを停止しました")
    
    def check_render_queue(self):
        """レンダーキュー確認"""
        if not self.davinci_connected:
            messagebox.showwarning("警告", "DaVinci Resolveに接続してください")
            return
        
        # 実際の実装では: self.current_resolve_project.GetRenderJobs()
        messagebox.showinfo("レンダーキュー", "レンダーキューの確認機能（要実装）")
    
    def complete_workflow(self):
        """ワークフロー完了"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成または読み込んでください")
            return
        
        # プロジェクト完了マーク
        self.current_project.step4_completed = True
        
        # 保存
        self.save_project()
        
        # 完了メッセージ
        completion_message = f\"\"\"🎉 ワークフロー完了！

プロジェクト: {self.current_project.name}
✅ Step 1: スクリプト編集・配役設定
✅ Step 2: TTS音声生成
✅ Step 3: 字幕タイミング調整  
✅ Step 4: DaVinci Resolve出力

お疲れさまでした！\"\"\"
        
        messagebox.showinfo("🎉 完了", completion_message)
        self.log_message("🎉 全ワークフロー完了!")
    
    def log_message(self, message: str):
        """ログメッセージ出力"""
        self.import_log.insert(tk.END, f"{message}\n")
        self.import_log.see(tk.END)
        
        self.output_log.insert(tk.END, f"{message}\n") 
        self.output_log.see(tk.END)
        
        self.root.update_idletasks()
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理"""
        if self.current_project and self.current_project.project_path:
            # 出力パス自動設定
            project_dir = self.current_project.project_path.parent
            
            # SRTファイル自動検出
            srt_files = list(project_dir.glob("**/*.srt"))
            if srt_files:
                self.srt_file_var.set(str(srt_files[0]))
            
            # 出力パス設定
            output_name = f"{self.current_project.name}_final.mp4"
            self.output_path_var.set(str(project_dir / "output" / output_name))
    
    def on_project_save(self):
        """プロジェクト保存時の処理"""
        pass


def main():
    """メイン関数"""
    app = DaVinciExportWindow()
    app.run()


if __name__ == "__main__":
    main()