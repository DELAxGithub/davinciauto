#!/usr/bin/env python3
"""
Step 3: Subtitle Timing Adjustment GUI
字幕タイミング調整GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys
import json
from typing import List, Dict, Optional, Tuple
import subprocess

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))

from gui_base import BaseStepWindow
from data_models import Project, ScriptLine

class SubtitleCue:
    """字幕キューデータ"""
    def __init__(self, line_number: int, text: str, start_time: float, end_time: float):
        self.line_number = line_number
        self.text = text
        self.start_time = start_time  # 秒
        self.end_time = end_time      # 秒
        self.duration = end_time - start_time
    
    def to_srt_format(self, cue_index: int) -> str:
        """SRT形式に変換"""
        start_srt = self._seconds_to_srt_time(self.start_time)
        end_srt = self._seconds_to_srt_time(self.end_time)
        return f"{cue_index}\n{start_srt} --> {end_srt}\n{self.text}\n\n"
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """秒をSRT時間形式に変換"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

class SubtitleTimingWindow(BaseStepWindow):
    """字幕タイミング調整ウィンドウ"""
    
    def __init__(self):
        super().__init__("Step 3: 字幕タイミング調整", 1400, 900, current_step="step3-subtitle-timing")
        
        # 字幕データ
        self.subtitle_cues: List[SubtitleCue] = []
        self.total_duration = 0.0
        self.current_selected_cue: Optional[SubtitleCue] = None
        
        # GUI セットアップ
        self.setup_main_layout()
        self.setup_timeline_view()
        self.setup_cue_editor()
        self.setup_preview_controls()
        
        # 初期状態
        self.update_display()
    
    def setup_main_layout(self):
        """メインレイアウト設定"""
        # 3分割: タイムライン | キューエディタ | プレビュー
        self.main_paned = ttk.PanedWindow(self.content_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # タイムラインフレーム (上部)
        self.timeline_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.timeline_frame, weight=2)
        
        # キューエディタフレーム (中央)
        self.editor_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.editor_frame, weight=2)
        
        # プレビューフレーム (下部)
        self.preview_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.preview_frame, weight=1)
    
    def setup_timeline_view(self):
        """タイムライン表示"""
        # ヘッダー
        header_frame = ttk.Frame(self.timeline_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="タイムライン", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        # 自動生成ボタン
        ttk.Button(header_frame, text="🔄 自動タイミング生成", 
                  command=self.auto_generate_timing).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header_frame, text="📁 音声フォルダ読み込み", 
                  command=self.load_audio_folder).pack(side=tk.RIGHT, padx=5)
        
        # 統計表示
        stats_frame = ttk.Frame(self.timeline_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_var = tk.StringVar(value="総時間: 0:00 | 字幕数: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var,
                 foreground="gray").pack(side=tk.LEFT)
        
        # タイムライン表示テーブル
        columns = ("cue", "start", "end", "duration", "text", "adjust")
        self.timeline_tree = ttk.Treeview(self.timeline_frame, columns=columns, show="headings")
        
        self.timeline_tree.heading("cue", text="#")
        self.timeline_tree.heading("start", text="開始")
        self.timeline_tree.heading("end", text="終了")
        self.timeline_tree.heading("duration", text="長さ")
        self.timeline_tree.heading("text", text="テキスト")
        self.timeline_tree.heading("adjust", text="調整")
        
        self.timeline_tree.column("cue", width=40)
        self.timeline_tree.column("start", width=80)
        self.timeline_tree.column("end", width=80)
        self.timeline_tree.column("duration", width=60)
        self.timeline_tree.column("text", width=400)
        self.timeline_tree.column("adjust", width=80)
        
        # スクロールバー
        timeline_scrollbar = ttk.Scrollbar(self.timeline_frame, orient=tk.VERTICAL,
                                         command=self.timeline_tree.yview)
        self.timeline_tree.configure(yscrollcommand=timeline_scrollbar.set)
        
        self.timeline_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        timeline_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 選択時のイベント
        self.timeline_tree.bind("<<TreeviewSelect>>", self.on_cue_select)
    
    def setup_cue_editor(self):
        """キューエディタ"""
        # ヘッダー
        header_frame = ttk.Frame(self.editor_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="選択キュー編集", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        # エディタ部分
        editor_main = ttk.Frame(self.editor_frame)
        editor_main.pack(fill=tk.BOTH, expand=True)
        
        # 左側: 時間調整
        time_frame = ttk.LabelFrame(editor_main, text="時間調整")
        time_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 開始時間
        ttk.Label(time_frame, text="開始時間:").pack(anchor=tk.W, padx=5, pady=5)
        start_frame = ttk.Frame(time_frame)
        start_frame.pack(fill=tk.X, padx=5)
        
        self.start_time_var = tk.StringVar(value="00:00.000")
        self.start_time_entry = ttk.Entry(start_frame, textvariable=self.start_time_var, width=12)
        self.start_time_entry.pack(side=tk.LEFT)
        
        ttk.Button(start_frame, text="±0.1s", width=6,
                  command=lambda: self.adjust_time("start", 0.1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(start_frame, text="±1s", width=6,
                  command=lambda: self.adjust_time("start", 1.0)).pack(side=tk.LEFT, padx=2)
        
        # 終了時間
        ttk.Label(time_frame, text="終了時間:").pack(anchor=tk.W, padx=5, pady=(10, 5))
        end_frame = ttk.Frame(time_frame)
        end_frame.pack(fill=tk.X, padx=5)
        
        self.end_time_var = tk.StringVar(value="00:00.000")
        self.end_time_entry = ttk.Entry(end_frame, textvariable=self.end_time_var, width=12)
        self.end_time_entry.pack(side=tk.LEFT)
        
        ttk.Button(end_frame, text="±0.1s", width=6,
                  command=lambda: self.adjust_time("end", 0.1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(end_frame, text="±1s", width=6,
                  command=lambda: self.adjust_time("end", 1.0)).pack(side=tk.LEFT, padx=2)
        
        # 長さ表示
        ttk.Label(time_frame, text="表示時間:").pack(anchor=tk.W, padx=5, pady=(10, 5))
        self.duration_var = tk.StringVar(value="0.0s")
        ttk.Label(time_frame, textvariable=self.duration_var, 
                 font=("", 10, "bold")).pack(anchor=tk.W, padx=5)
        
        # 更新ボタン
        ttk.Button(time_frame, text="🔄 更新", 
                  command=self.update_selected_cue).pack(pady=10)
        
        # 右側: テキスト編集
        text_frame = ttk.LabelFrame(editor_main, text="字幕テキスト")
        text_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.subtitle_text = tk.Text(text_frame, height=8, wrap=tk.WORD, font=("", 11))
        text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                     command=self.subtitle_text.yview)
        self.subtitle_text.configure(yscrollcommand=text_scrollbar.set)
        
        self.subtitle_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # テキスト変更監視
        self.subtitle_text.bind("<KeyRelease>", self.on_text_change)
    
    def setup_preview_controls(self):
        """プレビューコントロール"""
        # ヘッダー
        header_frame = ttk.Frame(self.preview_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="プレビュー・出力", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        # コントロール部分
        control_frame = ttk.Frame(self.preview_frame)
        control_frame.pack(fill=tk.X)
        
        # 左側: プレビュー
        preview_left = ttk.LabelFrame(control_frame, text="プレビュー")
        preview_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        preview_buttons = ttk.Frame(preview_left)
        preview_buttons.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(preview_buttons, text="▶️ 全体プレビュー", 
                  command=self.preview_all_subtitles).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_buttons, text="👁️ 選択キュー", 
                  command=self.preview_selected_cue).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_buttons, text="📄 SRTプレビュー", 
                  command=self.show_srt_preview).pack(side=tk.LEFT, padx=5)
        
        # 右側: 出力
        output_right = ttk.LabelFrame(control_frame, text="出力")
        output_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        output_buttons = ttk.Frame(output_right)
        output_buttons.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(output_buttons, text="💾 SRT保存", 
                  command=self.save_srt_file).pack(fill=tk.X, pady=2)
        ttk.Button(output_buttons, text="📊 統計出力", 
                  command=self.export_statistics).pack(fill=tk.X, pady=2)
        
        # 完了ボタン
        complete_frame = ttk.Frame(output_right)
        complete_frame.pack(fill=tk.X, padx=10, pady=(20, 10))
        
        ttk.Button(complete_frame, text="Step 3 完了 → Step 4へ", 
                  command=self.complete_step3,
                  style="Accent.TButton").pack(fill=tk.X)
    
    def load_audio_folder(self):
        """音声フォルダ読み込み"""
        folder = filedialog.askdirectory(title="音声ファイルフォルダを選択")
        if not folder:
            return
        
        audio_path = Path(folder)
        audio_files = []
        
        # 音声ファイル検索
        for ext in ['.mp3', '.wav', '.m4a']:
            audio_files.extend(audio_path.glob(f"*{ext}"))
        
        if not audio_files:
            messagebox.showwarning("警告", "音声ファイルが見つかりません")
            return
        
        # ファイル名でソート
        audio_files.sort()
        
        # 音声ファイル情報を読み取り（疑似実装）
        self.subtitle_cues = []
        current_time = 0.0
        
        for i, audio_file in enumerate(audio_files):
            # 実際の実装では音声ファイルの長さを取得
            # 今回は疑似的に2-5秒とする
            duration = 2.5 + (i % 3)  # 疑似時間
            
            # スクリプトから対応するテキストを取得
            text = f"音声ファイル {i+1}: {audio_file.stem}"
            if self.current_project and i < len(self.current_project.script_lines):
                text = self.current_project.script_lines[i].text
            
            cue = SubtitleCue(
                line_number=i+1,
                text=text,
                start_time=current_time,
                end_time=current_time + duration
            )
            
            self.subtitle_cues.append(cue)
            current_time = cue.end_time + 0.2  # 0.2秒のギャップ
        
        self.total_duration = current_time
        self.update_timeline_display()
        
        self.set_status(f"音声フォルダから {len(audio_files)} ファイルを読み込みました")
    
    def auto_generate_timing(self):
        """自動タイミング生成"""
        if not self.current_project or not self.current_project.script_lines:
            messagebox.showwarning("警告", "スクリプトデータがありません")
            return
        
        # 簡単な自動生成ロジック
        self.subtitle_cues = []
        current_time = 0.0
        
        for i, script_line in enumerate(self.current_project.script_lines):
            # テキスト長に基づく表示時間計算（疑似）
            char_count = len(script_line.text)
            duration = max(1.5, min(6.0, char_count * 0.1))  # 1.5-6秒の範囲
            
            cue = SubtitleCue(
                line_number=script_line.line_number,
                text=script_line.text,
                start_time=current_time,
                end_time=current_time + duration
            )
            
            self.subtitle_cues.append(cue)
            current_time = cue.end_time + 0.3  # 0.3秒のギャップ
        
        self.total_duration = current_time
        self.update_timeline_display()
        
        self.set_status(f"自動タイミングを生成しました（{len(self.subtitle_cues)}キュー）")
    
    def update_timeline_display(self):
        """タイムライン表示更新"""
        # テーブルクリア
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)
        
        # キューを追加
        for i, cue in enumerate(self.subtitle_cues):
            start_str = self._format_time(cue.start_time)
            end_str = self._format_time(cue.end_time)
            duration_str = f"{cue.duration:.1f}s"
            text_preview = cue.text[:50] + "..." if len(cue.text) > 50 else cue.text
            
            self.timeline_tree.insert("", tk.END, values=(
                i + 1,
                start_str,
                end_str,
                duration_str,
                text_preview,
                "調整可"
            ))
        
        # 統計更新
        total_time_str = self._format_time(self.total_duration)
        self.stats_var.set(f"総時間: {total_time_str} | 字幕数: {len(self.subtitle_cues)}")
    
    def _format_time(self, seconds: float) -> str:
        """時間フォーマット"""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:05.2f}"
    
    def on_cue_select(self, event):
        """キュー選択時の処理"""
        selected = self.timeline_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        cue_index = int(self.timeline_tree.item(item)["values"][0]) - 1
        
        if 0 <= cue_index < len(self.subtitle_cues):
            self.current_selected_cue = self.subtitle_cues[cue_index]
            self.load_cue_to_editor(self.current_selected_cue)
    
    def load_cue_to_editor(self, cue: SubtitleCue):
        """キューをエディタに読み込み"""
        self.start_time_var.set(self._format_time(cue.start_time))
        self.end_time_var.set(self._format_time(cue.end_time))
        self.duration_var.set(f"{cue.duration:.1f}s")
        
        self.subtitle_text.delete("1.0", tk.END)
        self.subtitle_text.insert("1.0", cue.text)
    
    def adjust_time(self, time_type: str, delta: float):
        """時間調整ボタン"""
        if not self.current_selected_cue:
            return
        
        # クリック時に+/-を判定（簡易実装）
        # 実際のUIでは+/-ボタンを分ける
        if time_type == "start":
            self.current_selected_cue.start_time += delta
        else:
            self.current_selected_cue.end_time += delta
        
        # 再計算
        self.current_selected_cue.duration = (
            self.current_selected_cue.end_time - self.current_selected_cue.start_time
        )
        
        # エディタ更新
        self.load_cue_to_editor(self.current_selected_cue)
        self.update_timeline_display()
    
    def on_text_change(self, event):
        """テキスト変更時の処理"""
        if self.current_selected_cue:
            new_text = self.subtitle_text.get("1.0", tk.END).strip()
            self.current_selected_cue.text = new_text
    
    def update_selected_cue(self):
        """選択キューの更新"""
        if not self.current_selected_cue:
            return
        
        try:
            # 時間文字列を解析
            start_str = self.start_time_var.get()
            end_str = self.end_time_var.get()
            
            # 簡易解析（MM:SS.sss形式）
            start_parts = start_str.split(":")
            start_time = float(start_parts[0]) * 60 + float(start_parts[1])
            
            end_parts = end_str.split(":")
            end_time = float(end_parts[0]) * 60 + float(end_parts[1])
            
            # 更新
            self.current_selected_cue.start_time = start_time
            self.current_selected_cue.end_time = end_time
            self.current_selected_cue.duration = end_time - start_time
            self.current_selected_cue.text = self.subtitle_text.get("1.0", tk.END).strip()
            
            # 表示更新
            self.load_cue_to_editor(self.current_selected_cue)
            self.update_timeline_display()
            
            self.set_status("キューを更新しました")
            
        except Exception as e:
            messagebox.showerror("エラー", f"時間形式が正しくありません: {e}")
    
    def preview_all_subtitles(self):
        """全体プレビュー"""
        if not self.subtitle_cues:
            messagebox.showwarning("警告", "プレビューする字幕がありません")
            return
        
        # プレビューウィンドウ表示
        preview_window = tk.Toplevel(self.root)
        preview_window.title("字幕プレビュー")
        preview_window.geometry("800x600")
        
        # プレビューテキスト
        preview_text = tk.Text(preview_window, wrap=tk.WORD, font=("", 11))
        preview_scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL,
                                         command=preview_text.yview)
        preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        # 内容生成
        content = "=== 字幕プレビュー ===\n\n"
        for i, cue in enumerate(self.subtitle_cues):
            start_str = self._format_time(cue.start_time)
            end_str = self._format_time(cue.end_time)
            content += f"[{i+1:03d}] {start_str} - {end_str}\n"
            content += f"{cue.text}\n\n"
        
        preview_text.insert("1.0", content)
        preview_text.configure(state="disabled")
        
        preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
    
    def preview_selected_cue(self):
        """選択キュープレビュー"""
        if not self.current_selected_cue:
            messagebox.showwarning("警告", "プレビューするキューを選択してください")
            return
        
        cue = self.current_selected_cue
        start_str = self._format_time(cue.start_time)
        end_str = self._format_time(cue.end_time)
        
        message = f"時間: {start_str} - {end_str}\n"
        message += f"表示時間: {cue.duration:.1f}秒\n\n"
        message += f"テキスト:\n{cue.text}"
        
        messagebox.showinfo("キュープレビュー", message)
    
    def show_srt_preview(self):
        """SRTプレビュー"""
        if not self.subtitle_cues:
            messagebox.showwarning("警告", "プレビューする字幕がありません")
            return
        
        # SRTファイル内容生成
        srt_content = ""
        for i, cue in enumerate(self.subtitle_cues):
            srt_content += cue.to_srt_format(i + 1)
        
        # プレビューウィンドウ
        preview_window = tk.Toplevel(self.root)
        preview_window.title("SRTプレビュー")
        preview_window.geometry("600x500")
        
        preview_text = tk.Text(preview_window, wrap=tk.NONE, font=("Courier", 10))
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL,
                                   command=preview_text.yview)
        h_scrollbar = ttk.Scrollbar(preview_window, orient=tk.HORIZONTAL,
                                   command=preview_text.xview)
        preview_text.configure(yscrollcommand=v_scrollbar.set,
                              xscrollcommand=h_scrollbar.set)
        
        preview_text.insert("1.0", srt_content)
        preview_text.configure(state="disabled")
        
        preview_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        v_scrollbar.grid(row=0, column=1, sticky="ns", pady=10)
        h_scrollbar.grid(row=1, column=0, sticky="ew", padx=10)
        
        preview_window.grid_columnconfigure(0, weight=1)
        preview_window.grid_rowconfigure(0, weight=1)
    
    def save_srt_file(self):
        """SRTファイル保存"""
        if not self.subtitle_cues:
            messagebox.showwarning("警告", "保存する字幕がありません")
            return
        
        # 保存先選択
        file_path = filedialog.asksaveasfilename(
            title="SRTファイルを保存",
            defaultextension=".srt",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # SRT内容生成
            srt_content = ""
            for i, cue in enumerate(self.subtitle_cues):
                srt_content += cue.to_srt_format(i + 1)
            
            # ファイル保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            messagebox.showinfo("完了", f"SRTファイルを保存しました:\n{file_path}")
            self.set_status(f"SRT保存完了: {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("エラー", f"SRTファイル保存エラー: {e}")
    
    def export_statistics(self):
        """統計出力"""
        if not self.subtitle_cues:
            messagebox.showwarning("警告", "統計を出力する字幕がありません")
            return
        
        # 統計計算
        total_cues = len(self.subtitle_cues)
        total_duration = self.total_duration
        avg_duration = sum(cue.duration for cue in self.subtitle_cues) / total_cues
        
        char_counts = [len(cue.text) for cue in self.subtitle_cues]
        avg_chars = sum(char_counts) / total_cues
        max_chars = max(char_counts)
        min_chars = min(char_counts)
        
        stats_text = f"""=== 字幕統計情報 ===
        
総キュー数: {total_cues}
総再生時間: {self._format_time(total_duration)}
平均表示時間: {avg_duration:.2f}秒

文字数統計:
- 平均: {avg_chars:.1f}文字
- 最大: {max_chars}文字
- 最小: {min_chars}文字

長時間表示キュー (>5秒):
"""
        
        long_cues = [cue for cue in self.subtitle_cues if cue.duration > 5.0]
        for cue in long_cues[:5]:  # 上位5件
            stats_text += f"- 行{cue.line_number}: {cue.duration:.1f}s\n"
        
        # 統計表示ウィンドウ
        stats_window = tk.Toplevel(self.root)
        stats_window.title("字幕統計")
        stats_window.geometry("500x400")
        
        stats_display = tk.Text(stats_window, wrap=tk.WORD, font=("Courier", 10))
        stats_display.insert("1.0", stats_text)
        stats_display.configure(state="disabled")
        
        stats_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def complete_step3(self):
        """Step 3 完了処理"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成または読み込んでください")
            return
        
        if not self.subtitle_cues:
            response = messagebox.askyesno(
                "確認", 
                "字幕が設定されていません。このまま次のステップに進みますか？"
            )
            if not response:
                return
        
        # 字幕データをプロジェクトに保存
        self.current_project.step3_completed = True
        
        # 保存
        self.save_project()
        
        # 次のステップに進む
        response = messagebox.askyesno(
            "Step 3 完了", 
            "Step 3 が完了しました。Step 4 (DaVinci出力) に進みますか？"
        )
        
        if response:
            self.launch_step("step4_davinci_export.py")
    
    def update_display(self):
        """表示更新"""
        if self.current_project and self.current_project.script_lines:
            # 自動タイミング生成を提案
            if not self.subtitle_cues:
                response = messagebox.askyesno(
                    "自動生成", 
                    "スクリプトから自動タイミングを生成しますか？"
                )
                if response:
                    self.auto_generate_timing()
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理"""
        self.update_display()
    
    def on_project_save(self):
        """プロジェクト保存時の処理"""
        pass


def main():
    """メイン関数"""
    app = SubtitleTimingWindow()
    app.run()


if __name__ == "__main__":
    main()