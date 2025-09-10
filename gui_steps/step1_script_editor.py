#!/usr/bin/env python3
"""
Step 1: Script Editor with Voice Assignment GUI
スクリプト編集・配役設定GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys
import re
from typing import List, Dict, Optional

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))
sys.path.append(str(Path(__file__).parent.parent / "minivt_pipeline" / "src"))

from gui_base import BaseStepWindow, SyntaxHighlightText
from data_models import Project, ScriptLine, Character
from utils.voice_parser import VoiceInstructionParser

class ScriptEditorWindow(BaseStepWindow):
    """スクリプト編集・配役設定ウィンドウ"""
    
    def __init__(self):
        super().__init__("Step 1: スクリプト編集・配役設定", 1200, 800, current_step="step1-script-editor")
        
        # Voice parser
        self.voice_parser = VoiceInstructionParser()
        
        # GUI セットアップ
        self.setup_main_layout()
        self.setup_script_editor()
        self.setup_character_panel()
        self.setup_preview_panel()
        
        # 初期状態
        self.update_preview()
    
    def setup_main_layout(self):
        """メインレイアウト設定"""
        # 3分割レイアウト: エディタ | キャラクター | プレビュー
        self.paned_window = ttk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # エディタフレーム (左)
        self.editor_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.editor_frame, weight=2)
        
        # キャラクターフレーム (中央)
        self.character_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.character_frame, weight=1)
        
        # プレビューフレーム (右)
        self.preview_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.preview_frame, weight=1)
    
    def setup_script_editor(self):
        """スクリプトエディタセットアップ"""
        # エディタヘッダー
        header_frame = ttk.Frame(self.editor_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="スクリプト編集", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="ファイルから読み込み", 
                  command=self.load_script_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header_frame, text="サンプル読み込み", 
                  command=self.load_sample_script).pack(side=tk.RIGHT, padx=5)
        
        # テキストエディタ (シンタックスハイライト付き)
        editor_container = ttk.Frame(self.editor_frame)
        editor_container.pack(fill=tk.BOTH, expand=True)
        
        self.script_editor = SyntaxHighlightText(
            editor_container, 
            wrap=tk.WORD,
            font=("Consolas", 11),
            undo=True
        )
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(editor_container, orient=tk.VERTICAL, 
                                 command=self.script_editor.yview)
        self.script_editor.configure(yscrollcommand=scrollbar.set)
        
        self.script_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # テキスト変更時の自動更新
        self.script_editor.bind("<KeyRelease>", self.on_script_change)
        
        # フォーマットヘルプ
        help_frame = ttk.Frame(self.editor_frame)
        help_frame.pack(fill=tk.X, pady=(10, 0))
        
        help_text = """フォーマット例:
