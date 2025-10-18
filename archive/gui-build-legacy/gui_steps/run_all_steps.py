#!/usr/bin/env python3
"""
Complete Workflow Launcher
全ステップ統合ランチャー
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys
import subprocess

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))

from gui_base import BaseStepWindow
from data_models import Project

class WorkflowLauncherWindow(BaseStepWindow):
    """ワークフロー統合ランチャー"""
    
    def __init__(self):
        super().__init__("DaVinci Auto - Video Production Workflow", 1000, 600)
        
        # GUI セットアップ
        self.setup_launcher_layout()
        self.setup_workflow_overview()
        self.setup_step_cards()
        self.setup_quick_actions()
        
    def setup_launcher_layout(self):
        """ランチャーレイアウト"""
        # ヘッダー
        header_frame = ttk.Frame(self.content_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, 
                               text="🎬 DaVinci Auto Workflow", 
                               font=("", 16, "bold"))
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                  text="8分動画制作自動化パイプライン", 
                                  font=("", 12))
        subtitle_label.pack(pady=(5, 0))
        
        # メイン分割
        main_paned = ttk.PanedWindow(self.content_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左側: ワークフロー概要
        self.overview_frame = ttk.Frame(main_paned)
        main_paned.add(self.overview_frame, weight=1)
        
        # 右側: ステップカード
        self.cards_frame = ttk.Frame(main_paned)
        main_paned.add(self.cards_frame, weight=2)
    
    def setup_workflow_overview(self):
        """ワークフロー概要"""
        overview_label = ttk.LabelFrame(self.overview_frame, text="ワークフロー概要")
        overview_label.pack(fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 進捗表示
        progress_frame = ttk.Frame(overview_label)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(progress_frame, text="完了進捗:", font=("", 10, "bold")).pack(anchor=tk.W)
        
        self.workflow_progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=4)
        self.workflow_progress.pack(fill=tk.X, pady=5)
        
        self.progress_text = tk.StringVar(value="0/4 ステップ完了")
        ttk.Label(progress_frame, textvariable=self.progress_text).pack(anchor=tk.W)
        
        # ワークフロー図
        workflow_text = tk.Text(overview_label, height=15, wrap=tk.WORD, 
                               font=("Courier", 10), state="disabled")
        workflow_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        workflow_content = """┌─ STEP 1: スクリプト編集 ─┐
│ 📝 脚本テキスト編集      │
│ 🎭 キャラクター配役設定   │
│ 🎵 音声指示・感情設定    │
└─────────────────────────┘
           ⬇️
┌─ STEP 2: TTS音声生成 ───┐
│ 🔊 ElevenLabs TTS生成   │
│ 📊 バッチ処理・進捗管理   │
│ 🎧 プレビュー・再生成    │
└─────────────────────────┘
           ⬇️
┌─ STEP 3: 字幕タイミング ─┐
│ ⏰ 自動タイミング生成    │
│ ✏️ 手動調整・編集機能    │
│ 💾 SRT形式エクスポート   │
└─────────────────────────┘
           ⬇️
