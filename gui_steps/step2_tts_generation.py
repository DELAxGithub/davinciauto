#!/usr/bin/env python3
"""
Step 2: TTS Generation GUI
TTS音声生成GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys
import threading
import time
from typing import List, Dict, Optional, Callable
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

# Try to import pygame, fallback if not available
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available, audio playback disabled")

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))
sys.path.append(str(Path(__file__).parent.parent / "minivt_pipeline" / "src"))

from gui_base import BaseStepWindow
from data_models import Project, ScriptLine, TTSResult
from clients.tts_elevenlabs import tts_elevenlabs_per_line, TTSError
from utils.cost_tracker import CostTracker
from utils.voice_parser import VoiceInstructionParser
from pydub import AudioSegment
from pydub.playback import play

class TTSGenerationWindow(BaseStepWindow):
    """TTS音声生成ウィンドウ"""
    
    def __init__(self):
        super().__init__("Step 2: TTS音声生成", 1400, 900, current_step="step2-tts-generation")
        
        # Initialize pygame for audio playback
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Warning: pygame initialization failed: {e}")
                PYGAME_AVAILABLE = False
        
        # TTS関連
        self.voice_parser = VoiceInstructionParser()
        self.cost_tracker = CostTracker()
        
        # 生成状態管理
        self.generation_in_progress = False
        self.generation_thread = None
        self.tts_results: List[TTSResult] = []
        
        # GUI セットアップ
        self.setup_main_layout()
        self.setup_script_display()
        self.setup_generation_controls()
        self.setup_results_panel()
        self.setup_audio_controls()
        
        # 初期状態
        self.update_display()
    
    def setup_main_layout(self):
        """メインレイアウト設定"""
        # 上下分割: スクリプト表示 | 生成コントロール | 結果表示
        self.main_paned = ttk.PanedWindow(self.content_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # スクリプト表示フレーム (上部)
        self.script_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.script_frame, weight=2)
        
        # 制御パネル (中央)
        self.control_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.control_frame, weight=1)
        
        # 結果パネル (下部)
        self.results_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.results_frame, weight=3)
    
    def setup_script_display(self):
        """スクリプト表示パネル"""
        # ヘッダー
        header_frame = ttk.Frame(self.script_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="スクリプト一覧", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        self.script_count_var = tk.StringVar(value="0行")
        ttk.Label(header_frame, textvariable=self.script_count_var,
                 foreground="gray").pack(side=tk.RIGHT)
        
        # スクリプト一覧テーブル
        columns = ("line", "role", "character", "voice", "text", "status")
        self.script_tree = ttk.Treeview(self.script_frame, columns=columns, show="headings", height=8)
        
        self.script_tree.heading("line", text="#")
        self.script_tree.heading("role", text="種類")
        self.script_tree.heading("character", text="キャラ")
        self.script_tree.heading("voice", text="音声")
        self.script_tree.heading("text", text="テキスト")
        self.script_tree.heading("status", text="状態")
        
        self.script_tree.column("line", width=40)
        self.script_tree.column("role", width=60)
        self.script_tree.column("character", width=100)
        self.script_tree.column("voice", width=100)
        self.script_tree.column("text", width=400)
        self.script_tree.column("status", width=80)
        
        # スクロールバー
        script_scrollbar = ttk.Scrollbar(self.script_frame, orient=tk.VERTICAL,
                                        command=self.script_tree.yview)
        self.script_tree.configure(yscrollcommand=script_scrollbar.set)
        
        self.script_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        script_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_generation_controls(self):
        """生成コントロールパネル"""
        # ヘッダー
        header_frame = ttk.Frame(self.control_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="TTS生成コントロール", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(self.control_frame, text="生成設定")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 出力パス設定
        path_frame = ttk.Frame(settings_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="出力パス:").pack(side=tk.LEFT, padx=5)
        self.output_path_var = tk.StringVar(value="output/audio/")
        ttk.Entry(path_frame, textvariable=self.output_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="参照", command=self.browse_output_path).pack(side=tk.LEFT, padx=5)
        
        # バッチ生成設定
        batch_frame = ttk.Frame(settings_frame)
        batch_frame.pack(fill=tk.X, pady=5)
        
        self.parallel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(batch_frame, text="並列生成 (実験的)", 
                       variable=self.parallel_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(batch_frame, text="同時実行数:").pack(side=tk.LEFT, padx=10)
        self.parallel_count_var = tk.IntVar(value=2)
        ttk.Spinbox(batch_frame, from_=1, to=5, width=5,
                   textvariable=self.parallel_count_var).pack(side=tk.LEFT, padx=5)
        
        # 進捗表示
        progress_frame = ttk.LabelFrame(self.control_frame, text="生成進捗")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 全体進捗
        ttk.Label(progress_frame, text="全体進捗:").pack(anchor=tk.W, padx=5)
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.overall_progress_text = tk.StringVar(value="待機中...")
        ttk.Label(progress_frame, textvariable=self.overall_progress_text).pack(anchor=tk.W, padx=5)
        
        # 現在の行進捗
        ttk.Label(progress_frame, text="現在の行:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.current_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.current_progress.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.current_progress_text = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.current_progress_text).pack(anchor=tk.W, padx=5)
        
        # コントロールボタン
        button_frame = ttk.Frame(self.control_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.generate_btn = ttk.Button(button_frame, text="🎵 全て生成開始", 
                                      command=self.start_batch_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ 停止", 
                                  command=self.stop_generation, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.regenerate_btn = ttk.Button(button_frame, text="🔄 選択行再生成", 
                                        command=self.regenerate_selected)
        self.regenerate_btn.pack(side=tk.LEFT, padx=5)
        
        # コスト表示
        cost_frame = ttk.Frame(button_frame)
        cost_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(cost_frame, text="推定コスト:").pack(side=tk.LEFT)
        self.cost_var = tk.StringVar(value="$0.00")
        ttk.Label(cost_frame, textvariable=self.cost_var, 
                 font=("", 10, "bold"), foreground="#E65100").pack(side=tk.LEFT, padx=5)
    
    def setup_results_panel(self):
        """結果表示パネル"""
        # ヘッダー
        header_frame = ttk.Frame(self.results_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="生成結果", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        self.results_count_var = tk.StringVar(value="0/0 完了")
        ttk.Label(header_frame, textvariable=self.results_count_var,
                 foreground="gray").pack(side=tk.RIGHT)
        
        # 結果テーブル
        columns = ("line", "text", "duration", "status", "file", "actions")
        self.results_tree = ttk.Treeview(self.results_frame, columns=columns, show="headings")
        
        self.results_tree.heading("line", text="#")
        self.results_tree.heading("text", text="テキスト")
        self.results_tree.heading("duration", text="時間")
        self.results_tree.heading("status", text="状態")
        self.results_tree.heading("file", text="ファイル")
        self.results_tree.heading("actions", text="操作")
        
        self.results_tree.column("line", width=40)
        self.results_tree.column("text", width=300)
        self.results_tree.column("duration", width=80)
        self.results_tree.column("status", width=80)
        self.results_tree.column("file", width=200)
        self.results_tree.column("actions", width=100)
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL,
                                         command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ダブルクリックで再生
        self.results_tree.bind("<Double-1>", self.on_result_double_click)
    
    def setup_audio_controls(self):
        """音声コントロールパネル"""
        audio_frame = ttk.Frame(self.results_frame)
        audio_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(audio_frame, text="音声コントロール:", font=("", 10, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(audio_frame, text="▶️ 再生", 
                  command=self.play_selected_audio).pack(side=tk.LEFT, padx=5)
        ttk.Button(audio_frame, text="⏹️ 停止", 
                  command=self.stop_audio).pack(side=tk.LEFT, padx=5)
        ttk.Button(audio_frame, text="📁 フォルダを開く", 
                  command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        
        # 完了ボタン
        complete_frame = ttk.Frame(audio_frame)
        complete_frame.pack(side=tk.RIGHT)
        
        ttk.Button(complete_frame, text="Step 2 完了 → Step 3へ", 
                  command=self.complete_step2,
                  style="Accent.TButton").pack()
    
    def browse_output_path(self):
        """出力パス参照"""
        folder = filedialog.askdirectory(title="出力フォルダを選択")
        if folder:
            self.output_path_var.set(folder)
    
    def update_display(self):
        """表示更新"""
        if not self.current_project:
            return
        
        # スクリプト一覧更新
        for item in self.script_tree.get_children():
            self.script_tree.delete(item)
        
        for script_line in self.current_project.script_lines:
            char_name = script_line.character or "-"
            voice_info = script_line.voice_instruction or "デフォルト"
            display_text = script_line.text[:50] + "..." if len(script_line.text) > 50 else script_line.text
            status = "待機"
            
            self.script_tree.insert("", tk.END, values=(
                script_line.line_number,
                script_line.role,
                char_name,
                voice_info,
                display_text,
                status
            ))
        
        self.script_count_var.set(f"{len(self.current_project.script_lines)}行")
        
        # コスト計算
        self.update_cost_estimate()
    
    def update_cost_estimate(self):
        """コスト見積もり更新"""
        if not self.current_project:
            return
        
        total_chars = sum(len(line.text) for line in self.current_project.script_lines)
        estimated_cost = self.cost_tracker.estimate_cost(total_chars)
        self.cost_var.set(f"${estimated_cost:.2f}")
    
    def start_batch_generation(self):
        """バッチTTS生成開始"""
        if not self.current_project or not self.current_project.script_lines:
            messagebox.showwarning("警告", "生成するスクリプトがありません")
            return
        
        if self.generation_in_progress:
            messagebox.showwarning("警告", "既に生成中です")
            return
        
        # 出力パスチェック
        output_path = Path(self.output_path_var.get())
        output_path.mkdir(parents=True, exist_ok=True)
        
        # UI状態変更
        self.generation_in_progress = True
        self.generate_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        # 進捗初期化
        self.overall_progress.configure(maximum=len(self.current_project.script_lines))
        self.overall_progress.configure(value=0)
        self.current_progress.start()
        
        # バックグラウンドで生成開始
        self.generation_thread = threading.Thread(target=self._batch_generation_worker)
        self.generation_thread.start()
    
    def _batch_generation_worker(self):
        """バッチ生成ワーカー（バックグラウンド実行）"""
        try:
            output_path = Path(self.output_path_var.get())
            lines = self.current_project.script_lines
            
            if self.parallel_var.get():
                # 並列生成
                self._parallel_generation(lines, output_path)
            else:
                # 順次生成
                self._sequential_generation(lines, output_path)
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"TTS生成エラー: {e}"))
        finally:
            self.root.after(0, self._generation_complete)
    
    def _sequential_generation(self, lines: List[ScriptLine], output_path: Path):
        """順次生成"""
        for i, line in enumerate(lines):
            if not self.generation_in_progress:  # 停止チェック
                break
            
            # UI更新
            self.root.after(0, lambda i=i, line=line: self._update_generation_progress(i, line))
            
            # TTS生成実行
            result = self._generate_single_line(line, output_path, i)
            self.tts_results.append(result)
            
            # 結果表示更新
            self.root.after(0, lambda result=result: self._update_result_display(result))
            
            # 進捗更新
            self.root.after(0, lambda i=i: self.overall_progress.configure(value=i+1))
    
    def _parallel_generation(self, lines: List[ScriptLine], output_path: Path):
        """並列生成"""
        max_workers = self.parallel_count_var.get()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全ての生成タスクを投入
            future_to_line = {
                executor.submit(self._generate_single_line, line, output_path, i): (line, i)
                for i, line in enumerate(lines)
            }
            
            completed = 0
            for future in future_to_line:
                if not self.generation_in_progress:  # 停止チェック
                    break
                
                line, i = future_to_line[future]
                try:
                    result = future.result()
                    self.tts_results.append(result)
                    
                    # 結果表示更新
                    self.root.after(0, lambda result=result: self._update_result_display(result))
                    
                    completed += 1
                    # 進捗更新
                    self.root.after(0, lambda c=completed: self.overall_progress.configure(value=c))
                    
                except Exception as e:
                    print(f"Line {i} generation failed: {e}")
    
    def _generate_single_line(self, line: ScriptLine, output_path: Path, line_index: int) -> TTSResult:
        """単一行のTTS生成"""
        try:
            # 音声設定決定
            voice_id = self._get_voice_id_for_line(line)
            voice_settings = self._get_voice_settings_for_line(line)
            
            # ファイル名生成
            slug = self._get_title_slug()
            filename = f"{slug}-S{line_index+1:03d}.mp3"
            file_path = output_path / filename
            
            # TTS生成実行
            audio_data = tts_elevenlabs_per_line(
                text=line.text,
                voice_id=voice_id,
                output_path=str(file_path),
                voice_settings=voice_settings
            )
            
            # 音声ファイルの時間取得
            if file_path.exists():
                audio = AudioSegment.from_mp3(str(file_path))
                duration = len(audio) / 1000.0  #秒
            else:
                duration = 0.0
            
            return TTSResult(
                line_number=line.line_number,
                audio_file_path=file_path,
                duration=duration,
                success=True
            )
            
        except Exception as e:
            return TTSResult(
                line_number=line.line_number,
                audio_file_path=Path(""),
                duration=0.0,
                success=False,
                error_message=str(e)
            )

    def _get_title_slug(self) -> str:
        """プロジェクト名から安全なスラッグを生成"""
        title = None
        try:
            if hasattr(self, 'project_name_var') and self.project_name_var.get():
                title = self.project_name_var.get()
            elif self.current_project and getattr(self.current_project, 'name', None):
                title = self.current_project.name
        except Exception:
            pass
        if not title:
            title = 'untitled'
        s = ''.join(ch if ch.isalnum() else '-' for ch in title)
        s = re.sub(r'-+', '-', s).strip('-')
        return s or 'untitled'
    
    def _get_voice_id_for_line(self, line: ScriptLine) -> str:
        """行に適した音声IDを取得"""
        # キャラクター設定があればそれを使用
        if line.character:
            for char in self.current_project.characters:
                if char.name == line.character:
                    return char.voice_id
        
        # デフォルト音声
        if line.role == "NA":
            return self.voice_parser.narration_voice
        else:
            return self.voice_parser.dialogue_voice
    
    def _get_voice_settings_for_line(self, line: ScriptLine) -> Dict:
        """行に適した音声設定を取得"""
        # 音声指示がある場合は専用設定
        if line.voice_instruction:
            return self.voice_parser.EMOTION_SETTINGS.get(
                line.voice_instruction, 
                {"stability": 0.5, "similarity_boost": 0.8, "style": 0.3}
            )
        
        # デフォルト設定
        return {"stability": 0.5, "similarity_boost": 0.8, "style": 0.3}
    
    def _update_generation_progress(self, line_index: int, line: ScriptLine):
        """生成進捗更新"""
        self.overall_progress_text.set(f"進行中... {line_index + 1}/{len(self.current_project.script_lines)}")
        self.current_progress_text.set(f"生成中: {line.text[:30]}...")
        
        # スクリプト一覧の状態更新
        items = self.script_tree.get_children()
        if line_index < len(items):
            item = items[line_index]
            values = list(self.script_tree.item(item)["values"])
            values[5] = "生成中"
            self.script_tree.item(item, values=values)
    
    def _update_result_display(self, result: TTSResult):
        """結果表示更新"""
        # 結果テーブルに追加
        status = "✅ 完了" if result.success else "❌ 失敗"
        filename = result.audio_file_path.name if result.success else "-"
        duration_str = f"{result.duration:.1f}s" if result.success else "-"
        
        # 対応するスクリプト行を取得
        script_line = None
        for line in self.current_project.script_lines:
            if line.line_number == result.line_number:
                script_line = line
                break
        
        text_preview = script_line.text[:30] + "..." if script_line and len(script_line.text) > 30 else (script_line.text if script_line else "")
        
        self.results_tree.insert("", tk.END, values=(
            result.line_number,
            text_preview,
            duration_str,
            status,
            filename,
            "再生/削除"
        ))
        
        # スクリプト一覧の状態更新
        items = self.script_tree.get_children()
        for item in items:
            values = self.script_tree.item(item)["values"]
            if int(values[0]) == result.line_number:
                new_values = list(values)
                new_values[5] = status
                self.script_tree.item(item, values=new_values)
                break
        
        # カウンター更新
        completed_count = len([r for r in self.tts_results if r.success])
        total_count = len(self.current_project.script_lines)
        self.results_count_var.set(f"{completed_count}/{total_count} 完了")
    
    def _generation_complete(self):
        """生成完了処理"""
        self.generation_in_progress = False
        self.generate_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        self.current_progress.stop()
        self.overall_progress_text.set("完了!")
        self.current_progress_text.set("")
        
        # 完了通知
        completed_count = len([r for r in self.tts_results if r.success])
        failed_count = len([r for r in self.tts_results if not r.success])
        
        message = f"TTS生成完了!\n成功: {completed_count}件\n失敗: {failed_count}件"
        messagebox.showinfo("完了", message)
    
    def stop_generation(self):
        """生成停止"""
        self.generation_in_progress = False
        self.set_status("生成を停止しています...")
    
    def regenerate_selected(self):
        """選択行再生成"""
        selected = self.script_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "再生成する行を選択してください")
            return
        
        # 選択行の情報取得
        item = selected[0]
        values = self.script_tree.item(item)["values"]
        line_number = int(values[0])
        
        # 対応するスクリプト行を取得
        script_line = None
        line_index = 0
        for i, line in enumerate(self.current_project.script_lines):
            if line.line_number == line_number:
                script_line = line
                line_index = i
                break
        
        if not script_line:
            messagebox.showerror("エラー", "対象行が見つかりません")
            return
        
        # バックグラウンドで再生成
        def regenerate_worker():
            try:
                output_path = Path(self.output_path_var.get())
                result = self._generate_single_line(script_line, output_path, line_index)
                
                # 既存結果を更新
                for i, existing_result in enumerate(self.tts_results):
                    if existing_result.line_number == line_number:
                        self.tts_results[i] = result
                        break
                else:
                    self.tts_results.append(result)
                
                # UI更新
                self.root.after(0, lambda: self._update_result_display(result))
                self.root.after(0, lambda: messagebox.showinfo("完了", f"行 {line_number} の再生成が完了しました"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("エラー", f"再生成エラー: {e}"))
        
        threading.Thread(target=regenerate_worker).start()
    
    def on_result_double_click(self, event):
        """結果テーブルダブルクリック"""
        self.play_selected_audio()
    
    def play_selected_audio(self):
        """選択音声再生"""
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "再生する音声を選択してください")
            return
        
        item = selected[0]
        values = self.results_tree.item(item)["values"]
        filename = values[4]
        
        if filename == "-":
            messagebox.showwarning("警告", "再生可能な音声ファイルがありません")
            return
        
        output_path = Path(self.output_path_var.get())
        audio_path = output_path / filename
        
        if not audio_path.exists():
            messagebox.showerror("エラー", f"音声ファイルが見つかりません: {audio_path}")
            return
        
        if not PYGAME_AVAILABLE:
            messagebox.showwarning("警告", "音声再生機能が利用できません。pygameをインストールしてください。")
            return
        
        try:
            # pygame で再生
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()
            self.set_status(f"再生中: {filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"音声再生エラー: {e}")
    
    def stop_audio(self):
        """音声停止"""
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.set_status("音声停止")
    
    def open_output_folder(self):
        """出力フォルダを開く"""
        output_path = Path(self.output_path_var.get())
        if output_path.exists():
            import subprocess
            subprocess.run(["open", str(output_path)])
        else:
            messagebox.showwarning("警告", "出力フォルダが存在しません")
    
    def complete_step2(self):
        """Step 2 完了処理"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成または読み込んでください")
            return
        
        # 生成結果をプロジェクトに保存
        self.current_project.step2_completed = True
        
        # 保存
        self.save_project()
        
        # 次のステップに進む
        response = messagebox.askyesno(
            "Step 2 完了", 
            "Step 2 が完了しました。Step 3 (字幕調整) に進みますか？"
        )
        
        if response:
            self.launch_step("step3_subtitle_timing.py")
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理"""
        self.update_display()
        
        # 出力パス設定
        if self.current_project.project_path:
            default_output = self.current_project.project_path.parent / "output" / "audio"
            self.output_path_var.set(str(default_output))
    
    def on_project_save(self):
        """プロジェクト保存時の処理"""
        pass


def main():
    """メイン関数"""
    app = TTSGenerationWindow()
    app.run()


if __name__ == "__main__":
    main()
