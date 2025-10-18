"""
Base GUI components for all steps
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, Callable
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "minivt_pipeline" / "src"))

from data_models import Project

class BaseStepWindow:
    """共通のステップウィンドウ基底クラス"""
    
    def __init__(self, title: str, width: int = 1000, height: int = 700, current_step: str = None):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        
        # ステップ管理
        self.current_step = current_step
        
        # プロジェクト管理
        self.current_project: Optional[Project] = None
        self.project_file: Optional[Path] = None
        
        # メインフレーム
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ステップナビゲーション
        self.setup_step_navigation()
        
        # ツールバー
        self.setup_toolbar()
        
        # メインコンテンツエリア（サブクラスで実装）
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # ステータスバー
        self.setup_status_bar()
        
        # スタイル設定
        self.setup_styles()
        
        # イベントバインディング
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_styles(self):
        """カスタムスタイル設定"""
        style = ttk.Style()
        
        # 現在ステップボタン用スタイル
        style.configure("Current.TButton", 
                       background="#4CAF50",
                       foreground="white",
                       focuscolor="none")
        style.map("Current.TButton",
                 background=[("disabled", "#81C784")],
                 foreground=[("disabled", "#FFFFFF")])
    
    def setup_step_navigation(self):
        """ステップナビゲーションボタン"""
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        steps = [
            ("Step 1: スクリプト編集", "step1_script_editor.py"),
            ("Step 2: TTS生成", "step2_tts_generation.py"),
            ("Step 3: 字幕調整", "step3_subtitle_timing.py"), 
            ("Step 4: DaVinci出力", "step4_davinci_export.py")
        ]
        
        for i, (label, script) in enumerate(steps):
            # 現在のステップかどうか判定
            step_name = script.replace(".py", "").replace("_", "-")
            is_current_step = self.current_step and self.current_step == step_name
            
            btn = ttk.Button(nav_frame, text=label, 
                           command=lambda s=script: self.launch_step(s),
                           state="disabled" if is_current_step else "normal")
            btn.pack(side=tk.LEFT, padx=5)
            
            # 現在のステップは視覚的に区別
            if is_current_step:
                btn.configure(style="Current.TButton")
    
    def setup_toolbar(self):
        """ツールバー"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # プロジェクト管理
        ttk.Button(toolbar, text="新規プロジェクト", 
                  command=self.new_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="プロジェクトを開く", 
                  command=self.open_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="保存", 
                  command=self.save_project).pack(side=tk.LEFT, padx=5)
        
        # 区切り線
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # プロジェクト名表示
        self.project_name_var = tk.StringVar(value="プロジェクトなし")
        ttk.Label(toolbar, text="プロジェクト:").pack(side=tk.LEFT, padx=5)
        ttk.Label(toolbar, textvariable=self.project_name_var, 
                 font=("", 10, "bold")).pack(side=tk.LEFT, padx=5)
    
    def setup_status_bar(self):
        """ステータスバー"""
        self.status_bar = ttk.Frame(self.main_frame)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.status_bar, textvariable=self.status_var).pack(side=tk.LEFT)
    
    def set_status(self, message: str):
        """ステータスメッセージ設定"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def new_project(self):
        """新規プロジェクト作成"""
        name = tk.simpledialog.askstring("新規プロジェクト", "プロジェクト名を入力:")
        if name:
            self.current_project = Project(name=name)
            self.project_name_var.set(name)
            self.on_project_loaded()
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
                self.on_project_loaded()
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
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                self.project_file = Path(file_path)
            else:
                return
        
        try:
            self.on_project_save()  # サブクラスで実装
            self.current_project.save_to_file(self.project_file)
            self.set_status(f"プロジェクト '{self.current_project.name}' を保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"プロジェクト保存エラー: {e}")
    
    def launch_step(self, script_name: str):
        """他のステップを起動"""
        try:
            script_path = Path(__file__).parent.parent / script_name
            if script_path.exists():
                # 現在のプロジェクトを保存してから起動
                if self.current_project and self.project_file:
                    self.save_project()
                
                # 新しいステップを起動
                import subprocess
                subprocess.Popen([sys.executable, str(script_path)])
            else:
                messagebox.showwarning("警告", f"スクリプト {script_name} が見つかりません")
        except Exception as e:
            messagebox.showerror("エラー", f"ステップ起動エラー: {e}")
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理（サブクラスで実装）"""
        pass
    
    def on_project_save(self):
        """プロジェクト保存時の処理（サブクラスで実装）"""
        pass
    
    def on_close(self):
        """ウィンドウクローズ時の処理"""
        if self.current_project and self.project_file:
            response = messagebox.askyesnocancel(
                "終了確認", 
                "プロジェクトの変更を保存しますか？"
            )
            if response is True:  # Yes
                self.save_project()
                self.root.destroy()
            elif response is False:  # No
                self.root.destroy()
            # Cancel の場合は何もしない
        else:
            self.root.destroy()
    
    def run(self):
        """メインループ実行"""
        self.root.mainloop()


class SyntaxHighlightText(tk.Text):
    """シンタックスハイライト付きテキストウィジェット"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # タグ設定
        self.tag_configure("NA", foreground="#2E7D32", font=("", 11, "bold"))  # 緑
        self.tag_configure("DL", foreground="#1565C0", font=("", 11, "bold"))  # 青
        self.tag_configure("voice_instruction", foreground="#F57C00", font=("", 10, "italic"))  # オレンジ
        self.tag_configure("character", foreground="#7B1FA2", font=("", 11, "bold"))  # 紫
        
        # リアルタイム更新
        self.bind("<KeyRelease>", self.on_text_change)
        self.bind("<Button-1>", self.on_text_change)
    
    def on_text_change(self, event=None):
        """テキスト変更時にハイライト更新"""
        self.highlight_syntax()
    
    def highlight_syntax(self):
        """シンタックスハイライト適用"""
        # 既存のタグをクリア
        for tag in ["NA", "DL", "voice_instruction", "character"]:
            self.tag_remove(tag, "1.0", tk.END)
        
        content = self.get("1.0", tk.END)
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_start = f"{line_num}.0"
            
            if line.strip().startswith("NA:"):
                # ナレーション行
                self.tag_add("NA", line_start, f"{line_num}.{len('NA:')}")
                
                # 音声指示検出
                import re
                voice_match = re.search(r'（[^）]+）', line)
                if voice_match:
                    start_pos = line_start.split('.')[0] + '.' + str(voice_match.start())
                    end_pos = line_start.split('.')[0] + '.' + str(voice_match.end())
                    self.tag_add("voice_instruction", start_pos, end_pos)
            
            elif line.strip().startswith("セリフ:"):
                # セリフ行
                self.tag_add("DL", line_start, f"{line_num}.{len('セリフ:')}")
                
                # キャラクター名検出（セリフ:キャラA（音声指示）：実際の台詞）
                import re
                char_match = re.search(r'セリフ:([^（：]+)', line)
                if char_match:
                    char_start = line_num + len('セリフ:')
                    char_end = char_start + len(char_match.group(1))
                    self.tag_add("character", f"{line_num}.{char_start}", f"{line_num}.{char_end}")
                
                # 音声指示検出
                voice_match = re.search(r'（[^）]+）', line)
                if voice_match:
                    start_pos = f"{line_num}.{voice_match.start()}"
                    end_pos = f"{line_num}.{voice_match.end()}"
                    self.tag_add("voice_instruction", start_pos, end_pos)