┌─ STEP 4: DaVinci出力 ───┐
│ 🔗 Resolve API連携     │
│ 📥 SRT自動インポート     │
│ 🎬 レンダリング・出力    │
└─────────────────────────┘
           ⬇️
        🎉 完成！"""
        
        workflow_text.configure(state="normal")
        workflow_text.insert("1.0", workflow_content)
        workflow_text.configure(state="disabled")
    
    def setup_step_cards(self):
        """ステップカード"""
        cards_label = ttk.LabelFrame(self.cards_frame, text="ステップ実行")
        cards_label.pack(fill=tk.BOTH, expand=True)
        
        # ステップ定義
        steps = [
            {
                "title": "Step 1: スクリプト編集",
                "description": "脚本入力・キャラクター配役・音声設定",
                "icon": "📝",
                "script": "step1_script_editor.py",
                "features": ["シンタックスハイライト", "自動キャラ抽出", "音声指示解析"]
            },
            {
                "title": "Step 2: TTS音声生成", 
                "description": "ElevenLabs統合・バッチ生成・品質管理",
                "icon": "🎵",
                "script": "step2_tts_generation.py",
                "features": ["並列生成対応", "リアルタイム進捗", "コスト追跡"]
            },
            {
                "title": "Step 3: 字幕タイミング",
                "description": "自動タイミング・手動調整・SRT出力",
                "icon": "⏰", 
                "script": "step3_subtitle_timing.py",
                "features": ["視覚的タイムライン", "精密調整", "統計出力"]
            },
            {
                "title": "Step 4: DaVinci出力",
                "description": "Resolve連携・レンダリング・最終出力",
                "icon": "🎬",
                "script": "step4_davinci_export.py", 
                "features": ["API自動接続", "プリセット対応", "キュー管理"]
            }
        ]
        
        # カード表示エリア
        cards_scroll_frame = ttk.Frame(cards_label)
        cards_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 各ステップカード作成
        for i, step in enumerate(steps):
            self.create_step_card(cards_scroll_frame, i+1, step)
    
    def create_step_card(self, parent, step_num, step_info):
        """ステップカード作成"""
        card_frame = ttk.LabelFrame(parent, text=f"{step_info['icon']} {step_info['title']}")
        card_frame.pack(fill=tk.X, pady=5)
        
        # カード内容
        content_frame = ttk.Frame(card_frame)
        content_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 説明
        desc_label = ttk.Label(content_frame, text=step_info['description'], 
                              font=("", 10))
        desc_label.pack(anchor=tk.W)
        
        # 機能リスト
        features_frame = ttk.Frame(content_frame)
        features_frame.pack(fill=tk.X, pady=(5, 0))
        
        features_text = " • ".join(step_info['features'])
        features_label = ttk.Label(features_frame, text=f"機能: {features_text}", 
                                  font=("", 9), foreground="gray")
        features_label.pack(anchor=tk.W)
        
        # ボタンフレーム
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 実行ボタン
        run_btn = ttk.Button(button_frame, text=f"Step {step_num} 実行", 
                            command=lambda script=step_info['script']: self.launch_step_script(script))
        run_btn.pack(side=tk.LEFT)
        
        # 状態表示
        status_var = tk.StringVar(value="未実行")
        status_label = ttk.Label(button_frame, textvariable=status_var, 
                               font=("", 9), foreground="orange")
        status_label.pack(side=tk.RIGHT)
        
        # 状態管理用（実際の実装では動的更新）
        setattr(self, f"step{step_num}_status_var", status_var)
    
    def setup_quick_actions(self):
        """クイックアクション"""
        # フッター
        footer_frame = ttk.Frame(self.content_frame)
        footer_frame.pack(fill=tk.X, pady=(20, 0))
        
        # クイックアクションボタン
        actions_frame = ttk.LabelFrame(footer_frame, text="クイックアクション")
        actions_frame.pack(fill=tk.X)
        
        button_frame = ttk.Frame(actions_frame)
        button_frame.pack(pady=10)
        
        # サンプルプロジェクト作成
        ttk.Button(button_frame, text="🏗️ サンプルプロジェクト作成", 
                  command=self.create_sample_project).pack(side=tk.LEFT, padx=5)
        
        # 全ステップ実行（デモ）
        ttk.Button(button_frame, text="🚀 デモワークフロー実行", 
                  command=self.run_demo_workflow).pack(side=tk.LEFT, padx=5)
        
        # ヘルプ
        ttk.Button(button_frame, text="❓ ヘルプ・説明", 
                  command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # 設定
        ttk.Button(button_frame, text="⚙️ 設定", 
                  command=self.show_settings).pack(side=tk.LEFT, padx=5)
    
    def launch_step_script(self, script_name):
        """ステップスクリプト起動"""
        try:
            script_path = Path(__file__).parent / script_name
            if script_path.exists():
                subprocess.Popen([sys.executable, str(script_path)])
                self.set_status(f"{script_name} を起動しました")
            else:
                messagebox.showerror("エラー", f"スクリプトが見つかりません: {script_name}")
        except Exception as e:
            messagebox.showerror("エラー", f"起動エラー: {e}")
    
    def create_sample_project(self):
        """サンプルプロジェクト作成"""
        sample_project = Project(name="サンプル動画プロジェクト")
        
        # サンプルスクリプト
        sample_script = """NA: 転職した同期の投稿を見て 焦りを感じたことはありませんか
