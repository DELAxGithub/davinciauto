#!/usr/bin/env python3
"""
ElevenLabs v3 Alpha 複数生成→選択ワークフロー
最高品質音声のための選択機能付きGUIコンポーネント
"""
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import threading
import queue
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️  pygame未インストール - 音声再生機能が無効です")

from common.gui_base import BaseGUI


class AudioQualitySelector(BaseGUI):
    """
    ElevenLabs v3 Alpha 複数音声生成・選択GUI

    アルファ版推奨ワークフロー:
    1. 同じテキストで3-5つの音声を生成
    2. ユーザーがプレビュー・比較
    3. 最良の音声を選択・採用
    """

    def __init__(self, parent=None):
        super().__init__(parent, "Audio Quality Selector - ElevenLabs v3 Alpha")
        self.generated_audio_files = []
        self.selected_audio = None
        self.audio_queue = queue.Queue()
        self.is_generating = False

        # pygame初期化（可能な場合）
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.audio_enabled = True
            except pygame.error:
                self.audio_enabled = False
                print("⚠️  pygame音声システム初期化失敗")
        else:
            self.audio_enabled = False

        self.create_widgets()
        self.style_widgets()

    def create_widgets(self):
        """UIコンポーネント作成"""

        # ヘッダー
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            header_frame,
            text="🎵 ElevenLabs v3 Alpha Quality Selector",
            font=("Helvetica", 16, "bold")
        ).pack()

        ttk.Label(
            header_frame,
            text="最高品質音声のための複数生成→選択ワークフロー",
            font=("Helvetica", 10)
        ).pack()

        # 入力エリア
        input_frame = ttk.LabelFrame(self.root, text="📝 テキスト入力", padding=10)
        input_frame.pack(fill="x", padx=20, pady=5)

        self.text_input = tk.Text(input_frame, height=4, wrap="word", font=("Helvetica", 11))
        self.text_input.pack(fill="x", pady=5)
        self.text_input.insert("1.0", "今日は良い天気ですね。外で散歩でもしましょうか。")

        # 音声設定
        settings_frame = ttk.LabelFrame(self.root, text="🎯 音声設定", padding=10)
        settings_frame.pack(fill="x", padx=20, pady=5)

        # 音声タイプ選択
        voice_frame = ttk.Frame(settings_frame)
        voice_frame.pack(fill="x", pady=5)

        ttk.Label(voice_frame, text="音声タイプ:").pack(side="left", padx=(0, 10))
        self.voice_type = tk.StringVar(value="narration")
        ttk.Radiobutton(voice_frame, text="ナレーション", variable=self.voice_type, value="narration").pack(side="left", padx=5)
        ttk.Radiobutton(voice_frame, text="対話", variable=self.voice_type, value="dialogue").pack(side="left", padx=5)

        # 生成数設定
        count_frame = ttk.Frame(settings_frame)
        count_frame.pack(fill="x", pady=5)

        ttk.Label(count_frame, text="生成数:").pack(side="left", padx=(0, 10))
        self.generation_count = tk.StringVar(value="3")
        count_spin = ttk.Spinbox(count_frame, from_=2, to=5, textvariable=self.generation_count, width=5)
        count_spin.pack(side="left", padx=5)
        ttk.Label(count_frame, text="（推奨: 3-5つ）", font=("Helvetica", 9)).pack(side="left", padx=5)

        # 生成ボタン
        generate_frame = ttk.Frame(self.root)
        generate_frame.pack(fill="x", padx=20, pady=10)

        self.generate_btn = ttk.Button(
            generate_frame,
            text="🚀 複数音声生成開始 (v3 Alpha)",
            command=self.start_generation,
            style="Action.TButton"
        )
        self.generate_btn.pack(side="left", padx=5)

        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            generate_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side="left", padx=10, fill="x", expand=True)

        # ステータス
        self.status_label = ttk.Label(generate_frame, text="準備完了", font=("Helvetica", 9))
        self.status_label.pack(side="right", padx=5)

        # 音声選択エリア
        self.selection_frame = ttk.LabelFrame(self.root, text="🎧 音声比較・選択", padding=10)
        self.selection_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 初期状態では非表示
        self.selection_frame.pack_forget()

        # 選択結果
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill="x", padx=20, pady=10)

        self.selected_label = ttk.Label(result_frame, text="選択音声: なし", font=("Helvetica", 10, "bold"))
        self.selected_label.pack(side="left")

        self.adopt_btn = ttk.Button(
            result_frame,
            text="✅ 選択音声を採用",
            command=self.adopt_selected_audio,
            state="disabled",
            style="Success.TButton"
        )
        self.adopt_btn.pack(side="right")

    def style_widgets(self):
        """ウィジェットスタイル設定"""
        style = ttk.Style()

        # カスタムボタンスタイル
        style.configure("Action.TButton", font=("Helvetica", 10, "bold"))
        style.configure("Success.TButton", font=("Helvetica", 10, "bold"))
        style.configure("Play.TButton", font=("Helvetica", 9))

    def start_generation(self):
        """複数音声生成開始"""
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("入力エラー", "テキストを入力してください")
            return

        if self.is_generating:
            messagebox.showinfo("生成中", "既に音声生成中です。しばらくお待ちください。")
            return

        count = int(self.generation_count.get())
        voice_type = self.voice_type.get()

        # UI状態更新
        self.is_generating = True
        self.generate_btn.config(state="disabled", text="生成中...")
        self.progress_var.set(0)
        self.status_label.config(text="音声生成開始...")
        self.selection_frame.pack_forget()
        self.clear_previous_results()

        # バックグラウンドで生成開始
        thread = threading.Thread(
            target=self.generate_multiple_audio,
            args=(text, voice_type, count),
            daemon=True
        )
        thread.start()

    def generate_multiple_audio(self, text: str, voice_type: str, count: int):
        """複数音声生成（バックグラウンド処理）"""
        try:
            self.generated_audio_files = []

            for i in range(count):
                # プログレス更新
                progress = (i / count) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda i=i: self.status_label.config(text=f"音声生成中 {i+1}/{count}..."))

                # 音声生成（モック - 実際のAPI呼び出しに置き換え）
                audio_file = self.generate_single_audio_mock(text, voice_type, i+1)
                if audio_file:
                    self.generated_audio_files.append({
                        'file': audio_file,
                        'text': text,
                        'voice_type': voice_type,
                        'index': i+1,
                        'selected': False
                    })

                # 小休憩（API制限対応）
                time.sleep(1)

            # 完了処理
            self.root.after(0, self.generation_complete)

        except Exception as e:
            self.root.after(0, lambda: self.generation_error(str(e)))

    def generate_single_audio_mock(self, text: str, voice_type: str, index: int) -> Optional[str]:
        """
        単一音声生成（モック実装）
        実際の実装では、backend/main.py の /api/tts/generate を呼び出し
        """
        try:
            # 一時ファイル作成
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_v3alpha_{voice_type}_{index}.mp3",
                delete=False
            )
            temp_path = temp_file.name
            temp_file.close()

            # モック音声データ（実際にはAPI呼び出し）
            # TODO: requests.post to backend/main.py /api/tts/generate
            mock_audio_data = b"mock_audio_data_" + str(index).encode() * 1000

            with open(temp_path, 'wb') as f:
                f.write(mock_audio_data)

            return temp_path

        except Exception as e:
            print(f"音声生成エラー {index}: {e}")
            return None

    def generation_complete(self):
        """音声生成完了処理"""
        self.is_generating = False
        self.progress_var.set(100)
        self.status_label.config(text=f"生成完了 - {len(self.generated_audio_files)}個の音声")
        self.generate_btn.config(state="normal", text="🚀 複数音声生成開始 (v3 Alpha)")

        if self.generated_audio_files:
            self.create_selection_ui()
            self.selection_frame.pack(fill="both", expand=True, padx=20, pady=5)
        else:
            messagebox.showerror("生成失敗", "音声生成に失敗しました")

    def generation_error(self, error_msg: str):
        """音声生成エラー処理"""
        self.is_generating = False
        self.progress_var.set(0)
        self.status_label.config(text="生成失敗")
        self.generate_btn.config(state="normal", text="🚀 複数音声生成開始 (v3 Alpha)")
        messagebox.showerror("生成エラー", f"音声生成中にエラーが発生しました:\n{error_msg}")

    def create_selection_ui(self):
        """音声選択UI作成"""
        # 既存のUIをクリア
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        # ヘッダー
        header = ttk.Label(
            self.selection_frame,
            text=f"🎧 生成された{len(self.generated_audio_files)}個の音声から最良のものを選択してください",
            font=("Helvetica", 11, "bold")
        )
        header.pack(pady=10)

        # 音声カードコンテナ
        cards_frame = ttk.Frame(self.selection_frame)
        cards_frame.pack(fill="both", expand=True, pady=10)

        self.audio_selection_var = tk.StringVar()

        for audio_info in self.generated_audio_files:
            self.create_audio_card(cards_frame, audio_info)

    def create_audio_card(self, parent: ttk.Widget, audio_info: Dict):
        """個別音声選択カード作成"""
        # カードフレーム
        card = ttk.LabelFrame(
            parent,
            text=f"🎵 音声 #{audio_info['index']} - {audio_info['voice_type']}",
            padding=10
        )
        card.pack(fill="x", pady=5)

        # 選択ラジオボタン
        select_radio = ttk.Radiobutton(
            card,
            text="この音声を選択",
            variable=self.audio_selection_var,
            value=str(audio_info['index']),
            command=lambda: self.select_audio(audio_info)
        )
        select_radio.pack(side="left")

        # 再生ボタン
        if self.audio_enabled:
            play_btn = ttk.Button(
                card,
                text="▶️ 再生",
                command=lambda: self.play_audio(audio_info['file']),
                style="Play.TButton",
                width=10
            )
            play_btn.pack(side="left", padx=10)
        else:
            ttk.Label(card, text="🔇 音声再生無効", font=("Helvetica", 9)).pack(side="left", padx=10)

        # ファイル情報
        file_info = f"ファイル: {Path(audio_info['file']).name}"
        ttk.Label(card, text=file_info, font=("Helvetica", 9)).pack(side="right")

    def select_audio(self, audio_info: Dict):
        """音声選択処理"""
        self.selected_audio = audio_info
        self.selected_label.config(text=f"選択音声: #{audio_info['index']} ({audio_info['voice_type']})")
        self.adopt_btn.config(state="normal")

    def play_audio(self, audio_file: str):
        """音声再生"""
        if not self.audio_enabled:
            messagebox.showinfo("再生不可", "音声再生機能が無効です")
            return

        try:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            self.status_label.config(text="再生中...")
        except Exception as e:
            messagebox.showerror("再生エラー", f"音声再生に失敗しました:\n{str(e)}")

    def adopt_selected_audio(self):
        """選択音声採用処理"""
        if not self.selected_audio:
            messagebox.showwarning("選択エラー", "音声が選択されていません")
            return

        # 選択音声を最終出力として採用
        selected_file = self.selected_audio['file']
        output_path = Path("output/audio/selected_quality.mp3")

        try:
            import shutil
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(selected_file, output_path)

            messagebox.showinfo(
                "採用完了",
                f"音声 #{self.selected_audio['index']} を採用しました\n保存先: {output_path}"
            )

            self.status_label.config(text="音声採用完了")

        except Exception as e:
            messagebox.showerror("採用エラー", f"音声採用に失敗しました:\n{str(e)}")

    def clear_previous_results(self):
        """前回結果クリア"""
        # 一時ファイルクリーンアップ
        for audio_info in self.generated_audio_files:
            try:
                Path(audio_info['file']).unlink(missing_ok=True)
            except:
                pass

        self.generated_audio_files = []
        self.selected_audio = None
        self.selected_label.config(text="選択音声: なし")
        self.adopt_btn.config(state="disabled")

    def on_closing(self):
        """ウィンドウ終了時の処理"""
        self.clear_previous_results()
        if self.audio_enabled:
            try:
                pygame.mixer.quit()
            except:
                pass
        super().on_closing()


def main():
    """メイン実行"""
    app = AudioQualitySelector()
    app.run()


if __name__ == "__main__":
    main()