NA: ナレーションテキスト
セリフ: キャラクター名（男声・疲れ切った声で）：実際の台詞
セリフ: キャラクターB（女声・つぶやくように）：別のキャラクターの台詞"""
        
        ttk.Label(help_frame, text=help_text, 
                 font=("", 9), foreground="gray").pack(anchor=tk.W)
    
    def setup_character_panel(self):
        """キャラクター設定パネル"""
        # ヘッダー
        header_frame = ttk.Frame(self.character_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="キャラクター設定", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="追加", 
                  command=self.add_character).pack(side=tk.RIGHT, padx=5)
        
        # キャラクター一覧
        list_frame = ttk.Frame(self.character_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for characters
        columns = ("name", "gender", "voice_id")
        self.character_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        self.character_tree.heading("name", text="キャラクター")
        self.character_tree.heading("gender", text="性別")
        self.character_tree.heading("voice_id", text="音声ID")
        
        self.character_tree.column("name", width=120)
        self.character_tree.column("gender", width=60)
        self.character_tree.column("voice_id", width=100)
        
        # スクロールバー
        char_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                      command=self.character_tree.yview)
        self.character_tree.configure(yscrollcommand=char_scrollbar.set)
        
        self.character_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        char_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # キャラクター編集フレーム
        edit_frame = ttk.Frame(self.character_frame)
        edit_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(edit_frame, text="選択キャラクター編集:").pack(anchor=tk.W)
        
        # 名前
        ttk.Label(edit_frame, text="名前:").pack(anchor=tk.W, pady=(5, 0))
        self.char_name_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.char_name_var).pack(fill=tk.X, pady=(0, 5))
        
        # 性別
        ttk.Label(edit_frame, text="性別:").pack(anchor=tk.W)
        self.char_gender_var = tk.StringVar()
        gender_combo = ttk.Combobox(edit_frame, textvariable=self.char_gender_var,
                                   values=["male", "female"], state="readonly")
        gender_combo.pack(fill=tk.X, pady=(0, 5))
        
        # 音声ID
        ttk.Label(edit_frame, text="音声ID:").pack(anchor=tk.W)
        self.char_voice_id_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.char_voice_id_var).pack(fill=tk.X, pady=(0, 5))
        
        # ボタン
        button_frame = ttk.Frame(edit_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="更新", 
                  command=self.update_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="削除", 
                  command=self.delete_character).pack(side=tk.LEFT, padx=5)
        
        # イベントバインディング
        self.character_tree.bind("<<TreeviewSelect>>", self.on_character_select)
    
    def setup_preview_panel(self):
        """プレビューパネル"""
        # ヘッダー
        header_frame = ttk.Frame(self.preview_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="プレビュー", 
                 font=("", 12, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="更新", 
                  command=self.update_preview).pack(side=tk.RIGHT, padx=5)
        
        # プレビューリスト
        preview_frame = ttk.Frame(self.preview_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("line", "role", "character", "voice", "text")
        self.preview_tree = ttk.Treeview(preview_frame, columns=columns, show="headings")
        
        self.preview_tree.heading("line", text="#")
        self.preview_tree.heading("role", text="種類")  
        self.preview_tree.heading("character", text="キャラ")
        self.preview_tree.heading("voice", text="音声")
        self.preview_tree.heading("text", text="テキスト")
        
        self.preview_tree.column("line", width=30)
        self.preview_tree.column("role", width=50)
        self.preview_tree.column("character", width=80)
        self.preview_tree.column("voice", width=80)
        self.preview_tree.column("text", width=200)
        
        # スクロールバー
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL,
                                         command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 完了ボタン
        complete_frame = ttk.Frame(self.preview_frame)
        complete_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(complete_frame, text="Step 1 完了 → Step 2へ", 
                  command=self.complete_step1,
                  style="Accent.TButton").pack(fill=tk.X)
    
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
                self.update_preview()
                self.set_status(f"ファイル読み込み完了: {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("エラー", f"ファイル読み込みエラー: {e}")
    
    def load_sample_script(self):
        """サンプルスクリプト読み込み"""
        sample_script = """NA: 転職した同期の投稿を見て 焦りを感じたことはありませんか