NA: 転職は脱出なのか それとも逃避なのか
セリフ: 同僚A（女声・つぶやくように）：うちの会社 もう限界かもね
NA: 金曜日の飲み会 愚痴と不満のオンパレード みんな口々に転職を口にする
セリフ: モーセ（男声・力強く）：エジプトにいた方がよかった
NA: 自由の荒野で 民は奴隷時代を懐かしみ始めたのです"""
        
        sample_project.script_text = sample_script
        
        # プロジェクト保存
        save_path = Path.cwd() / "sample_project.json"
        sample_project.save_to_file(save_path)
        
        messagebox.showinfo("完了", f"サンプルプロジェクトを作成しました:\\n{save_path}")
    
    def run_demo_workflow(self):
        """デモワークフロー実行"""
        demo_message = """🚀 デモワークフロー

以下の順序で実行してください:

1️⃣ Step 1でサンプルプロジェクト読み込み
2️⃣ Step 2でTTS生成（テスト版使用推奨）
3️⃣ Step 3で字幕タイミング調整
4️⃣ Step 4でDaVinci Resolve出力

各ステップは独立して動作します。"""
        
        messagebox.showinfo("デモワークフロー", demo_message)
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """🎬 DaVinci Auto Workflow ヘルプ

## 基本的な使用方法
1. Step 1で脚本を編集・配役設定
2. Step 2でTTS音声生成
3. Step 3で字幕タイミング調整
4. Step 4でDaVinci Resolveに出力

## システム要件
• Python 3.8+
• DaVinci Resolve Studio (Step 4)
• ElevenLabs API Key (Step 2)

## トラブルシューティング
• 依存関係エラー: requirements.txtを確認
• DaVinci接続エラー: Studio版を使用
• TTS生成エラー: API Keyを確認

詳細は各ステップのヘルプを参照してください。"""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("ヘルプ")
        help_window.geometry("600x400")
        
        help_display = tk.Text(help_window, wrap=tk.WORD, font=("", 11))
        help_display.insert("1.0", help_text)
        help_display.configure(state="disabled")
        
        scrollbar = ttk.Scrollbar(help_window, orient=tk.VERTICAL, command=help_display.yview)
        help_display.configure(yscrollcommand=scrollbar.set)
        
        help_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
    
    def show_settings(self):
        """設定画面"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("500x400")
        
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API設定タブ
        api_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(api_frame, text="API設定")
        
        # ElevenLabs設定
        elevenlabs_frame = ttk.LabelFrame(api_frame, text="ElevenLabs TTS")
        elevenlabs_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(elevenlabs_frame, text="API Key:").pack(anchor=tk.W, padx=10, pady=5)
        api_key_entry = ttk.Entry(elevenlabs_frame, width=50, show="*")
        api_key_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # DaVinci設定タブ
        davinci_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(davinci_frame, text="DaVinci設定")
        
        resolve_frame = ttk.LabelFrame(davinci_frame, text="DaVinci Resolve")
        resolve_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(resolve_frame, text="インストールパス:").pack(anchor=tk.W, padx=10, pady=5)
        resolve_path = ttk.Entry(resolve_frame, width=50)
        resolve_path.pack(fill=tk.X, padx=10, pady=5)
        resolve_path.insert(0, "/Applications/DaVinci Resolve/DaVinci Resolve.app")
    
    def update_progress(self):
        """進捗更新（実際の実装では定期的に呼び出し）"""
        if self.current_project:
            completed = sum([
                self.current_project.step1_completed,
                self.current_project.step2_completed, 
                self.current_project.step3_completed,
                self.current_project.step4_completed
            ])
            
            self.workflow_progress.configure(value=completed)
            self.progress_text.set(f"{completed}/4 ステップ完了")
            
            # 各ステップの状態更新
            statuses = ["完了" if completed else "未実行" for completed in [
                self.current_project.step1_completed,
                self.current_project.step2_completed,
                self.current_project.step3_completed, 
                self.current_project.step4_completed
            ]]
            
            for i, status in enumerate(statuses):
                status_var = getattr(self, f"step{i+1}_status_var", None)
                if status_var:
                    status_var.set(status)
    
    def on_project_loaded(self):
        """プロジェクト読み込み時の処理"""
        self.update_progress()
    
    def on_project_save(self):
        """プロジェクト保存時の処理"""
        pass


def main():
    """メイン関数"""
    app = WorkflowLauncherWindow()
    app.run()


if __name__ == "__main__":
    main()