#!/usr/bin/env python3
"""
Integrated Video Production Workspace
統合動画制作ワークスペース - 真の統合GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinter.simpledialog
from pathlib import Path
import sys
import json
import os
import csv
from typing import List, Dict, Optional
import threading
import time
import datetime

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))
sys.path.append(str(Path(__file__).parent.parent / "minivt_pipeline" / "src"))

from data_models import Project, ScriptLine, Character
from utils.voice_parser import VoiceInstructionParser

class IntegratedWorkspace:
    """統合動画制作ワークスペース"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 DaVinci Auto - 統合ワークスペース")
        self.root.geometry("1600x1000")
        
        # プロジェクト管理
        self.current_project: Optional[Project] = None
        self.project_file: Optional[Path] = None
        self.voice_parser = VoiceInstructionParser()
        
        # GUI状態管理
        self.current_step = 1
        self.step_completion_status = [False, False, False, False]
        
        # メインGUI構築
        self.setup_main_layout()
        self.setup_toolbar()
        self.setup_step_tabs()
        self.setup_status_bar()
        
        # 初期状態
        self.create_sample_project()  # デモ用
        self.update_all_displays()
    
    def setup_main_layout(self):
        """メインレイアウト設定"""
        # メインフレーム
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_toolbar(self):
        """ツールバー"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # プロジェクト管理
        project_frame = ttk.LabelFrame(toolbar, text="プロジェクト")
        project_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(project_frame, text="新規", command=self.new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(project_frame, text="開く", command=self.open_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(project_frame, text="保存", command=self.save_project).pack(side=tk.LEFT, padx=2)
        
        # プロジェクト情報表示
        info_frame = ttk.LabelFrame(toolbar, text="プロジェクト情報")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.project_name_var = tk.StringVar(value="プロジェクト未選択")
        ttk.Label(info_frame, text="名前:").pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, textvariable=self.project_name_var, font=("", 10, "bold")).pack(side=tk.LEFT)
        
        # 進捗表示
        progress_frame = ttk.LabelFrame(toolbar, text="進捗")
        progress_frame.pack(side=tk.RIGHT)

        self.progress_var = tk.StringVar(value="0/4 完了")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(padx=10)

        # エクスポート
        export_frame = ttk.LabelFrame(toolbar, text="エクスポート")
        export_frame.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(export_frame, text="CSV（縦）エクスポート", command=self.export_csv_vertical).pack(padx=6)
    
    def setup_step_tabs(self):
        """ステップタブ設定"""
        # タブ制御フレーム
        tab_control_frame = ttk.Frame(self.main_frame)
        tab_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ステップナビゲーション
        nav_frame = ttk.LabelFrame(tab_control_frame, text="ステップナビゲーション")
        nav_frame.pack(fill=tk.X)
        
        self.step_buttons = []
        self.step_status_vars = []
        
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(pady=10)
        
        steps = [
            ("📝 Step 1: スクリプト編集", 1),
            ("🎵 Step 2: TTS音声生成", 2), 
            ("⏰ Step 3: 字幕タイミング", 3),
            ("🎬 Step 4: DaVinci出力", 4)
        ]
        
        for title, step_num in steps:
            btn = ttk.Button(button_frame, text=title, 
                           command=lambda s=step_num: self.switch_to_step(s))
            btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            self.step_buttons.append(btn)
            
            # ステータス表示
            status_var = tk.StringVar(value="未完了")
            self.step_status_vars.append(status_var)
        
        # ステータス表示行
        status_frame = ttk.Frame(nav_frame)
        status_frame.pack(fill=tk.X, pady=(5, 10))
        
        for i, status_var in enumerate(self.step_status_vars):
            ttk.Label(status_frame, textvariable=status_var, 
                     font=("", 9), foreground="orange").pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # メインコンテンツ（ステップ表示エリア）
        self.content_notebook = ttk.Notebook(self.main_frame)
        self.content_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 各ステップのフレーム作成
        self.step1_frame = ttk.Frame(self.content_notebook)
        self.step2_frame = ttk.Frame(self.content_notebook)
        self.step3_frame = ttk.Frame(self.content_notebook)
        self.step4_frame = ttk.Frame(self.content_notebook)
        # テキスト調整（追加タブ）
        self.text_adjust_frame = ttk.Frame(self.content_notebook)
        
        self.content_notebook.add(self.step1_frame, text="📝 スクリプト編集")
        self.content_notebook.add(self.step2_frame, text="🎵 TTS音声生成")
        self.content_notebook.add(self.step3_frame, text="⏰ 字幕タイミング")
        self.content_notebook.add(self.step4_frame, text="🎬 DaVinci出力")
        self.content_notebook.add(self.text_adjust_frame, text="🧠 テキスト調整")
        
        # 各ステップの内容設定
        self.setup_step1_content()
        self.setup_step2_content()
        self.setup_step3_content()
        self.setup_step4_content()
        self.setup_text_adjustment_content()
        
        # タブ変更イベント
        self.content_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def setup_step1_content(self):
        """Step 1: スクリプト編集コンテンツ"""
        # 左右分割
        paned = ttk.PanedWindow(self.step1_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側: スクリプトエディタ
        editor_frame = ttk.LabelFrame(paned, text="スクリプト編集")
        paned.add(editor_frame, weight=2)
        
        # エディタツール
        editor_tools = ttk.Frame(editor_frame)
        editor_tools.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(editor_tools, text="📁 ファイル読み込み", 
                  command=self.load_script_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(editor_tools, text="💾 スクリプト保存", 
                  command=self.save_script).pack(side=tk.LEFT, padx=5)
        ttk.Button(editor_tools, text="🔄 解析更新", 
                  command=self.parse_script).pack(side=tk.LEFT, padx=5)
        
        # テキストエディタ
        self.script_editor = tk.Text(editor_frame, wrap=tk.WORD, font=("Consolas", 11), 
                                   undo=True, height=20)
        editor_scroll = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.script_editor.yview)
        self.script_editor.configure(yscrollcommand=editor_scroll.set)
        
        self.script_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=(5, 10))
        editor_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 10))
        
        # テキスト変更監視
        self.script_editor.bind("<KeyRelease>", self.on_script_change)
        
        # 右側: キャラクター管理
        char_frame = ttk.LabelFrame(paned, text="キャラクター管理")
        paned.add(char_frame, weight=1)
        
        # キャラクター一覧
        char_tools = ttk.Frame(char_frame)
        char_tools.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(char_tools, text="検出キャラクター:").pack(side=tk.LEFT)
        ttk.Button(char_tools, text="追加", command=self.add_character).pack(side=tk.RIGHT)
        
        # キャラクター表
        columns = ("name", "gender", "voice_id")
        self.character_tree = ttk.Treeview(char_frame, columns=columns, show="headings", height=8)
        
        self.character_tree.heading("name", text="名前")
        self.character_tree.heading("gender", text="性別")
        self.character_tree.heading("voice_id", text="音声ID")
        
        char_scroll = ttk.Scrollbar(char_frame, orient=tk.VERTICAL, command=self.character_tree.yview)
        self.character_tree.configure(yscrollcommand=char_scroll.set)
        
        self.character_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=5)
        char_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Step 1 完了ボタン
        step1_complete = ttk.Frame(self.step1_frame)
        step1_complete.pack(fill=tk.X, pady=10)
        
        ttk.Button(step1_complete, text="✅ Step 1 完了 → Step 2へ", 
                  command=lambda: self.complete_step(1), 
                  style="Accent.TButton").pack()
    
    def setup_step2_content(self):
        """Step 2: TTS音声生成コンテンツ"""
        # 上下分割
        paned = ttk.PanedWindow(self.step2_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上部: スクリプト一覧
        script_frame = ttk.LabelFrame(paned, text="生成対象スクリプト")
        paned.add(script_frame, weight=1)
        
        # スクリプト一覧表
        columns = ("line", "role", "character", "text", "status")
        self.tts_script_tree = ttk.Treeview(script_frame, columns=columns, show="headings")
        
        self.tts_script_tree.heading("line", text="#")
        self.tts_script_tree.heading("role", text="種類")
        self.tts_script_tree.heading("character", text="キャラ")
        self.tts_script_tree.heading("text", text="テキスト")
        self.tts_script_tree.heading("status", text="生成状況")
        
        tts_scroll = ttk.Scrollbar(script_frame, orient=tk.VERTICAL, command=self.tts_script_tree.yview)
        self.tts_script_tree.configure(yscrollcommand=tts_scroll.set)
        
        self.tts_script_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        tts_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # 下部: 生成制御
        control_frame = ttk.LabelFrame(paned, text="TTS生成制御")
        paned.add(control_frame, weight=1)
        
        # 進捗表示
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(progress_frame, text="生成進捗:").pack(anchor=tk.W)
        self.tts_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.tts_progress.pack(fill=tk.X, pady=5)
        
        self.tts_status_var = tk.StringVar(value="待機中...")
        ttk.Label(progress_frame, textvariable=self.tts_status_var).pack(anchor=tk.W)
        
        # 制御ボタン
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.tts_generate_btn = ttk.Button(button_frame, text="🎵 TTS生成開始", 
                                          command=self.start_tts_generation)
        self.tts_generate_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🎧 テスト再生", 
                  command=self.test_tts_playback).pack(side=tk.LEFT, padx=5)
        
        # Step 2 完了ボタン
        step2_complete = ttk.Frame(self.step2_frame)
        step2_complete.pack(fill=tk.X, pady=10)
        
        ttk.Button(step2_complete, text="✅ Step 2 完了 → Step 3へ", 
                  command=lambda: self.complete_step(2), 
                  style="Accent.TButton").pack()
    
    def setup_step3_content(self):
        """Step 3: 字幕タイミングコンテンツ"""
        # 上下分割
        paned = ttk.PanedWindow(self.step3_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上部: タイムライン表示
        timeline_frame = ttk.LabelFrame(paned, text="字幕タイムライン")
        paned.add(timeline_frame, weight=2)
        
        # タイムライン制御
        timeline_tools = ttk.Frame(timeline_frame)
        timeline_tools.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(timeline_tools, text="🔄 自動タイミング生成", 
                  command=self.auto_generate_timing).pack(side=tk.LEFT, padx=5)
        ttk.Button(timeline_tools, text="📁 音声フォルダ読み込み", 
                  command=self.load_audio_folder).pack(side=tk.LEFT, padx=5)
        
        # タイムライン表
        columns = ("cue", "start", "end", "duration", "text")
        self.timeline_tree = ttk.Treeview(timeline_frame, columns=columns, show="headings")
        
        self.timeline_tree.heading("cue", text="#")
        self.timeline_tree.heading("start", text="開始")
        self.timeline_tree.heading("end", text="終了")
        self.timeline_tree.heading("duration", text="長さ")
        self.timeline_tree.heading("text", text="テキスト")
        
        timeline_scroll = ttk.Scrollbar(timeline_frame, orient=tk.VERTICAL, command=self.timeline_tree.yview)
        self.timeline_tree.configure(yscrollcommand=timeline_scroll.set)
        
        self.timeline_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=(5, 10))
        timeline_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 10))
        
        # 下部: 編集制御
        edit_frame = ttk.LabelFrame(paned, text="字幕編集・出力")
        paned.add(edit_frame, weight=1)
        
        # 出力ボタン
        output_frame = ttk.Frame(edit_frame)
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(output_frame, text="💾 SRT保存", 
                  command=self.save_srt_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_frame, text="👁️ プレビュー", 
                  command=self.preview_subtitles).pack(side=tk.LEFT, padx=5)
        
        # Step 3 完了ボタン
        step3_complete = ttk.Frame(self.step3_frame)
        step3_complete.pack(fill=tk.X, pady=10)
        
        ttk.Button(step3_complete, text="✅ Step 3 完了 → Step 4へ", 
                  command=lambda: self.complete_step(3), 
                  style="Accent.TButton").pack()
    
    def setup_step4_content(self):
        """Step 4: DaVinci出力コンテンツ"""
        # 左右分割
        paned = ttk.PanedWindow(self.step4_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側: DaVinci接続・設定
        davinci_frame = ttk.LabelFrame(paned, text="DaVinci Resolve連携")
        paned.add(davinci_frame, weight=1)
        
        # 接続状態
        connection_frame = ttk.Frame(davinci_frame)
        connection_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(connection_frame, text="接続状態:").pack(anchor=tk.W)
        self.davinci_status_var = tk.StringVar(value="未接続")
        ttk.Label(connection_frame, textvariable=self.davinci_status_var, 
                 font=("", 10, "bold"), foreground="red").pack(anchor=tk.W, pady=5)
        
        ttk.Button(connection_frame, text="🔗 DaVinci接続", 
                  command=self.connect_davinci).pack(pady=5)
        
        # SRTインポート
        import_frame = ttk.Frame(davinci_frame)
        import_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(import_frame, text="SRTファイル:").pack(anchor=tk.W)
        self.srt_path_var = tk.StringVar()
        ttk.Entry(import_frame, textvariable=self.srt_path_var, state="readonly").pack(fill=tk.X, pady=2)
        
        ttk.Button(import_frame, text="📥 SRTインポート", 
                  command=self.import_srt_to_davinci).pack(pady=5)
        
        # 右側: レンダリング設定・出力
        render_frame = ttk.LabelFrame(paned, text="レンダリング・出力")
        paned.add(render_frame, weight=1)
        
        # プリセット選択
        preset_frame = ttk.Frame(render_frame)
        preset_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(preset_frame, text="出力プリセット:").pack(anchor=tk.W)
        self.render_preset_var = tk.StringVar(value="YouTube HD (1080p)")
        presets = ["YouTube HD (1080p)", "YouTube 4K (2160p)", "高品質MP4", "Web配信用"]
        ttk.Combobox(preset_frame, textvariable=self.render_preset_var, 
                    values=presets, state="readonly").pack(fill=tk.X, pady=5)
        
        # レンダリング制御
        render_control = ttk.Frame(render_frame)
        render_control.pack(fill=tk.X, padx=10, pady=10)
        
        self.render_progress = ttk.Progressbar(render_control, mode='determinate')
        self.render_progress.pack(fill=tk.X, pady=5)
        
        self.render_status_var = tk.StringVar(value="待機中...")
        ttk.Label(render_control, textvariable=self.render_status_var).pack(anchor=tk.W)
        
        ttk.Button(render_control, text="🎬 レンダリング開始", 
                  command=self.start_rendering).pack(pady=5)
        
        # Step 4 完了ボタン
        step4_complete = ttk.Frame(self.step4_frame)
        step4_complete.pack(fill=tk.X, pady=10)
        
        ttk.Button(step4_complete, text="🎉 全ワークフロー完了！", 
                  command=lambda: self.complete_step(4), 
                  style="Accent.TButton").pack()
    
    def setup_status_bar(self):
        """ステータスバー"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready - 統合ワークスペースが起動しました")
        ttk.Label(self.status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 時刻表示
        self.time_var = tk.StringVar()
        ttk.Label(self.status_frame, textvariable=self.time_var).pack(side=tk.RIGHT)
        self.update_time()
    
    def update_time(self):
        """時刻更新"""
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(now)
        self.root.after(1000, self.update_time)
    
    # === プロジェクト管理 ===
    
    def new_project(self):
        """新規プロジェクト"""
        name = tk.simpledialog.askstring("新規プロジェクト", "プロジェクト名:")
        if name:
            self.current_project = Project(name=name)
            self.project_file = None
            self.project_name_var.set(name)
            self.update_all_displays()
            self.set_status(f"新規プロジェクト '{name}' を作成しました")
    
    def open_project(self):
        """プロジェクト読み込み"""
        file_path = filedialog.askopenfilename(
            title="プロジェクトを開く",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.current_project = Project.load_from_file(Path(file_path))
                self.project_file = Path(file_path)
                self.project_name_var.set(self.current_project.name)
                self.update_all_displays()
                self.set_status(f"プロジェクト '{self.current_project.name}' を読み込みました")
            except Exception as e:
                messagebox.showerror("エラー", f"プロジェクト読み込みエラー: {e}")
    
    def save_project(self):
        """プロジェクト保存"""
        if not self.current_project:
            messagebox.showwarning("警告", "保存するプロジェクトがありません")
            return
        
        if not self.project_file:
            file_path = filedialog.asksaveasfilename(
                title="プロジェクトを保存",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            if file_path:
                self.project_file = Path(file_path)
            else:
                return
        
        try:
            # 現在の編集内容を保存
            self.save_current_step_data()
            self.current_project.save_to_file(self.project_file)
            self.set_status(f"プロジェクト '{self.current_project.name}' を保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクト保存エラー: {e}")
    
    def create_sample_project(self):
        """サンプルプロジェクト作成（デモ用）"""
        self.current_project = Project(name="デモプロジェクト")
        
        sample_script = """NA: 転職した同期の投稿を見て 焦りを感じたことはありませんか
NA: 転職は脱出なのか それとも逃避なのか
セリフ: 同僚A（女声・つぶやくように）：うちの会社 もう限界かもね
NA: 金曜日の飲み会 愚痴と不満のオンパレード
セリフ: モーセ（男声・力強く）：エジプトにいた方がよかった
NA: 自由の荒野で 民は奴隷時代を懐かしみ始めたのです"""
        
        self.current_project.script_text = sample_script
        self.project_name_var.set(self.current_project.name)
        
        # スクリプトエディタに反映
        self.script_editor.delete("1.0", tk.END)
        self.script_editor.insert("1.0", sample_script)
        
        self.set_status("デモプロジェクトを作成しました")
    
    # === ステップ管理 ===
    
    def switch_to_step(self, step_num: int):
        """ステップ切り替え"""
        self.current_step = step_num
        self.content_notebook.select(step_num - 1)
        self.update_step_buttons()
        self.set_status(f"Step {step_num} に切り替えました")
    
    def on_tab_changed(self, event):
        """タブ変更時の処理"""
        selected_tab = self.content_notebook.select()
        tab_index = self.content_notebook.index(selected_tab)
        self.current_step = tab_index + 1
        self.update_step_buttons()
    
    def complete_step(self, step_num: int):
        """ステップ完了"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成してください")
            return
        
        # ステップデータ保存
        self.save_current_step_data()
        
        # 完了状態更新
        self.step_completion_status[step_num - 1] = True
        
        if step_num == 1:
            self.current_project.step1_completed = True
        elif step_num == 2:
            self.current_project.step2_completed = True
        elif step_num == 3:
            self.current_project.step3_completed = True
        elif step_num == 4:
            self.current_project.step4_completed = True
        
        # 表示更新
        self.update_step_status()
        
        if step_num < 4:
            # 次のステップに移動
            response = messagebox.askyesno(
                f"Step {step_num} 完了", 
                f"Step {step_num} が完了しました。Step {step_num + 1} に進みますか？"
            )
            if response:
                self.switch_to_step(step_num + 1)
        else:
            # 全完了
            messagebox.showinfo("🎉 完了", "全ワークフローが完了しました！\nお疲れさまでした！")
        
        self.set_status(f"Step {step_num} を完了しました")
    
    def save_current_step_data(self):
        """現在のステップのデータを保存"""
        if not self.current_project:
            return
        
        if self.current_step == 1:
            # スクリプトテキストを保存
            self.current_project.script_text = self.script_editor.get("1.0", tk.END).strip()
            # スクリプト解析
            self.parse_script()
    
    # === Step 1: スクリプト編集 ===
    
    def load_script_file(self):
        """スクリプトファイル読み込み"""
        file_path = filedialog.askopenfilename(
            title="スクリプトファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.script_editor.delete("1.0", tk.END)
                self.script_editor.insert("1.0", content)
                self.parse_script()
                self.set_status(f"スクリプトファイルを読み込みました: {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("エラー", f"ファイル読み込みエラー: {e}")
    
    def save_script(self):
        """スクリプト保存"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成してください")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="スクリプトを保存",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                content = self.script_editor.get("1.0", tk.END).strip()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.set_status(f"スクリプトを保存しました: {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("エラー", f"保存エラー: {e}")
    
    def on_script_change(self, event=None):
        """スクリプト変更時の処理"""
        # 少し遅延してから解析実行（連続入力対応）
        self.root.after(1000, self.parse_script)
    
    def parse_script(self):
        """スクリプト解析"""
        if not self.current_project:
            return

        script_text = self.script_editor.get("1.0", tk.END).strip()
        self.current_project.script_text = script_text

        # スクリプト行解析
        lines = []
        characters = set()
        # 既存行の保存（行番号ベース）
        existing_by_ln = {}
        for old in (self.current_project.script_lines or []):
            existing_by_ln[(old.line_number, old.role, (old.character or ""))] = old
        
        for line_num, line in enumerate(script_text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("NA:"):
                role = "NA"
                text = line.replace("NA:", "", 1).strip()
                script_line = ScriptLine(role=role, text=text, line_number=line_num)
                
            elif line.startswith("セリフ:"):
                role = "DL"
                content = line.replace("セリフ:", "", 1).strip()
                
                # キャラクター名抽出
                import re
                char_match = re.match(r'^([^（：]+)', content)
                if char_match:
                    character = char_match.group(1).strip()
                    characters.add(character)
                    text = content[len(character):].strip()
                    if text.startswith(("：", ":")):
                        text = text[1:].strip()
                    script_line = ScriptLine(role=role, text=text, character=character, line_number=line_num)
                else:
                    script_line = ScriptLine(role=role, text=content, line_number=line_num)
            else:
                # 不明な行形式はスキップ
                continue
            
            # 既存フィールドを引き継ぎ
            key = (script_line.line_number, script_line.role, (script_line.character or ""))
            old = existing_by_ln.get(key)
            if old:
                script_line.voice_instruction = old.voice_instruction
                script_line.voice_id = old.voice_id or script_line.voice_id
                script_line.voice_settings = old.voice_settings or script_line.voice_settings
                script_line.final_text = old.final_text
                script_line.storyboard = old.storyboard
                script_line.telop = old.telop
                script_line.bgm_tag = old.bgm_tag
                script_line.tts_rate = old.tts_rate
                script_line.locked = old.locked
                script_line.notes = old.notes

            lines.append(script_line)
        
        self.current_project.script_lines = lines
        
        # キャラクター更新
        self.update_character_list(characters)
        
        # TTS画面更新
        self.update_tts_display()
        # テキスト調整画面更新
        self.update_text_adjustment_display()
        
        self.set_status(f"スクリプト解析完了: {len(lines)}行, {len(characters)}キャラクター")

    # === テキスト調整タブ ===
    def setup_text_adjustment_content(self):
        """テキスト調整（LLM候補・最終文・文字コンテ・BGM・注釈）"""
        paned = ttk.PanedWindow(self.text_adjust_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左: 行リスト
        list_frame = ttk.LabelFrame(paned, text="行リスト（縦）")
        paned.add(list_frame, weight=2)

        columns = ("line", "role", "character", "original", "final", "story", "telop", "bgm")
        self.textadj_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col, label in [
            ("line", "#"), ("role", "種類"), ("character", "キャラ"), ("original", "オリジナル"),
            ("final", "最終文"), ("story", "文字コンテ"), ("telop", "テロップ"), ("bgm", "BGM")
        ]:
            self.textadj_tree.heading(col, text=label)
        self.textadj_tree.column("line", width=50, anchor=tk.CENTER)
        self.textadj_tree.column("role", width=60, anchor=tk.CENTER)
        self.textadj_tree.column("character", width=120)
        self.textadj_tree.column("original", width=260)
        self.textadj_tree.column("final", width=260)
        self.textadj_tree.column("story", width=160)
        self.textadj_tree.column("telop", width=160)
        self.textadj_tree.column("bgm", width=100)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.textadj_tree.yview)
        self.textadj_tree.configure(yscrollcommand=tree_scroll.set)
        self.textadj_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        self.textadj_tree.bind("<<TreeviewSelect>>", self.on_text_adjust_select)

        # 右: 詳細エディタ
        detail_frame = ttk.LabelFrame(paned, text="詳細エディタ")
        paned.add(detail_frame, weight=3)

        # オリジナル（読み取り専用）
        ttk.Label(detail_frame, text="オリジナル").pack(anchor=tk.W, padx=10)
        self.ta_original = scrolledtext.ScrolledText(detail_frame, height=5, wrap=tk.WORD, state="disabled")
        self.ta_original.pack(fill=tk.X, padx=10, pady=(0, 10))

        # 編集タブ
        editor_nb = ttk.Notebook(detail_frame)
        editor_nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ナレーション原稿
        narr_frame = ttk.Frame(editor_nb)
        editor_nb.add(narr_frame, text="ナレーション原稿")
        self.ta_final = scrolledtext.ScrolledText(narr_frame, height=8, wrap=tk.WORD)
        self.ta_final.pack(fill=tk.BOTH, expand=True)

        # 文字コンテ
        story_frame = ttk.Frame(editor_nb)
        editor_nb.add(story_frame, text="文字コンテ")
        self.ta_story = scrolledtext.ScrolledText(story_frame, height=6, wrap=tk.WORD)
        self.ta_story.pack(fill=tk.BOTH, expand=True)

        # 注釈テロップ
        telop_frame = ttk.Frame(editor_nb)
        editor_nb.add(telop_frame, text="注釈テロップ")
        self.ta_telop = scrolledtext.ScrolledText(telop_frame, height=4, wrap=tk.WORD)
        self.ta_telop.pack(fill=tk.BOTH, expand=True)

        # BGM／話速など
        meta_frame = ttk.Frame(detail_frame)
        meta_frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(meta_frame, text="BGMタグ:").pack(side=tk.LEFT)
        self.var_bgm = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.var_bgm).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(meta_frame, text="話速:").pack(side=tk.LEFT, padx=(10, 0))
        self.var_rate = tk.DoubleVar(value=1.0)
        ttk.Spinbox(meta_frame, from_=0.5, to=2.0, increment=0.05, textvariable=self.var_rate, width=6).pack(side=tk.LEFT, padx=5)
        self.var_locked = tk.BooleanVar(value=False)
        ttk.Checkbutton(meta_frame, text="ロック", variable=self.var_locked).pack(side=tk.LEFT, padx=10)

        # メモ
        notes_frame = ttk.Frame(detail_frame)
        notes_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        ttk.Label(notes_frame, text="メモ:").pack(anchor=tk.W)
        self.ta_notes = scrolledtext.ScrolledText(notes_frame, height=3, wrap=tk.WORD)
        self.ta_notes.pack(fill=tk.BOTH, expand=True)

        # 操作ボタン
        btns = ttk.Frame(detail_frame)
        btns.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btns, text="保存", command=self.save_text_adjust_changes).pack(side=tk.LEFT)
        ttk.Button(btns, text="CSV（縦）エクスポート", command=self.export_csv_vertical).pack(side=tk.RIGHT)

        # 内部選択状態
        self._textadj_selected_ln = None

    def update_text_adjustment_display(self):
        """テキスト調整の行リスト更新"""
        if not hasattr(self, 'textadj_tree'):
            return
        for item in self.textadj_tree.get_children():
            self.textadj_tree.delete(item)
        if not self.current_project:
            return
        for sl in (self.current_project.script_lines or []):
            orig = sl.text
            fin = sl.final_text or ""
            story = ("✓" if sl.storyboard.strip() else "")
            tel = ("✓" if sl.telop.strip() else "")
            bgm = sl.bgm_tag or ""
            def trunc(s, n):
                return (s[:n] + "...") if len(s) > n else s
            self.textadj_tree.insert("", tk.END, values=(
                sl.line_number,
                sl.role,
                sl.character or "-",
                trunc(orig, 40),
                trunc(fin, 40),
                story,
                tel,
                bgm
            ))

    def on_text_adjust_select(self, event=None):
        sel = self.textadj_tree.selection()
        if not sel:
            return
        item = sel[0]
        values = self.textadj_tree.item(item)["values"]
        try:
            ln = int(values[0])
        except Exception:
            return
        # 保存しておく
        self._textadj_selected_ln = ln
        # 対象行検索
        target = next((x for x in self.current_project.script_lines if x.line_number == ln), None)
        if not target:
            return
        # original
        self.ta_original.configure(state="normal")
        self.ta_original.delete("1.0", tk.END)
        self.ta_original.insert("1.0", target.text)
        self.ta_original.configure(state="disabled")
        # final/story/telop
        self.ta_final.delete("1.0", tk.END)
        self.ta_final.insert("1.0", target.final_text or "")
        self.ta_story.delete("1.0", tk.END)
        self.ta_story.insert("1.0", target.storyboard or "")
        self.ta_telop.delete("1.0", tk.END)
        self.ta_telop.insert("1.0", target.telop or "")
        # meta
        self.var_bgm.set(target.bgm_tag or "")
        try:
            self.var_rate.set(float(target.tts_rate or 1.0))
        except Exception:
            self.var_rate.set(1.0)
        self.var_locked.set(bool(target.locked))
        # notes
        self.ta_notes.delete("1.0", tk.END)
        self.ta_notes.insert("1.0", target.notes or "")

    def save_text_adjust_changes(self):
        if not self.current_project or self._textadj_selected_ln is None:
            return
        target = next((x for x in self.current_project.script_lines if x.line_number == self._textadj_selected_ln), None)
        if not target:
            return
        target.final_text = self.ta_final.get("1.0", tk.END).strip()
        target.storyboard = self.ta_story.get("1.0", tk.END).strip()
        target.telop = self.ta_telop.get("1.0", tk.END).strip()
        target.bgm_tag = self.var_bgm.get().strip()
        try:
            target.tts_rate = float(self.var_rate.get())
        except Exception:
            target.tts_rate = 1.0
        target.locked = bool(self.var_locked.get())
        target.notes = self.ta_notes.get("1.0", tk.END).strip()
        self.update_text_adjustment_display()
        self.set_status(f"行 {target.line_number} を保存しました")

    def export_csv_vertical(self):
        """CSV（縦）エクスポート"""
        if not self.current_project or not self.current_project.script_lines:
            messagebox.showwarning("警告", "エクスポートする行がありません")
            return
        file_path = filedialog.asksaveasfilename(
            title="CSV（縦型）を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return
        headers = [
            "line_no", "role", "character", "text_original", "text_final",
            "storyboard", "telop", "bgm_tag", "voice_id", "rate", "locked", "notes"
        ]
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for sl in self.current_project.script_lines:
                    writer.writerow([
                        sl.line_number,
                        sl.role,
                        sl.character or "",
                        sl.text,
                        sl.final_text or "",
                        sl.storyboard or "",
                        sl.telop or "",
                        sl.bgm_tag or "",
                        sl.voice_id or "",
                        sl.tts_rate if sl.tts_rate is not None else 1.0,
                        1 if sl.locked else 0,
                        sl.notes or ""
                    ])
            messagebox.showinfo("エクスポート完了", f"CSVを保存しました:\n{Path(file_path).name}")
            self.set_status(f"CSVエクスポート完了: {Path(file_path).name}")
        except Exception as e:
            messagebox.showerror("エクスポート失敗", f"CSV保存中にエラー: {e}")
    
    def update_character_list(self, detected_characters):
        """キャラクター一覧更新"""
        # 既存キャラクター取得
        existing_chars = {char.name for char in self.current_project.characters}
        
        # 新しいキャラクター追加
        for char_name in detected_characters:
            if char_name not in existing_chars:
                char = Character(name=char_name, voice_id=self.voice_parser.dialogue_voice)
                self.current_project.characters.append(char)
        
        # 表示更新
        for item in self.character_tree.get_children():
            self.character_tree.delete(item)
        
        for char in self.current_project.characters:
            self.character_tree.insert("", tk.END, values=(
                char.name,
                char.gender or "未設定",
                char.voice_id
            ))
    
    def add_character(self):
        """キャラクター手動追加"""
        name = tk.simpledialog.askstring("キャラクター追加", "キャラクター名:")
        if name and self.current_project:
            char = Character(name=name, voice_id=self.voice_parser.dialogue_voice)
            self.current_project.characters.append(char)
            self.update_character_list({char.name})
    
    # === Step 2: TTS音声生成 ===
    
    def update_tts_display(self):
        """TTS表示更新"""
        # スクリプト一覧更新
        for item in self.tts_script_tree.get_children():
            self.tts_script_tree.delete(item)
        
        if not self.current_project or not self.current_project.script_lines:
            return
        
        for script_line in self.current_project.script_lines:
            char_name = script_line.character or "-"
            text_preview = script_line.text[:40] + "..." if len(script_line.text) > 40 else script_line.text
            
            self.tts_script_tree.insert("", tk.END, values=(
                script_line.line_number,
                script_line.role,
                char_name,
                text_preview,
                "待機"
            ))
    
    def start_tts_generation(self):
        """TTS生成開始（疑似実装）"""
        if not self.current_project or not self.current_project.script_lines:
            messagebox.showwarning("警告", "生成するスクリプトがありません")
            return
        
        self.tts_generate_btn.configure(state="disabled")
        self.tts_progress.configure(maximum=len(self.current_project.script_lines), value=0)
        
        # 疑似TTS生成プロセス
        def generate_worker():
            for i, script_line in enumerate(self.current_project.script_lines):
                self.root.after(0, lambda i=i: self.tts_progress.configure(value=i+1))
                self.root.after(0, lambda i=i: self.tts_status_var.set(f"生成中... {i+1}/{len(self.current_project.script_lines)}"))
                
                # スクリプト表の状態更新
                items = self.tts_script_tree.get_children()
                if i < len(items):
                    item = items[i]
                    values = list(self.tts_script_tree.item(item)["values"])
                    values[4] = "✅ 完了"
                    self.root.after(0, lambda item=item, values=values: self.tts_script_tree.item(item, values=values))
                
                time.sleep(0.5)  # 疑似処理時間
            
            self.root.after(0, lambda: self.tts_status_var.set("TTS生成完了！"))
            self.root.after(0, lambda: self.tts_generate_btn.configure(state="normal"))
        
        threading.Thread(target=generate_worker, daemon=True).start()
    
    def test_tts_playback(self):
        """TTS再生テスト"""
        messagebox.showinfo("テスト再生", "TTS音声のテスト再生機能（実装予定）")
    
    # === Step 3: 字幕タイミング ===
    
    def auto_generate_timing(self):
        """自動タイミング生成"""
        if not self.current_project or not self.current_project.script_lines:
            messagebox.showwarning("警告", "タイミングを生成するスクリプトがありません")
            return
        
        # タイムライン表更新
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)
        
        current_time = 0.0
        for i, script_line in enumerate(self.current_project.script_lines):
            # テキスト長に基づく表示時間計算
            duration = max(1.5, min(5.0, len(script_line.text) * 0.08))
            
            start_time = current_time
            end_time = current_time + duration
            
            self.timeline_tree.insert("", tk.END, values=(
                i + 1,
                f"{start_time:.2f}s",
                f"{end_time:.2f}s",
                f"{duration:.2f}s",
                script_line.text[:50] + "..." if len(script_line.text) > 50 else script_line.text
            ))
            
            current_time = end_time + 0.2  # 0.2秒のギャップ
        
        self.set_status(f"自動タイミング生成完了: {len(self.current_project.script_lines)}キュー")
    
    def load_audio_folder(self):
        """音声フォルダ読み込み"""
        folder = filedialog.askdirectory(title="音声ファイルフォルダを選択")
        if folder:
            messagebox.showinfo("読み込み", f"音声フォルダ読み込み機能（実装予定）\n選択: {folder}")
    
    def save_srt_file(self):
        """SRTファイル保存"""
        file_path = filedialog.asksaveasfilename(
            title="SRTファイルを保存",
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # 疑似SRT内容生成
                srt_content = ""
                for i, item in enumerate(self.timeline_tree.get_children()):
                    values = self.timeline_tree.item(item)["values"]
                    srt_content += f"{i+1}\n00:00:{values[1]} --> 00:00:{values[2]}\n{values[4]}\n\n"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                # Step 4のSRTパスに設定
                self.srt_path_var.set(file_path)
                
                messagebox.showinfo("保存完了", f"SRTファイルを保存しました:\n{Path(file_path).name}")
                self.set_status(f"SRT保存完了: {Path(file_path).name}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"SRT保存エラー: {e}")
    
    def preview_subtitles(self):
        """字幕プレビュー"""
        messagebox.showinfo("プレビュー", "字幕プレビュー機能（実装予定）")
    
    # === Step 4: DaVinci出力 ===
    
    def connect_davinci(self):
        """DaVinci Resolve接続"""
        try:
            # 疑似接続処理
            self.davinci_status_var.set("✅ 接続済み")
            messagebox.showinfo("接続成功", "DaVinci Resolve接続成功（疑似）")
            self.set_status("DaVinci Resolve接続成功")
        except Exception as e:
            self.davinci_status_var.set("❌ 接続失敗")
            messagebox.showerror("接続エラー", f"DaVinci接続エラー: {e}")
    
    def import_srt_to_davinci(self):
        """SRTをDaVinciにインポート"""
        srt_path = self.srt_path_var.get()
        if not srt_path:
            messagebox.showwarning("警告", "SRTファイルが設定されていません")
            return
        
        messagebox.showinfo("インポート", f"SRTインポート機能（実装予定）\nファイル: {Path(srt_path).name}")
    
    def start_rendering(self):
        """レンダリング開始"""
        preset = self.render_preset_var.get()
        
        # 疑似レンダリングプロセス
        self.render_status_var.set("レンダリング中...")
        self.render_progress.configure(mode='indeterminate')
        self.render_progress.start()
        
        def render_worker():
            time.sleep(3)  # 疑似レンダリング時間
            self.root.after(0, lambda: self.render_progress.stop())
            self.root.after(0, lambda: self.render_progress.configure(mode='determinate', value=100))
            self.root.after(0, lambda: self.render_status_var.set("✅ レンダリング完了！"))
            self.root.after(0, lambda: messagebox.showinfo("完了", f"レンダリング完了！\nプリセット: {preset}"))
        
        threading.Thread(target=render_worker, daemon=True).start()
    
    # === UI更新・ユーティリティ ===
    
    def update_all_displays(self):
        """全表示更新"""
        if self.current_project:
            # Step 1: スクリプトエディタ
            if self.current_project.script_text:
                self.script_editor.delete("1.0", tk.END)
                self.script_editor.insert("1.0", self.current_project.script_text)
                self.parse_script()
            
            # 進捗更新
            self.update_step_status()
    
    def update_step_status(self):
        """ステップステータス更新"""
        if not self.current_project:
            return
        
        completed_count = sum([
            self.current_project.step1_completed,
            self.current_project.step2_completed,
            self.current_project.step3_completed,
            self.current_project.step4_completed
        ])
        
        self.progress_var.set(f"{completed_count}/4 完了")
        
        # 個別ステータス
        statuses = [
            "✅ 完了" if self.current_project.step1_completed else "未完了",
            "✅ 完了" if self.current_project.step2_completed else "未完了", 
            "✅ 完了" if self.current_project.step3_completed else "未完了",
            "✅ 完了" if self.current_project.step4_completed else "未完了"
        ]
        
        for i, status in enumerate(statuses):
            self.step_status_vars[i].set(status)
            if status == "✅ 完了":
                self.step_status_vars[i].set(status)
                # 緑色にする処理（TODO: スタイル設定）
    
    def update_step_buttons(self):
        """ステップボタン更新"""
        for i, btn in enumerate(self.step_buttons):
            if i + 1 == self.current_step:
                btn.configure(style="Accent.TButton")
            else:
                btn.configure(style="TButton")
    
    def set_status(self, message: str):
        """ステータス設定"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def run(self):
        """アプリケーション実行"""
        # スタイル設定
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#4CAF50")
        
        self.root.mainloop()


def main():
    """メイン関数"""
    import tkinter.simpledialog as simpledialog
    tk.simpledialog = simpledialog
    
    app = IntegratedWorkspace()
    app.run()


if __name__ == "__main__":
    main()