NA: 転職は脱出なのか それとも逃避なのか
セリフ: 同僚A（女声・つぶやくように）：うちの会社 もう限界かもね
NA: 金曜日の飲み会 愚痴と不満のオンパレード
セリフ: モーセ（男声・力強く）：エジプトにいた方がよかった あそこには肉鍋があり パンを腹いっぱい食べられた
NA: 自由の荒野で 民は奴隷時代を懐かしみ始めたのです"""
        
        self.script_editor.delete("1.0", tk.END)
        self.script_editor.insert("1.0", sample_script)
        self.update_preview()
        self.set_status("サンプルスクリプトを読み込みました")
    
    def on_script_change(self, event=None):
        """スクリプト変更時の処理"""
        # 少し遅延してからプレビュー更新（連続入力対応）
        self.root.after(500, self.update_preview)
    
    def parse_script_lines(self) -> List[ScriptLine]:
        """スクリプトテキストを解析してScriptLineリストを生成"""
        script_text = self.script_editor.get("1.0", tk.END).strip()
        lines = []
        
        for line_num, line in enumerate(script_text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            
            script_line = ScriptLine(line_number=line_num)
            
            if line.startswith("NA:"):
                script_line.role = "NA"
                script_line.text = line.replace("NA:", "", 1).strip()
                
                # 音声指示解析
                instruction = self.voice_parser.parse_voice_instruction(script_line.text)
                script_line.text = instruction.clean_text
                script_line.voice_instruction = instruction.emotion
                
            elif line.startswith("セリフ:"):
                script_line.role = "DL"
                content = line.replace("セリフ:", "", 1).strip()
                
                # キャラクター名と音声指示を解析
                char_match = re.match(r'^([^（：]+)（?([^）]*)）?[:：]?(.*)$', content)
                if char_match:
                    script_line.character = char_match.group(1).strip()
                    voice_inst = char_match.group(2) or ""
                    script_line.text = char_match.group(3).strip()
                    
                    # 音声指示解析
                    if voice_inst:
                        instruction = self.voice_parser.parse_voice_instruction(f"（{voice_inst}）")
                        script_line.voice_instruction = instruction.emotion
                else:
                    script_line.text = content
            
            lines.append(script_line)
        
        return lines
    
    def update_preview(self):
        """プレビューを更新"""
        # プレビューリストクリア
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # スクリプト解析
        script_lines = self.parse_script_lines()
        
        # プレビューリスト更新
        for script_line in script_lines:
            voice_info = script_line.voice_instruction or "デフォルト"
            char_name = script_line.character or "-"
            
            # テキストを短縮
            display_text = script_line.text[:50] + "..." if len(script_line.text) > 50 else script_line.text
            
            self.preview_tree.insert("", tk.END, values=(
                script_line.line_number,
                script_line.role,
                char_name,
                voice_info,
                display_text
            ))
        
        # キャラクター自動抽出・更新
        self.auto_extract_characters(script_lines)
    
    def auto_extract_characters(self, script_lines: List[ScriptLine]):
        """スクリプトからキャラクターを自動抽出"""
        # 既存キャラクター名リスト
        existing_chars = {item[1] for item in self.character_tree.get_children() 
                         if self.character_tree.item(item)["values"]}
        
        # 新しいキャラクター検出
        new_characters = set()
        for line in script_lines:
            if line.character and line.character not in existing_chars:
                new_characters.add(line.character)
        
        # 新しいキャラクター追加
        for char_name in new_characters:
            default_voice = self.voice_parser.dialogue_voice
            self.character_tree.insert("", tk.END, values=(char_name, "不明", default_voice))
    
    def add_character(self):
        """手動でキャラクター追加"""
        name = tk.simpledialog.askstring("キャラクター追加", "キャラクター名:")
        if name:
            default_voice = self.voice_parser.dialogue_voice
            self.character_tree.insert("", tk.END, values=(name, "不明", default_voice))
    
    def on_character_select(self, event):
        """キャラクター選択時の処理"""
        selected = self.character_tree.selection()
        if selected:
            item = selected[0]
            values = self.character_tree.item(item)["values"]
            
            self.char_name_var.set(values[0])
            self.char_gender_var.set(values[1] if values[1] != "不明" else "")
            self.char_voice_id_var.set(values[2])
    
    def update_character(self):
        """キャラクター情報更新"""
        selected = self.character_tree.selection()
        if selected:
            item = selected[0]
            self.character_tree.item(item, values=(
                self.char_name_var.get(),
                self.char_gender_var.get() or "不明",
                self.char_voice_id_var.get()
            ))
    
    def delete_character(self):
        """キャラクター削除"""
        selected = self.character_tree.selection()
        if selected:
            response = messagebox.askyesno("削除確認", "選択したキャラクターを削除しますか？")
            if response:
                self.character_tree.delete(selected[0])
    
    def complete_step1(self):
        """Step 1 完了処理"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを作成または読み込んでください")
            return
        
        # スクリプトとキャラクター情報をプロジェクトに保存
        self.current_project.script_text = self.script_editor.get("1.0", tk.END).strip()
        self.current_project.script_lines = self.parse_script_lines()
        
        # キャラクター情報を保存
        characters = []
        for item in self.character_tree.get_children():
            values = self.character_tree.item(item)["values"]
            char = Character(
                name=values[0],
                gender=values[1] if values[1] != "不明" else None,
                voice_id=values[2]
            )
            characters.append(char)
        
        self.current_project.characters = characters
        self.current_project.step1_completed = True
        
        # 保存
        self.save_project()
        
        # 次のステップに進む
        response = messagebox.askyesno(
            "Step 1 完了", 
            "Step 1 が完了しました。Step 2 (TTS生成) に進みますか？"
        )
        
        if response:
            self.launch_step("step2_tts_generation.py")
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理"""
        if self.current_project.script_text:
            self.script_editor.delete("1.0", tk.END)
            self.script_editor.insert("1.0", self.current_project.script_text)
        
        # キャラクター情報読み込み
        for item in self.character_tree.get_children():
            self.character_tree.delete(item)
        
        for char in self.current_project.characters:
            self.character_tree.insert("", tk.END, values=(
                char.name, 
                char.gender or "不明", 
                char.voice_id
            ))
        
        self.update_preview()
    
    def on_project_save(self):
        """プロジェクト保存時の処理"""
        if self.current_project:
            self.current_project.script_text = self.script_editor.get("1.0", tk.END).strip()
            self.current_project.script_lines = self.parse_script_lines()


def main():
    """メイン関数"""
    import tkinter.simpledialog as simpledialog
    
    app = ScriptEditorWindow()
    app.run()


if __name__ == "__main__":
    main()