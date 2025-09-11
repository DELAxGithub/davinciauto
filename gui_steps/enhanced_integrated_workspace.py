#!/usr/bin/env python3
"""
Enhanced Integrated Video Production Workspace
統合動画制作ワークスペース - 新機能統合版

- 台本解析・セクション分割
- CPS警告システム
- 発音辞書システム
- API制限監視
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinter.simpledialog
from pathlib import Path
import sys
import json
import os
from typing import List, Dict, Optional, Tuple
import threading
import time
import datetime
import re
import csv

# .env file loading
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "common"))
sys.path.append(str(Path(__file__).parent.parent / "minivt_pipeline" / "src"))

# Import existing modules
from data_models import Project, ScriptLine, Character
from utils.voice_parser import VoiceInstructionParser
# wrap-based fallbacksは使用しない（LLM以外のロールバックを廃止）
from utils.srt import Cue as SrtCue, build_srt
import shutil

# Import new analysis modules (from local copies)
from script_parser import ScriptParser, CPSAnalyzer, create_test_analyzer, SpeakerType
from pronunciation_dict import PronunciationDictionary, create_orion_dictionary
from api_limiter import APILimiter, APIType, LimitMode, create_test_limiter

# TTS client import
try:
    from enhanced_tts_client import EnhancedTTSClient, TTSRequest, TTSResult, create_test_client
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# Fallback TTS client
try:
    from simple_tts_fallback import SimpleTTSClient, SimpleTTSResult, create_simple_client
    SIMPLE_TTS_AVAILABLE = True
except ImportError:
    SIMPLE_TTS_AVAILABLE = False

# GPT client import for storyboard generation
try:
    sys.path.append(str(Path(__file__).parent.parent / "minivt_pipeline" / "src" / "clients"))
    from gpt_client import GPTClient
    GPT_AVAILABLE = True
except ImportError as e:
    print(f"GPT Client import error: {e}")
    GPT_AVAILABLE = False

class EnhancedIntegratedWorkspace:
    """拡張統合動画制作ワークスペース"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 DaVinci Auto - 拡張統合ワークスペース")
        self.root.geometry("1800x1200")
        # Install exception hook to capture Tkinter callback errors
        self._install_exception_hook()
        # Make messageboxes thread-safe
        self._install_threadsafe_ui_helpers()
        
        # .env file loading
        print("🔧 環境変数読み込み開始...")
        self.load_environment_variables()
        
        # デバッグ: 読み込み後の環境変数チェック
        api_key = os.getenv("ELEVENLABS_API_KEY")
        print(f"🔍 読み込み後チェック: ELEVENLABS_API_KEY = {api_key[:8] + '...' if api_key else 'None'}")
        print("🔧 環境変数読み込み完了")
        
        # Voice management
        self.available_voices = {}
        self.load_voice_configuration()
        
        # Analysis engines
        self.script_parser = ScriptParser()
        self.cps_analyzer = create_test_analyzer()
        self.pronunciation_dict = create_orion_dictionary()
        self.api_limiter = create_test_limiter(LimitMode.DEVELOPMENT)
        
        # TTS engine
        self.tts_client = None
        self.simple_tts_client = None
        self.tts_init_error = None
        self.use_simple_client = False
        
        # Try enhanced client first
        if TTS_AVAILABLE:
            try:
                self.tts_client = create_test_client(LimitMode.DEMO)  # DEMO mode for safety
                self.tts_init_error = None
            except Exception as e:
                self.tts_init_error = f"Enhanced client error: {str(e)}"
                self.tts_client = None
        
        # Fallback to simple client
        if self.tts_client is None and SIMPLE_TTS_AVAILABLE:
            try:
                self.simple_tts_client = create_simple_client()
                self.use_simple_client = True
                self.tts_init_error = None
            except Exception as e:
                self.tts_init_error = f"Simple client error: {str(e)}"
                self.simple_tts_client = None
        
        # Final fallback error
        if self.tts_client is None and self.simple_tts_client is None:
            if not self.tts_init_error:
                self.tts_init_error = "TTSクライアントライブラリが利用できません"
        
        # GPT client for storyboard generation
        self.gpt_client = None
        self.gpt_init_error = None
        if GPT_AVAILABLE:
            try:
                self.gpt_client = GPTClient()
                self.gpt_init_error = None
            except Exception as e:
                self.gpt_init_error = f"GPT client error: {str(e)}"
                self.gpt_client = None
        
        # プロジェクト管理
        self.current_project: Optional[Project] = None
        self.project_file: Optional[Path] = None
        self.voice_parser = VoiceInstructionParser()
        
        # 解析結果
        self.parsed_segments = []
        self.cps_warnings = []
        self.pronunciation_matches = []
        
        # 文字コンテ・BGM解析結果
        self.storyboard_data = []
        self.music_prompts_data = []
        # 字幕データ（SRT用）
        self.subtitle_cues_data = []  # [{index, start, end, duration, lines:[...]}]
        
        # GUI状態管理
        self.current_step = 1
        self.step_completion_status = [False, False, False, False]
        
        # メインGUI構築
        self.setup_main_layout()
        self.setup_toolbar()
        self.setup_enhanced_tabs()
        self.setup_status_bar()
        
        # 初期状態
        self.update_all_displays()

    def _install_exception_hook(self):
        """Install a Tkinter callback exception handler that logs to file and shows a message."""
        def _handler(exc, val, tb):
            try:
                import traceback, sys
                from pathlib import Path as _Path
                log_dir = _Path("output/logs")
                log_dir.mkdir(parents=True, exist_ok=True)
                text = ''.join(traceback.format_exception(exc, val, tb))
                (log_dir / "gui_traceback.log").write_text(text, encoding="utf-8")
                print(text, file=sys.stderr)
                try:
                    messagebox.showerror("エラー", "予期しないエラーが発生しました。output/logs/gui_traceback.log を確認してください。")
                except Exception:
                    pass
            except Exception:
                pass
        # Hook into Tk's exception reporting
        try:
            self.root.report_callback_exception = _handler
        except Exception:
            pass

    def _install_threadsafe_ui_helpers(self):
        """Patch messagebox functions to run on Tk main thread."""
        try:
            import tkinter.messagebox as mb
            def wrap(fn):
                def _inner(*a, **kw):
                    try:
                        self.root.after(0, lambda: fn(*a, **kw))
                    except Exception:
                        pass
                return _inner
            mb.showinfo = wrap(mb.showinfo)
            mb.showwarning = wrap(mb.showwarning)
            mb.showerror = wrap(mb.showerror)
        except Exception:
            pass

    def ui_call(self, fn, *args, **kwargs):
        """Schedule a callable to run on the Tk main thread."""
        try:
            self.root.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

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
        ttk.Button(project_frame, text="台本読み込み", command=self.load_script_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(project_frame, text="デモ読込", command=self.load_demo_script).pack(side=tk.LEFT, padx=2)
        ttk.Button(project_frame, text="保存", command=self.save_project).pack(side=tk.LEFT, padx=2)
        
        # 解析アクション
        analysis_frame = ttk.LabelFrame(toolbar, text="解析")
        analysis_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(analysis_frame, text="台本解析", command=self.analyze_script).pack(side=tk.LEFT, padx=2)
        ttk.Button(analysis_frame, text="CPS チェック", command=self.check_cps).pack(side=tk.LEFT, padx=2)
        ttk.Button(analysis_frame, text="発音チェック", command=self.check_pronunciation).pack(side=tk.LEFT, padx=2)
        
        # API監視
        api_frame = ttk.LabelFrame(toolbar, text="API監視")
        api_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.api_status_var = tk.StringVar(value="DEV制限")
        ttk.Label(api_frame, textvariable=self.api_status_var).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_frame, text="使用量", command=self.show_api_usage).pack(side=tk.LEFT, padx=2)
        ttk.Button(api_frame, text="LLM設定", command=self.show_llm_settings).pack(side=tk.LEFT, padx=2)
        
        # プロジェクト情報表示
        info_frame = ttk.LabelFrame(toolbar, text="プロジェクト情報")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.project_name_var = tk.StringVar(value="プロジェクト未選択")
        ttk.Label(info_frame, text="名前:").pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, textvariable=self.project_name_var, font=("", 10, "bold")).pack(side=tk.LEFT)
    
    def setup_enhanced_tabs(self):
        """拡張タブセットアップ"""
        # ノートブック（タブコンテナ）
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 各タブセットアップ
        self.setup_script_analysis_tab()
        self.setup_cps_warning_tab()
        self.setup_pronunciation_tab()
        self.setup_api_monitoring_tab()
        self.setup_production_tab()
    
    def setup_script_analysis_tab(self):
        """台本解析タブ"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="📋 台本解析")
        
        # 左右分割
        paned = ttk.PanedWindow(tab_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左: 台本入力
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="台本テキスト", font=("", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        self.script_text = scrolledtext.ScrolledText(left_frame, width=60, height=30, wrap=tk.WORD)
        self.script_text.pack(fill=tk.BOTH, expand=True)
        self.script_text.bind('<KeyRelease>', self.on_script_change)
        
        # 右: 解析結果
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="解析結果", font=("", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        # 統計表示
        stats_frame = ttk.LabelFrame(right_frame, text="統計")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=6, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X, padx=5, pady=5)
        
        # セクション表示
        sections_frame = ttk.LabelFrame(right_frame, text="セクション詳細")
        sections_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # セクションツリービュー
        columns = ("section", "segments", "speakers", "issues")
        self.sections_tree = ttk.Treeview(sections_frame, columns=columns, show="headings", height=15)
        
        self.sections_tree.heading("section", text="セクション")
        self.sections_tree.heading("segments", text="セグメント数")
        self.sections_tree.heading("speakers", text="話者構成")
        self.sections_tree.heading("issues", text="問題")
        
        self.sections_tree.column("section", width=200)
        self.sections_tree.column("segments", width=80)
        self.sections_tree.column("speakers", width=120)
        self.sections_tree.column("issues", width=100)
        
        scrollbar_sections = ttk.Scrollbar(sections_frame, orient=tk.VERTICAL, command=self.sections_tree.yview)
        self.sections_tree.configure(yscrollcommand=scrollbar_sections.set)
        
        self.sections_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_sections.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_cps_warning_tab(self):
        """CPS警告タブ"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="⚡ CPS警告")
        
        # 上部: 設定
        settings_frame = ttk.LabelFrame(tab_frame, text="CPS設定")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # CPS設定
        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(settings_inner, text="警告CPS:").pack(side=tk.LEFT, padx=5)
        self.cps_threshold_var = tk.DoubleVar(value=14.0)
        threshold_spinbox = ttk.Spinbox(settings_inner, from_=8.0, to=20.0, increment=0.5, 
                                      textvariable=self.cps_threshold_var, width=6)
        threshold_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(settings_inner, text="表示時間(秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.duration_var = tk.DoubleVar(value=3.0)
        duration_spinbox = ttk.Spinbox(settings_inner, from_=1.0, to=10.0, increment=0.5,
                                     textvariable=self.duration_var, width=6)
        duration_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(settings_inner, text="再計算", command=self.recalculate_cps).pack(side=tk.LEFT, padx=20)
        
        # 統計情報パネル
        stats_frame = ttk.LabelFrame(tab_frame, text="📊 CPS統計")
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.cps_stats_var = tk.StringVar(value="解析を実行してください")
        stats_label = ttk.Label(stats_frame, textvariable=self.cps_stats_var, font=("", 10))
        stats_label.pack(pady=5)
        
        # 中央: CPS結果リスト
        results_frame = ttk.LabelFrame(tab_frame, text="CPS分析結果")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # CPSツリービュー（改良版）
        cps_columns = ("index", "text", "cps", "duration", "status", "suggestion")
        self.cps_tree = ttk.Treeview(results_frame, columns=cps_columns, show="headings", height=18)
        
        # ヘッダー設定
        self.cps_tree.heading("index", text="#")
        self.cps_tree.heading("text", text="テキスト")
        self.cps_tree.heading("cps", text="CPS")
        self.cps_tree.heading("duration", text="時間(s)")
        self.cps_tree.heading("status", text="状態")
        self.cps_tree.heading("suggestion", text="推奨")
        
        # カラム幅調整（見やすさ重視）
        self.cps_tree.column("index", width=50, anchor="center")
        self.cps_tree.column("text", width=500)  # テキスト幅拡大
        self.cps_tree.column("cps", width=80, anchor="center")
        self.cps_tree.column("duration", width=80, anchor="center")
        self.cps_tree.column("status", width=100, anchor="center")
        self.cps_tree.column("suggestion", width=150, anchor="center")
        
        scrollbar_cps = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.cps_tree.yview)
        self.cps_tree.configure(yscrollcommand=scrollbar_cps.set)
        
        # 見やすい色分け設定
        self.cps_tree.tag_configure("danger", background="#ff6b6b", foreground="white")      # 危険（高速）
        self.cps_tree.tag_configure("warning", background="#ffd93d", foreground="black")    # 注意（やや高速）
        self.cps_tree.tag_configure("safe", background="#6bcf7f", foreground="white")       # 安全（適正）
        self.cps_tree.tag_configure("slow", background="#74c0fc", foreground="black")       # 遅い（延長推奨）
        
        self.cps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_cps.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_pronunciation_tab(self):
        """発音辞書タブ"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🗣️ 発音辞書")
        
        # 左右分割
        paned = ttk.PanedWindow(tab_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左: 辞書一覧
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="登録単語一覧", font=("", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        # 辞書ツリー
        dict_columns = ("word", "reading", "category", "confidence")
        self.dict_tree = ttk.Treeview(left_frame, columns=dict_columns, show="headings", height=25)
        
        self.dict_tree.heading("word", text="単語")
        self.dict_tree.heading("reading", text="読み")
        self.dict_tree.heading("category", text="カテゴリ")
        self.dict_tree.heading("confidence", text="確信度")
        
        self.dict_tree.column("word", width=150)
        self.dict_tree.column("reading", width=150)
        self.dict_tree.column("category", width=100)
        self.dict_tree.column("confidence", width=80)
        
        scrollbar_dict = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.dict_tree.yview)
        self.dict_tree.configure(yscrollcommand=scrollbar_dict.set)
        
        self.dict_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_dict.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右: 検出結果・編集
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="台本内検出結果", font=("", 12, "bold")).pack(anchor=tk.W, pady=5)
        
        # 検出結果リスト
        matches_frame = ttk.LabelFrame(right_frame, text="検出された専門用語")
        matches_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.matches_text = scrolledtext.ScrolledText(matches_frame, height=15, wrap=tk.WORD)
        self.matches_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 発音適用テスト
        test_frame = ttk.LabelFrame(right_frame, text="発音適用テスト")
        test_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(test_frame, text="読み適用", command=lambda: self.test_pronunciation("reading")).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(test_frame, text="SSML適用", command=lambda: self.test_pronunciation("ssml")).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.pronunciation_result = scrolledtext.ScrolledText(test_frame, height=8, wrap=tk.WORD)
        self.pronunciation_result.pack(fill=tk.X, padx=5, pady=5)
    
    def setup_api_monitoring_tab(self):
        """API監視タブ"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="📊 API監視")
        
        # 上部: 制限設定
        settings_frame = ttk.LabelFrame(tab_frame, text="制限設定")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(mode_frame, text="制限モード:").pack(side=tk.LEFT, padx=5)
        self.api_mode_var = tk.StringVar(value="DEVELOPMENT")
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.api_mode_var, 
                                values=["DEMO", "DEVELOPMENT", "TESTING", "PRODUCTION"], 
                                state="readonly", width=15)
        mode_combo.pack(side=tk.LEFT, padx=5)
        mode_combo.bind('<<ComboboxSelected>>', self.on_api_mode_change)
        
        # 使用量表示
        usage_frame = ttk.LabelFrame(tab_frame, text="API使用量")
        usage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.api_usage_text = scrolledtext.ScrolledText(usage_frame, wrap=tk.WORD)
        self.api_usage_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # アクション
        action_frame = ttk.Frame(usage_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="使用量更新", command=self.update_api_usage).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="テスト実行", command=self.test_api_limits).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="リセット", command=self.reset_api_usage).pack(side=tk.LEFT, padx=5)
    
    def setup_production_tab(self):
        """制作タブ（TTS生成・制御）"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="🎬 制作")
        
        # メインレイアウト
        main_production_frame = ttk.PanedWindow(tab_frame, orient=tk.HORIZONTAL)
        main_production_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側: TTS制御パネル
        tts_frame = ttk.LabelFrame(main_production_frame, text="🎤 TTS音声生成", padding=10)
        main_production_frame.add(tts_frame, weight=1)
        
        # TTS状態表示
        status_frame = ttk.Frame(tts_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.tts_status_var = tk.StringVar(value="準備中...")
        ttk.Label(status_frame, text="状態:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_frame, textvariable=self.tts_status_var)
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 接続テスト
        test_frame = ttk.Frame(tts_frame)
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(test_frame, text="API接続テスト", command=self.test_tts_connection).pack(side=tk.LEFT, padx=(0, 5))
        
        self.connection_status_var = tk.StringVar(value="未テスト")
        ttk.Label(test_frame, textvariable=self.connection_status_var).pack(side=tk.LEFT, padx=(10, 0))
        
        # テスト音声生成
        test_tts_frame = ttk.LabelFrame(tts_frame, text="🧪 テスト生成", padding=5)
        test_tts_frame.pack(fill=tk.X, pady=(0, 10))
        
        # テスト用テキスト
        ttk.Label(test_tts_frame, text="テスト文:").pack(anchor=tk.W)
        self.test_text_var = tk.StringVar(value="ニーチェは「神は死んだ」と宣言しました。")
        test_text_entry = ttk.Entry(test_tts_frame, textvariable=self.test_text_var, width=50)
        test_text_entry.pack(fill=tk.X, pady=(0, 5))
        
        # テスト生成設定
        test_settings_frame = ttk.Frame(test_tts_frame)
        test_settings_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 第1行：音声タイプと発音辞書
        settings_row1 = ttk.Frame(test_settings_frame)
        settings_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(settings_row1, text="音声タイプ:").pack(side=tk.LEFT)
        self.test_voice_type = tk.StringVar(value="NA")
        voice_type_combo = ttk.Combobox(settings_row1, textvariable=self.test_voice_type, 
                                       values=["NA", "DL", "FEMALE", "MALE"], width=10, state="readonly")
        voice_type_combo.pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(settings_row1, text="発音辞書:").pack(side=tk.LEFT)
        self.apply_pronunciation_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_row1, variable=self.apply_pronunciation_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # 第2行：具体的ボイス選択
        settings_row2 = ttk.Frame(test_settings_frame)
        settings_row2.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(settings_row2, text="ボイス選択:").pack(side=tk.LEFT)
        self.selected_voice_id = tk.StringVar()
        self.voice_id_combo = ttk.Combobox(settings_row2, textvariable=self.selected_voice_id, 
                                          width=50, state="readonly")
        self.voice_id_combo.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        
        # ボイスタイプ変更時のコールバック
        voice_type_combo.bind('<<ComboboxSelected>>', self.on_voice_type_change)
        
        # 生成ボタン
        ttk.Button(test_tts_frame, text="🎤 テスト生成", command=self.generate_test_tts).pack(pady=5)

        # LLM演出付与トグル
        enhance_row = ttk.Frame(test_tts_frame)
        enhance_row.pack(fill=tk.X, pady=(2, 0))
        self.tts_llm_enhance_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(enhance_row, text="LLMで演出付与（Eleven v3タグ）", \
                        variable=self.tts_llm_enhance_var).pack(side=tk.LEFT)

        # 一括生成エリア
        batch_frame = ttk.LabelFrame(tts_frame, text="📦 台本からTTS一括生成", padding=8)
        batch_frame.pack(fill=tk.X, pady=(4, 10))

        # 出力フォルダ設定
        out_row = ttk.Frame(batch_frame)
        out_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(out_row, text="出力フォルダ:").pack(side=tk.LEFT)
        default_out = str((Path.cwd() / "output" / "audio").resolve())
        self.batch_output_dir_var = tk.StringVar(value=default_out)
        ttk.Entry(out_row, textvariable=self.batch_output_dir_var, width=50).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(out_row, text="参照", command=self.choose_batch_output_dir).pack(side=tk.LEFT)

        # 実行ボタン
        ttk.Button(batch_frame, text="🎵 台本からTTS一括生成", command=self.generate_batch_tts_from_script).pack(anchor=tk.W)
        
        # ボイス設定エリア
        voice_config_frame = ttk.LabelFrame(tts_frame, text="🎵 ボイス設定", padding=5)
        voice_config_frame.pack(fill=tk.X, pady=(10, 0))
        
        # ボイスID編集
        ttk.Label(voice_config_frame, text="ボイスID直接編集:").pack(anchor=tk.W)
        
        # 各ボイスタイプの編集フィールド
        voice_types = [
            ("ナレーション (NA)", "ELEVENLABS_VOICE_ID_NARRATION"),
            ("対話 (DL)", "ELEVENLABS_VOICE_ID_DIALOGUE"), 
            ("女性声 (FEMALE)", "ELEVENLABS_VOICE_ID_FEMALE"),
            ("男性声 (MALE)", "ELEVENLABS_VOICE_ID_MALE")
        ]
        
        self.voice_id_vars = {}
        self.voice_id_entries = {}
        
        for display_name, env_key in voice_types:
            row_frame = ttk.Frame(voice_config_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(row_frame, text=f"{display_name}:", width=20).pack(side=tk.LEFT)
            
            # 現在の値を取得
            current_value = os.getenv(env_key, "")
            
            # StringVar作成
            var = tk.StringVar(value=current_value)
            self.voice_id_vars[env_key] = var
            
            # Entry作成
            entry = ttk.Entry(row_frame, textvariable=var, width=30, font=("Consolas", 9))
            entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
            self.voice_id_entries[env_key] = entry
            
            # テストボタン
            ttk.Button(row_frame, text="🔊", width=3, 
                      command=lambda key=env_key: self.test_voice_id(key)).pack(side=tk.LEFT, padx=(0, 5))
        
        # ボタン行
        voice_buttons_frame = ttk.Frame(voice_config_frame)
        voice_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(voice_buttons_frame, text="💾 .envに保存", 
                  command=self.save_voice_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(voice_buttons_frame, text="🔄 リロード", 
                  command=self.reload_voice_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(voice_buttons_frame, text="🎤 利用可能ボイス取得", 
                  command=self.fetch_available_voices).pack(side=tk.LEFT)
        
        # 文字コンテ生成エリア
        storyboard_frame = ttk.LabelFrame(tts_frame, text="🎬 文字コンテ生成", padding=5)
        storyboard_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 生成コントロール
        storyboard_control_frame = ttk.Frame(storyboard_frame)
        storyboard_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(storyboard_control_frame, text="📝 文字コンテ生成", 
                  command=self.generate_storyboard).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(storyboard_control_frame, text="💾 文字コンテ保存(JSON)", 
                  command=lambda: self._save_json_via_dialog('storyboard')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(storyboard_control_frame, text="🎵 BGM雰囲気生成", 
                  command=self.generate_music_prompts).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(storyboard_control_frame, text="💾 BGM保存(JSON)", 
                  command=lambda: self._save_json_via_dialog('music')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(storyboard_control_frame, text="🔄 リロード", 
                  command=self.reload_storyboard_data).pack(side=tk.LEFT)
        ttk.Button(storyboard_control_frame, text="📤 L→R CSV書き出し", 
                  command=self.export_l2r_csv).pack(side=tk.LEFT, padx=(6, 0))
        
        # ステータス表示
        self.storyboard_status_var = tk.StringVar(value="未生成")
        ttk.Label(storyboard_control_frame, textvariable=self.storyboard_status_var).pack(side=tk.LEFT, padx=(10, 0))
        
        # シーン表示エリア
        self.storyboard_notebook = ttk.Notebook(storyboard_frame)
        self.storyboard_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 文字コンテタブ
        self.storyboard_tab = ttk.Frame(self.storyboard_notebook)
        self.storyboard_notebook.add(self.storyboard_tab, text="🎬 シーン")
        
        # BGMタブ
        self.music_tab = ttk.Frame(self.storyboard_notebook)
        self.storyboard_notebook.add(self.music_tab, text="🎵 BGM")
        
        # 文字コンテ表示エリア
        ttk.Label(self.storyboard_tab, text="シーン一覧:").pack(anchor=tk.W, pady=(5, 0))
        self.storyboard_display = scrolledtext.ScrolledText(self.storyboard_tab, height=15, font=("Consolas", 13))
        self.storyboard_display.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # BGM表示エリア  
        ttk.Label(self.music_tab, text="BGM雰囲気一覧:").pack(anchor=tk.W, pady=(5, 0))
        self.music_display = scrolledtext.ScrolledText(self.music_tab, height=15, font=("Consolas", 13))
        self.music_display.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # 字幕タブを追加
        self.subtitles_tab = ttk.Frame(self.storyboard_notebook)
        self.storyboard_notebook.add(self.subtitles_tab, text="🈶 字幕")
        self._setup_subtitles_tab()
        
        # 右側: 進捗・ログパネル
        log_frame = ttk.LabelFrame(main_production_frame, text="📊 進捗・ログ", padding=10)
        main_production_frame.add(log_frame, weight=1)
        
        # 進捗バー
        progress_frame = ttk.Frame(log_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_frame, text="生成進捗:").pack(anchor=tk.W)
        self.tts_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.tts_progress.pack(fill=tk.X, pady=(5, 0))
        
        # ログエリア
        ttk.Label(log_frame, text="ログ:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, font=("Consolas", 13))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # TTS初期化状態を確認
        self.update_tts_status()
        
    def _setup_subtitles_tab(self):
        """字幕タブセットアップ"""
        controls = ttk.Frame(self.subtitles_tab)
        controls.pack(fill=tk.X, pady=(8, 4), padx=6)

        ttk.Button(controls, text="🈶 字幕生成", command=self.generate_subtitles).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="📁 音声フォルダ指定", command=self.choose_audio_folder).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="💾 SRT保存", command=self.save_srt_from_workspace).pack(side=tk.LEFT)

        self.audio_folder_var = tk.StringVar(value="")
        ttk.Label(controls, textvariable=self.audio_folder_var, foreground="gray").pack(side=tk.LEFT, padx=10)

        self.subtitles_display = scrolledtext.ScrolledText(self.subtitles_tab, height=20, font=("Consolas", 13))
        self.subtitles_display.pack(fill=tk.BOTH, expand=True, pady=(4, 8), padx=6)

    def choose_audio_folder(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="音声フォルダを選択 (line_001.mp3 など)")
        if path:
            self.audio_folder_var.set(path)
            self.status_var.set(f"音声フォルダ: {Path(path).name}")

    def generate_subtitles(self):
        """台本解析→字幕キュー作成（LLM/ルール）→表示更新"""
        script_content = self.script_text.get('1.0', tk.END).strip()
        if not script_content:
            messagebox.showwarning("警告", "台本を入力してから生成してください")
            return
        if not self.parsed_segments:
            self.analyze_script()
            if not self.parsed_segments:
                messagebox.showerror("エラー", "台本解析に失敗しました")
                return

        use_audio = False
        audio_path = None
        if self.audio_folder_var.get():
            ap = Path(self.audio_folder_var.get())
            if ap.exists():
                audio_path = ap
                use_audio = True

        # pydub で実長を読む（任意）
        audio_durations = {}
        if use_audio:
            try:
                from pydub import AudioSegment
                # 対応パターン: 旧(line_001.mp3) と 新(<Title>-S001.mp3)
                slug = self._get_title_slug()
                patterns = [f"{slug}-S*.mp3", f"{slug}-S*.*", "line_*.*"]
                files = []
                for pat in patterns:
                    files.extend(list(audio_path.glob(pat)))
                files = sorted(list({f for f in files}))
                for f in files:
                    try:
                        audio = AudioSegment.from_file(f)
                        sec = len(audio) / 1000.0
                        stem = f.stem
                        idx = None
                        try:
                            if '_' in stem and stem.startswith('line_'):
                                idx = int(stem.split('_')[1])
                            elif '-S' in stem:
                                # pattern: <slug>-S001
                                after_s = stem.split('-S')[-1]
                                idx = int(after_s[:3])
                        except Exception:
                            idx = None
                        if idx is not None:
                            audio_durations[idx] = sec
                    except Exception:
                        continue
            except Exception:
                audio_durations = {}
                use_audio = False

        max_line_chars = 26
        default_min = 1.8
        default_max = 6.0

        # LLM可用性チェック（クレジット用）
        llm_available = bool(os.getenv('OPENAI_API_KEY')) or bool(shutil.which('claude')) or bool(os.getenv('GEMINI_API_KEY')) or bool(os.getenv('LLM_CLI_CMD'))
        if not llm_available:
            messagebox.showerror("LLM未設定", "LLMの設定がありません。LLM設定からプロバイダ/キーを設定してください。")
            return

        def _normalize_punct(s: str) -> str:
            # 句読点を半角スペースに置き換え（連続スペースは1つに圧縮）
            try:
                s = s.replace('、', ' ').replace('。', ' ')
                s = re.sub(r"\s+", " ", s).strip()
                return s
            except Exception:
                return s

        cues = []
        current_time = 0.0
        slug = self._get_title_slug()
        for i, seg in enumerate(self.parsed_segments, 1):
            text = seg.text.strip()
            if not text:
                continue
            # 統合ルール/LLMでカード分割
            lines_cards = None
            # LLM利用設定
            use_llm_sub = getattr(self, 'llm_use_subtitles', True)
            if use_llm_sub and self.gpt_client:
                # Use GPTClient provider-agnostic splitter with cost tracking
                lines_cards = self.gpt_client.split_text_to_cards(text, max_len=max_line_chars)
                if lines_cards and getattr(self.gpt_client, 'last_cost', None):
                    c = self.gpt_client.last_cost
                    self.llm_cost_var.set(f"LLM: ¥{c['cost_jpy']} (${c['cost_usd']})")
            if lines_cards:
                # 事後バリデーション: ルール違反があればエラー（非LLMフォールバックは行わない）
                norm_cards = []
                for card in lines_cards:
                    card_lines = [ _normalize_punct(ln.strip()) for ln in card if ln and ln.strip()]
                    # 基本制約: 1–2行, 各行<=26
                    if len(card_lines) == 0 or len(card_lines) > 2 or any(len(ln) > max_line_chars for ln in card_lines):
                        messagebox.showerror(
                            "フォーマットエラー",
                            "LLMが生成した字幕カードが制約(最大2行/各26文字)を超えています。モデル/プロンプトを見直してください。"
                        )
                        return
                    # 追加制約: 1カード=最大52文字（行結合・句読点置換後）
                    joined = " ".join(card_lines)
                    if len(joined) > 52:
                        messagebox.showerror(
                            "フォーマットエラー",
                            f"字幕カードが52文字を超えています({len(joined)}文字)。モデル/プロンプトを見直してください。"
                        )
                        return
                    norm_cards.append(card_lines)
                lines_cards = norm_cards
            if not lines_cards:
                messagebox.showerror("LLMエラー", "字幕のLLM分割に失敗しました。LLM設定を確認してください。")
                return

            for j, card in enumerate(lines_cards, 1):
                card_text = '\n'.join(card)
                if use_audio and (i in audio_durations):
                    dur = max(default_min, min(default_max, audio_durations[i]))
                else:
                    char_count = self.cps_analyzer.count_characters(card_text)
                    est = max(default_min, min(default_max, char_count / 12.0))
                    dur = est

                start = current_time
                end = start + dur
                current_time = end + 0.25

                role = 'NA' if str(getattr(seg, 'speaker_type', 'NA')).endswith('NA') else 'DL'
                uid = f"{slug}-S{i:03d}C{j:02d}"
                cue = {
                    'index': len(cues) + 1,
                    'start_sec': start,
                    'end_sec': end,
                    'start': self._sec_to_srt_time(start),
                    'end': self._sec_to_srt_time(end),
                    'duration': dur,
                    'lines': card,
                    'role': role,
                    'uid': uid
                }
                cues.append(cue)

        self.subtitle_cues_data = cues
        self._update_subtitles_display()
        self.status_var.set(f"字幕生成完了: {len(cues)}キュー")

    def _update_subtitles_display(self):
        self.subtitles_display.delete('1.0', tk.END)
        if not self.subtitle_cues_data:
            self.subtitles_display.insert('1.0', "まだ字幕が生成されていません。\n\n🈶 「字幕生成」ボタンをクリックしてください。")
            return
        # SRT形式でプレビュー（ROLEコメント付き）
        srt_cues = [
            SrtCue(idx=c['index'], start=c['start_sec'], end=c['end_sec'], lines=c['lines'], role=c.get('role',''), uid=c.get('uid'))
            for c in self.subtitle_cues_data
        ]
        srt_text = build_srt(srt_cues)
        self.subtitles_display.insert('1.0', srt_text)

    def save_srt_from_workspace(self):
        if not self.subtitle_cues_data:
            messagebox.showwarning("警告", "生成済みの字幕がありません")
            return
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="SRTファイルを保存",
            defaultextension=".srt",
            filetypes=[("SRT", "*.srt"), ("All files", "*.*")]
        )
        if not file_path:
            return
        try:
            srt_cues = [SrtCue(idx=c['index'], start=c['start_sec'], end=c['end_sec'], lines=c['lines'], role=c.get('role',''), uid=c.get('uid')) for c in self.subtitle_cues_data]
            srt_text = build_srt(srt_cues)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_text)
            self.status_var.set(f"SRT保存完了: {Path(file_path).name}")
            self.log_message(f"💾 SRT保存: {file_path}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("エラー", f"SRT保存エラー:\n{e}")

    def _get_title_slug(self) -> str:
        """プロジェクト名から安全なスラッグを生成"""
        title = self.project_name_var.get() if hasattr(self, 'project_name_var') else (self.current_project.name if self.current_project else 'untitled')
        s = title.strip() if title else 'untitled'
        # 半角化は簡易に: 非英数はハイフンに
        s = ''.join(ch if ch.isalnum() else '-' for ch in s)
        s = re.sub(r'-+', '-', s).strip('-')
        return s or 'untitled'

    def _sec_to_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    # === バッチTTS生成（台本から） ===
    def choose_batch_output_dir(self):
        """一括TTSの出力フォルダ選択"""
        path = filedialog.askdirectory(title="出力フォルダを選択")
        if path:
            self.batch_output_dir_var.set(path)

    def _speaker_type_to_code(self, speaker_type) -> str:
        """ScriptParserのSpeakerTypeを 'NA'/'DL'/'QT' に正規化"""
        try:
            name = str(getattr(speaker_type, 'value', speaker_type))
            if name in ('NA', 'NARRATOR') or str(speaker_type).endswith('NARRATOR'):
                return 'NA'
            if name in ('DL', 'DIALOGUE') or str(speaker_type).endswith('DIALOGUE'):
                return 'DL'
            return 'QT'
        except Exception:
            return 'NA'

    def _voice_id_for_type(self, code: str) -> str:
        """ボイスタイプコードから音声IDを取得（ENV/設定を優先）"""
        try:
            if code in self.available_voices:
                return self._normalize_voice_id(self.available_voices[code].get('id', ''))
        except Exception:
            pass
        # フォールバック: NA
        try:
            return self._normalize_voice_id(self.available_voices.get('NA', {}).get('id', ''))
        except Exception:
            return ''

    def generate_batch_tts_from_script(self):
        """台本の各セグメントから一括でTTS音声を生成"""
        # クライアント確認
        if self.tts_client is None and self.simple_tts_client is None:
            messagebox.showerror("エラー", "TTSクライアントが初期化されていません")
            return

        # 台本確認・解析
        script_content = self.script_text.get('1.0', tk.END).strip()
        if not script_content:
            messagebox.showwarning("警告", "台本テキストを入力してください")
            return
        if not self.parsed_segments:
            self.analyze_script()
            if not self.parsed_segments:
                messagebox.showerror("エラー", "台本解析に失敗しました")
                return

        # 出力フォルダ
        out_dir = Path(self.batch_output_dir_var.get().strip() or (Path.cwd() / 'output' / 'audio'))
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("エラー", f"出力フォルダを作成できません:\n{e}")
            return

        # ファイル名スラッグ
        slug = self._get_title_slug()

        # 実行ログ
        self.log_message(f"🎵 一括TTS生成開始: セグメント {len(self.parsed_segments)} 件 → {out_dir}", "INFO")
        try:
            self.tts_progress.start()
        except Exception:
            pass
        self.tts_status_var.set("生成中...")

        def worker():
            success = 0
            failed = 0
            total = len(self.parsed_segments)
            for idx, seg in enumerate(self.parsed_segments, 1):
                text = (getattr(seg, 'text', '') or '').strip()
                if not text:
                    continue
                spk = self._speaker_type_to_code(getattr(seg, 'speaker_type', 'NA'))
                voice_id = self._voice_id_for_type(spk)
                filename = f"{slug}-S{idx:03d}.mp3"
                out_file = out_dir / filename

                # 進捗表示
                self.ui_call(self.tts_status_var.set, f"生成中 {idx}/{total} ({spk})")
                # LLM演出付与
                text_to_use = text
                if self.tts_llm_enhance_var.get() and self.gpt_client:
                    try:
                        speaker_name = getattr(seg, 'speaker_detail', '') or ("Narrator" if spk=='NA' else 'Speaker')
                        enhanced = self.gpt_client.enhance_tts_with_eleven_v3(text, spk, speaker_name)
                        if enhanced:
                            text_to_use = enhanced
                            self.log_message(f"🎭 行{idx}: LLM演出付与を適用", "SUCCESS")
                        else:
                            self.log_message(f"⚠️ 行{idx}: LLM演出付与に失敗。元テキスト使用", "WARNING")
                    except Exception as e:
                        self.log_message(f"⚠️ 行{idx}: LLM演出付与エラー: {e}", "WARNING")

                self.log_message(f"▶️ 行{idx}: {text_to_use[:30]}... | voice={spk}:{(voice_id or '')[:8]}...", "INFO")

                try:
                    if self.use_simple_client and self.simple_tts_client:
                        # 制限チェック（簡易）
                        allowed, reason = self.simple_tts_client.check_generation_limits(text)
                        if not allowed:
                            failed += 1
                            self.log_message(f"⛔ 行{idx} 制限によりスキップ: {reason}", "WARNING")
                            continue
                        res = self.simple_tts_client.generate_tts_simple(text_to_use, voice_id, str(out_file))
                        if res.success:
                            success += 1
                            self.log_message(f"✅ 行{idx} 完了: {out_file.name} ({res.duration_sec:.1f}s)", "SUCCESS")
                        else:
                            failed += 1
                            self.log_message(f"❌ 行{idx} 失敗: {res.error_message}", "ERROR")
                    else:
                        # 拡張クライアント
                        req = TTSRequest(
                            text=text_to_use,
                            voice_id=voice_id,
                            output_file=str(out_file),
                            speaker_type=spk,
                            apply_pronunciation=self.apply_pronunciation_var.get() if hasattr(self, 'apply_pronunciation_var') else True
                        )
                        def cb(msg: str):
                            self.log_message(f"📊 行{idx}: {msg}", "INFO")
                        result = self.tts_client.generate_tts(req, cb)
                        if result.success:
                            success += 1
                            self.log_message(f"✅ 行{idx} 完了: {out_file.name} ({result.duration_sec:.1f}s)", "SUCCESS")
                        else:
                            failed += 1
                            self.log_message(f"❌ 行{idx} 失敗: {result.error_message}", "ERROR")
                except Exception as e:
                    failed += 1
                    self.log_message(f"❌ 行{idx} 例外: {e}", "ERROR")

            # 完了処理
            try:
                self.ui_call(self.tts_progress.stop)
            except Exception:
                pass
            self.ui_call(self.tts_status_var.set, f"完了: 成功 {success} / 失敗 {failed}")
            # 字幕タブの音声フォルダに反映
            try:
                self.ui_call(self.audio_folder_var.set, str(out_dir))
            except Exception:
                pass
            self.ui_call(messagebox.showinfo, "一括生成 完了", f"TTS一括生成が完了しました\n成功: {success}\n失敗: {failed}\n出力: {out_dir}")

        threading.Thread(target=worker, daemon=True).start()
    
    def setup_status_bar(self):
        """ステータスバー"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="準備完了")
        ttk.Label(self.status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 右寄せ情報
        self.info_var = tk.StringVar(value="セグメント: 0 | 警告: 0 | 辞書: 0")
        self.llm_cost_var = tk.StringVar(value="LLM: -")
        ttk.Label(self.status_frame, textvariable=self.llm_cost_var, foreground="#2E7D32").pack(side=tk.RIGHT, padx=(10,0))
        ttk.Label(self.status_frame, textvariable=self.info_var).pack(side=tk.RIGHT)

    def show_llm_settings(self):
        """LLM設定ダイアログ"""
        win = tk.Toplevel(self.root)
        win.title("LLM設定")
        win.geometry("520x360")

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Provider
        ttk.Label(frm, text="プロバイダ:").grid(row=0, column=0, sticky=tk.W, pady=4)
        # Gemini固定（他の選択肢は表示しない）
        self.llm_provider_var = tk.StringVar(value='gemini')
        provider_combo = ttk.Combobox(frm, textvariable=self.llm_provider_var, state='disabled',
                                      values=['gemini'])
        provider_combo.grid(row=0, column=1, sticky=tk.W)

        # Model / CLI cmd
        ttk.Label(frm, text="モデル:").grid(row=1, column=0, sticky=tk.W, pady=4)
        # Gemini 2.5 Pro に固定（編集不可）
        self.llm_model_var = tk.StringVar(value='gemini-2.5-pro')
        model_entry = ttk.Entry(frm, textvariable=self.llm_model_var, width=32, state='disabled')
        model_entry.grid(row=1, column=1, sticky=tk.W)

        # CLIは非表示（Gemini固定）
        ttk.Label(frm, text="CLIコマンド").grid_remove()
        self.llm_cli_var = tk.StringVar(value='')
        ttk.Entry(frm, textvariable=self.llm_cli_var, width=40).grid_remove()

        # API keys (optional)
        # OpenAIキーは非表示（Gemini固定）
        self.openai_key_var = tk.StringVar(value='')
        # placeholders removed

        ttk.Label(frm, text="GEMINI_API_KEY:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.gemini_key_var = tk.StringVar(value=os.getenv('GEMINI_API_KEY', ''))
        ttk.Entry(frm, textvariable=self.gemini_key_var, width=40, show='*').grid(row=2, column=1, sticky=tk.W)

        # Subtitles toggle
        self.llm_use_sub_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="字幕生成でLLMを使用", variable=self.llm_use_sub_var).grid(row=3, column=1, sticky=tk.W, pady=6)

        # Buttons
        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="保存", command=lambda: self._apply_llm_settings(win)).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="閉じる", command=win.destroy).pack(side=tk.LEFT, padx=6)

    def _apply_llm_settings(self, win):
        """LLM設定適用"""
        provider = 'gemini'
        model = 'gemini-2.5-pro'
        cli_cmd = self.llm_cli_var.get().strip()
        openai_key = self.openai_key_var.get().strip()
        gemini_key = self.gemini_key_var.get().strip()
        use_sub = self.llm_use_sub_var.get()

        # Save in instance
        self.llm_provider = provider
        self.llm_model = model
        self.llm_use_subtitles = use_sub

        # Env + client wiring
        # CLIは使わない
        os.environ.pop('LLM_CLI_CMD', None)
        if self.gpt_client:
            self.gpt_client.cli_cmd = ''
        # OpenAIキーは無視
        os.environ.pop('OPENAI_API_KEY', None)
        if gemini_key:
            os.environ['GEMINI_API_KEY'] = gemini_key

        if self.gpt_client:
            # 固定モデルを適用
            os.environ['GEMINI_MODEL'] = 'gemini-2.5-pro'
            self.gpt_client.gemini_model = 'gemini-2.5-pro'
            # Provider preference
            self.gpt_client.preferred_provider = provider

        # Status note
        self.api_status_var.set(f"LLM: gemini {model or ''}")
        self.log_message(f"LLM設定を適用: provider={provider}, model={model or '-'}", "SUCCESS")
        win.destroy()
    
    # === イベントハンドラー ===
    
    def new_project(self):
        """新規プロジェクト作成"""
        self.current_project = Project(name="新規プロジェクト")
        self.project_name_var.set("新規プロジェクト")
        self.update_all_displays()
    
    def load_script_file(self):
        """台本ファイル読み込み"""
        file_path = filedialog.askopenfilename(
            title="台本ファイルを選択",
            filetypes=[("テキスト", "*.txt"), ("マークダウン", "*.md"), ("全て", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.script_text.delete('1.0', tk.END)
                self.script_text.insert('1.0', content)
                
                # 自動解析
                self.analyze_script()
                
                # プロジェクト名を更新
                file_name = Path(file_path).stem
                self.project_name_var.set(file_name)
                self.status_var.set(f"台本読み込み完了: {file_name}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"ファイル読み込みエラー:\n{e}")

    def load_demo_script(self):
        """デモ台本をエディタに読み込み（解析も自動実行）"""
        demo_text = (
            "[00:00-00:30] アバン\n"
            "深夜0時。オフィスビルの窓に、まだポツポツと明かりが灯っています。\n"
            "その一室で、あなたはビジネス系SNSの画面を見つめている。元同期の転職報告。「新しいチャレンジ」「素晴らしい環境」—— そんな言葉が並ぶ投稿に、「いいね！」を押しながら、胸の奥がざわつく。\n"
            "また一人、脱出に成功した。\n"
            "ようこそ、オリオンの会議室へ。ここは、時代を超えた知恵が交差する場所。今夜は「転職の約束」について、3000年の時を超えた対話を始めましょう。\n\n"
            "[00:30-01:00] 星座の提示\n"
            "【画面：夜空に星が現れ、線で結ばれていくアニメーション】\n"
            "今夜結ぶのは、こんな星座。\n"
            "エジプトから脱出した古代イスラエルの民、「神は死んだ」と宣言したニーチェ、組織論を研究する現代の学者たち、そして迷宮に閉じ込められたカフカの主人公——\n"
            "時代も場所も違う星々が、「脱出」と「約束」という糸で結ばれて、ひとつの物語を紡ぎ始めます。\n\n"
            "[01:00-02:00] 現代の悩み導入\n"
            "（ここに現代の悩み導入セクションの本文を追記）\n"
        )
        try:
            self.script_text.delete('1.0', tk.END)
            self.script_text.insert('1.0', demo_text)
            self.project_name_var.set("オリオンEP1_デモ")
            self.status_var.set("デモ台本を読み込みました。解析中...")
            self.analyze_script()
            self.status_var.set("デモ台本の解析が完了しました")
        except Exception as e:
            messagebox.showerror("エラー", f"デモ台本の読み込みに失敗しました:\n{e}")
    
    def save_project(self):
        """プロジェクト保存"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトが選択されていません")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="プロジェクト保存",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("全て", "*.*")]
        )
        
        if file_path:
            try:
                # プロジェクトデータを保存
                project_data = {
                    'name': self.current_project.name,
                    'script_content': self.script_text.get('1.0', tk.END),
                    'analysis_results': {
                        'segments_count': len(self.parsed_segments),
                        'cps_warnings': len(self.cps_warnings),
                        'pronunciation_matches': len(self.pronunciation_matches)
                    },
                    # 追加: 文字コンテ / BGM / 字幕
                    'storyboard': self.storyboard_data,
                    'music_prompts': self.music_prompts_data,
                    'subtitles': self.subtitle_cues_data
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                
                self.status_var.set(f"プロジェクト保存完了: {Path(file_path).name}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"保存エラー:\n{e}")
    
    def on_script_change(self, event):
        """台本変更時の処理"""
        # リアルタイム解析は重いので、タイマーで遅延実行
        if hasattr(self, '_analysis_timer'):
            self.root.after_cancel(self._analysis_timer)
        
        self._analysis_timer = self.root.after(1000, self.analyze_script)  # 1秒後に実行
    
    def analyze_script(self):
        """台本解析実行"""
        try:
            script_content = self.script_text.get('1.0', tk.END).strip()
            if not script_content:
                return
            
            # 台本解析
            self.parsed_segments = self.script_parser.parse_script(script_content)
            
            # 統計更新
            self.update_script_statistics()
            self.update_sections_display()
            
            # CPS分析も同時実行
            self.check_cps()
            
            # 発音チェックも同時実行
            self.check_pronunciation()
            
            self.status_var.set(f"解析完了: {len(self.parsed_segments)}セグメント")
            
        except Exception as e:
            self.status_var.set(f"解析エラー: {str(e)}")
    
    def update_script_statistics(self):
        """台本統計更新"""
        if not self.parsed_segments:
            self.stats_text.delete('1.0', tk.END)
            return
        
        # セクション統計
        sections = {}
        speaker_counts = {speaker.value: 0 for speaker in SpeakerType}
        
        for segment in self.parsed_segments:
            # セクション集計
            section_key = f"{segment.timecode_start}-{segment.timecode_end} {segment.section_title}"
            if section_key not in sections:
                sections[section_key] = []
            sections[section_key].append(segment)
            
            # 話者集計
            speaker_counts[segment.speaker_type.value] += 1
        
        # 統計テキスト作成
        stats_text = f"📊 統計サマリー\n"
        stats_text += f"総セグメント: {len(self.parsed_segments)}\n"
        stats_text += f"セクション数: {len(sections)}\n"
        stats_text += f"話者構成: NA={speaker_counts['NA']}, DL={speaker_counts['DL']}, QT={speaker_counts['QT']}\n"
        
        # 文字数統計
        total_chars = sum(self.cps_analyzer.count_characters(seg.text) for seg in self.parsed_segments)
        avg_chars = total_chars / len(self.parsed_segments) if self.parsed_segments else 0
        stats_text += f"総文字数: {total_chars}, 平均: {avg_chars:.1f}文字/セグメント"
        
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats_text)
    
    def update_sections_display(self):
        """セクション表示更新"""
        # ツリーをクリア
        for item in self.sections_tree.get_children():
            self.sections_tree.delete(item)
        
        if not self.parsed_segments:
            return
        
        # セクション別グループ化
        sections = {}
        for segment in self.parsed_segments:
            section_key = f"{segment.timecode_start}-{segment.timecode_end} {segment.section_title}"
            if section_key not in sections:
                sections[section_key] = []
            sections[section_key].append(segment)
        
        # ツリーに追加
        for section_key, section_segments in sections.items():
            # 話者構成
            speaker_counts = {}
            issues = []
            
            for seg in section_segments:
                speaker_type = seg.speaker_type.value
                speaker_counts[speaker_type] = speaker_counts.get(speaker_type, 0) + 1
                
                # 問題検出
                char_count = self.cps_analyzer.count_characters(seg.text)
                if char_count > 60:
                    issues.append("長文")
            
            speaker_text = ", ".join([f"{k}:{v}" for k, v in speaker_counts.items()])
            issues_text = ", ".join(issues) if issues else "なし"
            
            self.sections_tree.insert('', tk.END, values=(
                section_key,
                len(section_segments),
                speaker_text,
                issues_text
            ))
    
    def check_cps(self):
        """CPS分析実行"""
        # 台本が入力されているかチェック
        script_content = self.script_text.get('1.0', tk.END).strip()
        if not script_content:
            self.cps_stats_var.set("❌ 台本を入力してから分析を実行してください")
            return
        
        # 台本解析が実行されているかチェック
        if not self.parsed_segments:
            self.analyze_script()  # 自動的に台本解析を実行
            if not self.parsed_segments:
                self.cps_stats_var.set("❌ 台本解析に失敗しました")
                return
        
        # 実行中表示
        self.cps_stats_var.set("🔄 CPS分析実行中...")
        
        # ツリーをクリア
        for item in self.cps_tree.get_children():
            self.cps_tree.delete(item)
        
        self.cps_warnings = []
        duration = self.duration_var.get()
        
        try:
            for i, segment in enumerate(self.parsed_segments, 1):
                # CPS分析
                cue = self.cps_analyzer.analyze_subtitle(segment.text, duration)
                
                # 改良されたステータス判定と色分け
                if cue.cps >= 15.0:
                    status = "🚨 危険"
                    tag = "danger"
                    suggestion = f"即座に分割({int(cue.cps/8)+1}分割)"
                    self.cps_warnings.append((i, segment.text, cue.cps))
                elif cue.cps >= 10.0:
                    status = "⚡ 注意"
                    tag = "warning" 
                    suggestion = f"分割推奨({int(cue.cps/10)+1}分割)"
                    self.cps_warnings.append((i, segment.text, cue.cps))
                elif cue.cps >= 3.0:
                    status = "✅ 適正"
                    tag = "safe"
                    suggestion = ""
                else:
                    status = "⏳ 遅い"
                    tag = "slow"
                    suggestion = "表示延長"
                
                # テキスト表示改良（長文に対応）
                display_text = segment.text
                if len(display_text) > 60:
                    display_text = display_text[:57] + "..."
                
                # ツリーに挿入
                item_id = self.cps_tree.insert('', tk.END, values=(
                    f"#{i}",
                    display_text,
                    f"{cue.cps:.1f}",
                    f"{duration:.1f}",
                    status,
                    suggestion
                ))
                
                # 見やすい色分け適用
                self.cps_tree.item(item_id, tags=(tag,))
            
            # 統計情報計算（効率化版）
            total_segments = len(self.parsed_segments)
            danger_count = 0
            warning_count = 0
            safe_count = 0
            slow_count = 0
            
            # 既に計算したCPS値を活用
            for child in self.cps_tree.get_children():
                cps_value = float(self.cps_tree.item(child)['values'][2])
                if cps_value >= 15.0:
                    danger_count += 1
                elif cps_value >= 10.0:
                    warning_count += 1
                elif cps_value >= 3.0:
                    safe_count += 1
                else:
                    slow_count += 1
            
            # 統計情報をGUIに表示
            stats_text = f"総計: {total_segments}セグメント | 🚨危険: {danger_count}件 | ⚡注意: {warning_count}件 | ✅適正: {safe_count}件 | ⏳遅い: {slow_count}件"
            self.cps_stats_var.set(stats_text)
            
            print(f"📊 CPS分析完了: 危険{danger_count}件、注意{warning_count}件、適正{safe_count}件、遅い{slow_count}件")
            
        except Exception as e:
            error_msg = f"CPS分析エラー: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.cps_stats_var.set("❌ CPS分析でエラーが発生しました")
            print(f"CPS分析エラー詳細: {e}")
        
        self.update_status_info()
    
    def recalculate_cps(self):
        """CPS再計算"""
        try:
            # 新しい閾値で解析器を更新
            self.cps_analyzer.warning_threshold = self.cps_threshold_var.get()
            self.check_cps()
            self.log_message(f"CPS再計算完了（閾値: {self.cps_threshold_var.get()}）", "SUCCESS")
        except Exception as e:
            error_msg = f"CPS再計算エラー: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.cps_stats_var.set("❌ CPS計算でエラーが発生しました")
    
    def check_pronunciation(self):
        """発音チェック実行"""
        # 辞書ツリーを更新
        for item in self.dict_tree.get_children():
            self.dict_tree.delete(item)
        
        for word, entry in self.pronunciation_dict.entries.items():
            self.dict_tree.insert('', tk.END, values=(
                word,
                entry.reading,
                entry.category,
                f"{entry.confidence:.1f}"
            ))
        
        # 台本内マッチング
        script_content = self.script_text.get('1.0', tk.END).strip()
        if script_content:
            matches = self.pronunciation_dict.find_matches_in_text(script_content)
            self.pronunciation_matches = matches
            
            # マッチ結果表示
            self.matches_text.delete('1.0', tk.END)
            matches_text = f"🎯 検出された専門用語: {len(matches)}語\n\n"
            
            for word, entry in matches:
                matches_text += f"📖 {word} → {entry.reading} ({entry.category})\n"
                if entry.notes:
                    matches_text += f"   備考: {entry.notes}\n"
                matches_text += "\n"
            
            self.matches_text.insert('1.0', matches_text)
        
        self.update_status_info()
    
    def test_pronunciation(self, format_type: str):
        """発音適用テスト"""
        script_content = self.script_text.get('1.0', tk.END).strip()
        if not script_content:
            return
        
        # テスト用に最初の数行を使用
        lines = script_content.split('\n')[:5]
        test_text = '\n'.join([line for line in lines if line.strip()])
        
        # 発音適用
        result_text = self.pronunciation_dict.apply_pronunciation_to_text(test_text, format_type)
        
        # 結果表示
        self.pronunciation_result.delete('1.0', tk.END)
        result_display = f"🔊 発音適用結果 ({format_type})\n\n"
        result_display += f"元テキスト:\n{test_text}\n\n"
        result_display += f"適用後:\n{result_text}"
        
        self.pronunciation_result.insert('1.0', result_display)
    
    def on_api_mode_change(self, event):
        """API制限モード変更"""
        mode_name = self.api_mode_var.get()
        mode = LimitMode[mode_name]
        
        self.api_limiter = create_test_limiter(mode)
        self.api_status_var.set(f"{mode_name}制限")
        self.update_api_usage()
    
    def show_api_usage(self):
        """API使用量表示"""
        report = self.api_limiter.get_usage_report()
        messagebox.showinfo("API使用量", report)
    
    def update_api_usage(self):
        """API使用量表示更新"""
        report = self.api_limiter.get_usage_report()
        self.api_usage_text.delete('1.0', tk.END)
        self.api_usage_text.insert('1.0', report)
    
    def test_api_limits(self):
        """API制限テスト"""
        test_text = "ニーチェの哲学について考えてみましょう。"
        
        allowed, reason = self.api_limiter.check_limits(APIType.ELEVENLABS_TTS, len(test_text))
        
        if allowed:
            self.api_limiter.record_usage(APIType.ELEVENLABS_TTS, len(test_text))
            messagebox.showinfo("テスト結果", f"✅ テスト成功\n理由: {reason}")
        else:
            messagebox.showwarning("テスト結果", f"❌ 制限により拒否\n理由: {reason}")
        
        self.update_api_usage()
    
    def reset_api_usage(self):
        """API使用量リセット"""
        if messagebox.askyesno("確認", "API使用量をリセットしますか？"):
            # 新しいリミッターを作成（使用量クリア）
            mode = LimitMode[self.api_mode_var.get()]
            self.api_limiter = create_test_limiter(mode)
            
            # ファイルも削除
            usage_file = f"api_usage_{mode.value}.json"
            if Path(usage_file).exists():
                os.remove(usage_file)
            
            self.update_api_usage()
            self.status_var.set("API使用量をリセットしました")
    
    def update_status_info(self):
        """ステータス情報更新"""
        segments_count = len(self.parsed_segments)
        warnings_count = len(self.cps_warnings) 
        matches_count = len(self.pronunciation_matches)
        dict_count = len(self.pronunciation_dict.entries)
        
        self.info_var.set(f"セグメント: {segments_count} | CPS警告: {warnings_count} | 辞書マッチ: {matches_count} | 登録語: {dict_count}")
    
    # === 環境変数・ボイス管理 ===
    
    def load_environment_variables(self):
        """環境変数読み込み（.envファイル対応）"""
        self.env_file_path = None
        
        # Try multiple potential .env file locations
        env_paths = [
            Path(".env"),  # Current directory
            Path("..") / "minivt_pipeline" / ".env",  # Parent/minivt_pipeline
            Path(__file__).parent.parent / "minivt_pipeline" / ".env"  # Relative to script
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                self.env_file_path = env_path
                print(f"🔍 .envファイル発見: {env_path}")
                
                if DOTENV_AVAILABLE:
                    load_dotenv(env_path)
                    print(f"✅ python-dotenv使用: {env_path}")
                else:
                    # Manual .env parsing fallback
                    self._manual_load_env(env_path)
                    print(f"✅ 手動.env読み込み: {env_path}")
                break
        else:
            print("❌ .envファイルが見つかりません")
            
    def _manual_load_env(self, env_path: Path):
        """手動.env読み込み（python-dotenvなしの場合）"""
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value
                        print(f"  設定: {key} = {value[:10]}...")
        except Exception as e:
            print(f"❌ 手動.env読み込みエラー: {e}")
    
    def load_voice_configuration(self):
        """ボイス設定読み込み"""
        # Default voice configuration
        self.available_voices = {
            "NA": {
                "name": "ナレーション",
                "id": os.getenv("ELEVENLABS_VOICE_ID_NARRATION", os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")).strip(),
                "description": "ナレーション用音声"
            },
            "DL": {
                "name": "対話",
                "id": os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")).strip(),
                "description": "対話・セリフ用音声"
            },
            "FEMALE": {
                "name": "女性声",
                "id": os.getenv("ELEVENLABS_VOICE_ID_FEMALE", os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", "WQz3clzUdMqvBf0jswZQ")).strip(),
                "description": "女性キャラクター用"
            },
            "MALE": {
                "name": "男性声",
                "id": os.getenv("ELEVENLABS_VOICE_ID_MALE", os.getenv("ELEVENLABS_VOICE_ID_NARRATION", "3JDquces8E8bkmvbh6Bc")).strip(),
                "description": "男性キャラクター用"
            }
        }

    def _normalize_voice_id(self, value: str) -> str:
        """Extract a valid ElevenLabs voice ID from user/display strings.
        Accepts plain IDs or display like 'ナレーション (21m00Tcm...) - 説明'.
        """
        try:
            s = (value or "").strip()
            # If pure token-like string without spaces, use as-is
            if s and ' ' not in s and '(' not in s and ')' not in s:
                return s
            import re
            m = re.search(r"([A-Za-z0-9]{12,})", s)
            return m.group(1) if m else s
        except Exception:
            return value
    
    def on_voice_type_change(self, event):
        """ボイスタイプ変更時のコールバック"""
        voice_type = self.test_voice_type.get()
        
        if voice_type in self.available_voices:
            voice_info = self.available_voices[voice_type]
            
            # ボイスIDコンボボックス更新
            voice_display = f"{voice_info['name']} ({voice_info['id'][:8]}...) - {voice_info['description']}"
            self.voice_id_combo['values'] = [voice_display]
            self.voice_id_combo.set(voice_display)
            self.selected_voice_id.set(voice_info['id'])
    
    # === TTS制御機能 ===
    
    def update_tts_status(self):
        """TTS状態更新"""
        if self.tts_client is None and self.simple_tts_client is None:
            if self.tts_init_error:
                self.tts_status_var.set(f"❌ 初期化エラー: {self.tts_init_error[:30]}...")
            else:
                self.tts_status_var.set("❌ TTS初期化失敗")
            return
        
        # 環境変数チェック
        api_key = os.getenv("ELEVENLABS_API_KEY")
        print(f"🔍 環境変数チェック: ELEVENLABS_API_KEY = {api_key[:8] + '...' if api_key else 'None'}")
        
        if api_key:
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            client_type = "シンプル" if self.use_simple_client else "拡張"
            env_source = f"(.env: {self.env_file_path.name})" if self.env_file_path else "(システム環境変数)"
            self.tts_status_var.set(f"✅ API設定済み ({client_type}) {env_source}")
        else:
            self.tts_status_var.set("❌ ELEVENLABS_API_KEY 未設定")
    
    def log_message(self, message: str, level: str = "INFO"):
        """ログメッセージ追加"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        level_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "📝")
        log_entry = f"[{timestamp}] {level_emoji} {message}\n"
        # Console output for external logs (e.g., launcher/terminal)
        try:
            print(log_entry.strip())
        except Exception:
            pass
        
        def _append():
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
        
        import threading
        if threading.current_thread() is not threading.main_thread():
            self.ui_call(_append)
        else:
            _append()
    
    def test_tts_connection(self):
        """TTS接続テスト"""
        # どちらのクライアントも利用できない場合
        if self.tts_client is None and self.simple_tts_client is None:
            self.connection_status_var.set("❌ TTS未初期化")
            error_details = f"クライアント未初期化: {self.tts_init_error}" if self.tts_init_error else "クライアント未初期化"
            self.log_message(f"TTS接続テスト失敗: {error_details}", "ERROR")
            return
        
        client_type = "シンプル" if self.use_simple_client else "拡張"
        self.log_message(f"TTS接続テスト開始... ({client_type}クライアント)", "INFO")
        
        def test_thread():
            try:
                # 利用可能なクライアントで接続テスト
                if self.use_simple_client and self.simple_tts_client:
                    connected, message = self.simple_tts_client.test_connection()
                else:
                    connected, message = self.tts_client.test_connection()
                
                if connected:
                    self.connection_status_var.set(f"✅ 接続成功 ({client_type})")
                    self.log_message(f"TTS接続テスト成功: {message}", "SUCCESS")
                else:
                    self.connection_status_var.set("❌ 接続失敗")
                    self.log_message(f"TTS接続テスト失敗: {message}", "ERROR")
                    
            except Exception as e:
                self.connection_status_var.set("❌ エラー")
                self.log_message(f"TTS接続テストエラー: {str(e)}", "ERROR")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def generate_test_tts(self):
        """テストTTS生成"""
        if self.tts_client is None and self.simple_tts_client is None:
            messagebox.showerror("エラー", "TTSクライアントが初期化されていません")
            return
        
        text = self.test_text_var.get().strip()
        if not text:
            messagebox.showwarning("警告", "テストテキストを入力してください")
            return
        
        # 制限チェック（利用可能なクライアントで実行）
        if self.use_simple_client and self.simple_tts_client:
            allowed, reason = self.simple_tts_client.check_generation_limits(text)
        else:
            allowed, reason = self.tts_client.check_generation_limits(text)
            
        if not allowed:
            messagebox.showwarning("制限エラー", f"API制限により生成できません:\n{reason}")
            self.log_message(f"TTS生成拒否: {reason}", "WARNING")
            return
        
        # LLM演出付与（任意）
        original_text = text
        if self.tts_llm_enhance_var.get() and self.gpt_client:
            try:
                role_code = (self.test_voice_type.get() or 'NA')
                enhanced = self.gpt_client.enhance_tts_with_eleven_v3(text, role_code)
                if enhanced:
                    text = enhanced
                    self.log_message("🎭 LLM演出付与を適用（Eleven v3タグ）", "SUCCESS")
                else:
                    self.log_message("⚠️ LLM演出付与に失敗。元テキストを使用", "WARNING")
            except Exception as e:
                self.log_message(f"⚠️ LLM演出付与エラー: {e}", "WARNING")
        self.log_message(f"TTS生成開始: 「{(text or original_text)[:30]}...」", "INFO")
        self.tts_progress.start()
        
        def generation_thread():
            try:
                # ボイス選択: 型優先（NA/DLなど）、手入力優先（有効ID検出時）
                voice_type = self.test_voice_type.get()
                default_voice_id = self._normalize_voice_id(self.available_voices.get(voice_type, {}).get('id', ''))
                user_text = (self.selected_voice_id.get() or '').strip()
                user_candidate = self._normalize_voice_id(user_text)
                # 十分な長さのトークンなら採用、そうでなければデフォルト
                selected_voice_id = user_candidate if (user_candidate and len(user_candidate) >= 12 and (' ' not in user_candidate)) else default_voice_id
                
                # TTS生成実行（クライアントタイプに応じて）
                if self.use_simple_client and self.simple_tts_client:
                    # シンプルクライアントでの生成
                    self.log_message("📊 シンプルクライアントでTTS生成中...", "INFO")
                    result = self.simple_tts_client.generate_tts_simple(text, selected_voice_id, "temp_test_tts.mp3")
                else:
                    # 拡張クライアントでの生成
                    request = TTSRequest(
                        text=text,
                        voice_id=selected_voice_id,
                        output_file="temp_test_tts.mp3",
                        speaker_type=self.test_voice_type.get(),
                        apply_pronunciation=self.apply_pronunciation_var.get()
                    )
                    
                    def progress_callback(message: str):
                        self.log_message(f"📊 {message}", "INFO")
                    
                    result = self.tts_client.generate_tts(request, progress_callback)
                
                self.ui_call(self.tts_progress.stop)
                
                if result.success:
                    self.log_message(f"TTS生成完了: {result.output_file}", "SUCCESS")
                    self.log_message(f"音声時間: {result.duration_sec:.1f}秒", "INFO")
                    self.log_message(f"推定コスト: ${result.cost_usd:.4f}", "INFO")
                    
                    # 使用統計表示（利用可能なクライアントで）
                    if self.use_simple_client and self.simple_tts_client:
                        stats = self.simple_tts_client.get_usage_report()
                    else:
                        stats = self.tts_client.get_usage_report()
                    self.log_message("TTS使用統計更新完了", "INFO")
                    
                    self.ui_call(messagebox.showinfo, "生成完了",
                                  f"TTS生成が完了しました\n\n"
                                  f"出力ファイル: {result.output_file}\n"
                                  f"音声時間: {result.duration_sec:.1f}秒\n"
                                  f"推定コスト: ${result.cost_usd:.4f}")
                    
                else:
                    self.log_message(f"TTS生成失敗: {result.error_message}", "ERROR")
                    self.ui_call(messagebox.showerror, "生成失敗", f"TTS生成に失敗しました:\n{result.error_message}")
                    
            except Exception as e:
                self.ui_call(self.tts_progress.stop)
                error_msg = f"TTS生成エラー: {str(e)}"
                self.log_message(error_msg, "ERROR")
                self.ui_call(messagebox.showerror, "エラー", error_msg)
        
        threading.Thread(target=generation_thread, daemon=True).start()
    
    # === ボイス設定管理機能 ===
    
    def test_voice_id(self, env_key: str):
        """個別ボイスIDテスト"""
        voice_id = self._normalize_voice_id(self.voice_id_vars[env_key].get())
        if not voice_id:
            messagebox.showwarning("警告", "ボイスIDを入力してください")
            return
        
        self.log_message(f"🔊 ボイステスト開始: {env_key} = {voice_id[:8]}...", "INFO")
        
        def test_thread():
            try:
                if self.use_simple_client and self.simple_tts_client:
                    # シンプルクライアントでテスト
                    test_text = "音声テスト"
                    result = self.simple_tts_client.generate_tts_simple(
                        test_text, voice_id, f"voice_test_{env_key}.mp3"
                    )
                    
                    if result.success:
                        self.log_message(f"✅ ボイステスト成功: {env_key}", "SUCCESS")
                        self.ui_call(messagebox.showinfo, "テスト成功",
                                     f"ボイスID {voice_id[:8]}... のテストが成功しました\n"
                                     f"出力: {result.output_file}")
                    else:
                        self.log_message(f"❌ ボイステスト失敗: {result.error_message}", "ERROR")
                        self.ui_call(messagebox.showerror, "テスト失敗",
                                     f"ボイスID {voice_id[:8]}... のテストに失敗しました\n"
                                     f"エラー: {result.error_message}")
                else:
                    self.log_message("❌ TTSクライアントが利用できません", "ERROR")
                    self.ui_call(messagebox.showerror, "エラー", "TTSクライアントが初期化されていません")
                    
            except Exception as e:
                error_msg = f"ボイステストエラー: {str(e)}"
                self.log_message(error_msg, "ERROR")
                self.ui_call(messagebox.showerror, "エラー", error_msg)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def save_voice_config(self):
        """ボイス設定を.envファイルに保存"""
        if not self.env_file_path:
            messagebox.showerror("エラー", ".envファイルが見つかりません")
            return
        
        try:
            # 現在の.envファイルを読み込み
            env_lines = []
            env_dict = {}
            
            if self.env_file_path.exists():
                with open(self.env_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and '=' in stripped:
                            key, value = stripped.split('=', 1)
                            env_dict[key.strip()] = value.strip()
                        env_lines.append(line.rstrip())
            
            # 新しいボイス設定で更新
            for env_key, var in self.voice_id_vars.items():
                new_value = var.get().strip()
                env_dict[env_key] = new_value
                # 環境変数も更新
                os.environ[env_key] = new_value
            
            # .envファイルを再構築
            new_lines = []
            processed_keys = set()
            
            for line in env_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    key, old_value = stripped.split('=', 1)
                    key = key.strip()
                    
                    if key in env_dict:
                        # 更新された値を使用
                        new_lines.append(f"{key}={env_dict[key]}")
                        processed_keys.add(key)
                    else:
                        # 元の行をそのまま保持
                        new_lines.append(line)
                else:
                    # コメントや空行はそのまま保持
                    new_lines.append(line)
            
            # まだ処理されていないボイス設定を追加
            for env_key in self.voice_id_vars.keys():
                if env_key not in processed_keys:
                    new_lines.append(f"{env_key}={env_dict[env_key]}")
            
            # ファイルに書き込み
            with open(self.env_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines) + '\n')
            
            # ボイス設定をリロード
            self.load_voice_configuration()
            
            self.log_message("💾 ボイス設定を保存しました", "SUCCESS")
            messagebox.showinfo("保存完了", f"ボイス設定を.envファイルに保存しました\n{self.env_file_path}")
            
        except Exception as e:
            error_msg = f"保存エラー: {str(e)}"
            self.log_message(error_msg, "ERROR")
            messagebox.showerror("保存失敗", error_msg)
    
    def reload_voice_config(self):
        """環境変数からボイス設定をリロード"""
        try:
            # 環境変数を再読み込み
            self.load_environment_variables()
            
            # UI上の値を更新
            for env_key, var in self.voice_id_vars.items():
                current_value = os.getenv(env_key, "")
                var.set(current_value)
            
            # ボイス設定も更新
            self.load_voice_configuration()
            
            self.log_message("🔄 ボイス設定をリロードしました", "SUCCESS")
            messagebox.showinfo("リロード完了", "環境変数からボイス設定をリロードしました")
            
        except Exception as e:
            error_msg = f"リロードエラー: {str(e)}"
            self.log_message(error_msg, "ERROR")
            messagebox.showerror("リロード失敗", error_msg)
    
    def fetch_available_voices(self):
        """ElevenLabsから利用可能ボイス一覧を取得"""
        self.log_message("🎤 利用可能ボイス取得開始...", "INFO")
        
        def fetch_thread():
            try:
                if not self.simple_tts_client:
                    self.log_message("❌ TTSクライアントが利用できません", "ERROR")
                    self.ui_call(messagebox.showerror, "エラー", "TTSクライアントが初期化されていません")
                    return
                
                # 簡易的な接続テストとして、ボイス一覧取得を試行
                api_key = os.getenv("ELEVENLABS_API_KEY")
                if not api_key:
                    self.log_message("❌ ELEVENLABS_API_KEYが設定されていません", "ERROR")
                    self.ui_call(messagebox.showerror, "エラー", "APIキーが設定されていません")
                    return
                
                # ダミーの応答（実際のAPIがエラーの場合の代替）
                voices_info = """
🎤 一般的なElevenLabsボイスID:

📝 プリセットボイス（推奨）:
• Rachel: 21m00Tcm4TlvDq8ikWAM
• Drew: 29vD33N1CtxCmqQRPOHJ  
• Clyde: 2EiwWnXFnvU5JabPnv8n
• Dave: CYw3kZ02Hs0563khs1Fj
• Fin: D38z5RcWu1voky8WS1ja
• Sarah: EXAVITQu4vr4xnSDxMaL
• Antoni: ErXwobaYiN019PkySvjV
• Arnold: VR6AewLTigWG4xSOukaG
• Adam: pNInz6obpgDQGcFmaJgB
• Sam: yoZ06aMxZJJ28mfd3POQ

💡 使用方法:
1. 上記のIDをコピー
2. 対応する入力フィールドに貼り付け
3. 🔊ボタンでテスト
4. 💾ボタンで保存
"""
                
                # 情報表示ウィンドウ（UIスレッドで作成）
                def _show_info():
                    info_window = tk.Toplevel(self.root)
                    info_window.title("🎤 利用可能ボイス情報")
                    info_window.geometry("600x500")
                    text_widget = scrolledtext.ScrolledText(info_window, font=("Consolas", 10))
                    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    text_widget.insert('1.0', voices_info)
                    text_widget.config(state='disabled')
                    ttk.Button(info_window, text="閉じる", command=info_window.destroy).pack(pady=5)
                    self.log_message("✅ ボイス情報を表示しました", "SUCCESS")
                self.ui_call(_show_info)
                
            except Exception as e:
                error_msg = f"ボイス取得エラー: {str(e)}"
                self.log_message(error_msg, "ERROR")
                self.ui_call(messagebox.showerror, "取得失敗", error_msg)
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def update_all_displays(self):
        """全表示更新"""
        self.update_api_usage()
        self.update_status_info()
        self.update_tts_status()
        
        # デフォルトボイス選択を初期化（安全チェック）
        if hasattr(self, 'test_voice_type') and hasattr(self, 'voice_id_combo'):
            try:
                self.on_voice_type_change(None)
            except Exception as e:
                print(f"⚠️ ボイス初期化スキップ: {e}")
    
    def generate_storyboard(self):
        """文字コンテ生成"""
        if not self.gpt_client:
            messagebox.showerror("エラー", f"GPTクライアントが利用できません\n{self.gpt_init_error or '初期化されていません'}")
            return
        
        # 台本テキスト取得
        script_text = self.script_text.get('1.0', tk.END).strip()
        if not script_text:
            messagebox.showwarning("警告", "台本テキストを入力してください")
            return
        
        self.storyboard_status_var.set("生成中...")
        # LLM必須（非LLMロールバック廃止）
        llm_available = bool(os.getenv('OPENAI_API_KEY')) or bool(shutil.which('claude')) or bool(os.getenv('GEMINI_API_KEY')) or bool(os.getenv('LLM_CLI_CMD'))
        if not llm_available:
            messagebox.showerror("LLM未設定", "LLMの設定がありません。LLM設定からプロバイダ/キーを設定してください。")
            return
        self.log_message("🎬 文字コンテ生成開始...", "INFO")
        
        def generate_thread():
            try:
                # 台本解析結果も渡す
                result = self.gpt_client.generate_storyboard(script_text, self.parsed_segments)
                
                if result and "storyboard" in result:
                    self.storyboard_data = result["storyboard"]
                    self.ui_call(self.update_storyboard_display)
                    self.ui_call(self.storyboard_status_var.set, f"生成完了 ({len(self.storyboard_data)}シーン)")
                    self.log_message(f"✅ 文字コンテ生成完了: {len(self.storyboard_data)}シーン", "SUCCESS")
                    # LLMコスト表示更新
                    try:
                        if hasattr(self.gpt_client, 'last_cost') and self.gpt_client.last_cost:
                            c = self.gpt_client.last_cost
                            self.ui_call(self.llm_cost_var.set, f"LLM: ¥{c['cost_jpy']} (${c['cost_usd']})")
                    except Exception:
                        pass
                else:
                    self.ui_call(self.storyboard_status_var.set, "生成失敗")
                    self.log_message("❌ 文字コンテ生成失敗: 無効なレスポンス", "ERROR")
                    self.ui_call(messagebox.showerror, "生成失敗", "文字コンテの生成に失敗しました")
                    
            except Exception as e:
                error_msg = f"文字コンテ生成エラー: {str(e)}"
                self.ui_call(self.storyboard_status_var.set, "エラー")
                self.log_message(error_msg, "ERROR")
                self.ui_call(messagebox.showerror, "生成エラー", error_msg)
        
        threading.Thread(target=generate_thread, daemon=True).start()

    def export_storyboard_json(self, file_path: Path):
        """文字コンテJSON保存"""
        try:
            import json
            # UID付与して保存
            slug = self._get_title_slug()
            scenes = []
            for i, scene in enumerate(self.storyboard_data, 1):
                scene_id = scene.get('scene_id', f'SC-{i:03d}')
                s = dict(scene)
                s['uid'] = f"{slug}-{scene_id}"
                scenes.append(s)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({"storyboard": scenes}, f, ensure_ascii=False, indent=2)
            self.log_message(f"💾 文字コンテJSON保存: {file_path}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("エラー", f"文字コンテ保存エラー:\n{e}")
    
    def generate_music_prompts(self):
        """BGM雰囲気生成"""
        if not self.gpt_client:
            messagebox.showerror("エラー", f"GPTクライアントが利用できません\n{self.gpt_init_error or '初期化されていません'}")
            return
        
        # 台本テキスト取得
        script_text = self.script_text.get('1.0', tk.END).strip()
        if not script_text:
            messagebox.showwarning("警告", "台本テキストを入力してください")
            return
        
        self.storyboard_status_var.set("BGM生成中...")
        llm_available = bool(os.getenv('OPENAI_API_KEY')) or bool(shutil.which('claude')) or bool(os.getenv('GEMINI_API_KEY')) or bool(os.getenv('LLM_CLI_CMD'))
        if not llm_available:
            messagebox.showerror("LLM未設定", "LLMの設定がありません。LLM設定からプロバイダ/キーを設定してください。")
            return
        self.log_message("🎵 BGM雰囲気生成開始...", "INFO")
        
        def generate_thread():
            try:
                # 台本解析結果も渡す
                result = self.gpt_client.generate_music_prompts(script_text, self.parsed_segments)
                
                if result and "music_prompts" in result:
                    self.music_prompts_data = result["music_prompts"]
                    self.ui_call(self.update_music_display)
                    self.ui_call(self.storyboard_status_var.set, f"BGM生成完了 ({len(self.music_prompts_data)}キュー)")
                    self.log_message(f"✅ BGM雰囲気生成完了: {len(self.music_prompts_data)}キュー", "SUCCESS")
                    try:
                        if hasattr(self.gpt_client, 'last_cost') and self.gpt_client.last_cost:
                            c = self.gpt_client.last_cost
                            self.ui_call(self.llm_cost_var.set, f"LLM: ¥{c['cost_jpy']} (${c['cost_usd']})")
                    except Exception:
                        pass
                else:
                    self.ui_call(self.storyboard_status_var.set, "BGM生成失敗")
                    self.log_message("❌ BGM雰囲気生成失敗: 無効なレスポンス", "ERROR")
                    self.ui_call(messagebox.showerror, "生成失敗", "BGM雰囲気の生成に失敗しました")
                    
            except Exception as e:
                error_msg = f"BGM雰囲気生成エラー: {str(e)}"
                self.ui_call(self.storyboard_status_var.set, "エラー")
                self.log_message(error_msg, "ERROR")
                self.ui_call(messagebox.showerror, "生成エラー", error_msg)
        
        threading.Thread(target=generate_thread, daemon=True).start()

    def export_music_prompts_json(self, file_path: Path):
        """BGM雰囲気JSON保存"""
        try:
            import json
            slug = self._get_title_slug()
            items = []
            for i, music in enumerate(self.music_prompts_data, 1):
                cue_id = music.get('cue_id', f'M-{i:03d}')
                m = dict(music)
                m['uid'] = f"{slug}-{cue_id}"
                items.append(m)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({"music_prompts": items}, f, ensure_ascii=False, indent=2)
            self.log_message(f"💾 BGM雰囲気JSON保存: {file_path}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("エラー", f"BGM雰囲気保存エラー:\n{e}")
    
    def reload_storyboard_data(self):
        """文字コンテ・BGMデータをリロード"""
        self.update_storyboard_display()
        self.update_music_display()
        self.log_message("🔄 文字コンテ・BGMデータをリロードしました", "SUCCESS")

    def export_l2r_csv(self):
        """左→右（列=字幕カード SxxxCyy）形式のCSVを書き出し（1セル=1テロップ<=52文字）"""
        if not self.parsed_segments:
            messagebox.showwarning("警告", "台本解析結果がありません")
            return
        from tkinter import filedialog
        default_name = f"{self._get_title_slug()}_l2r.csv"
        file_path = filedialog.asksaveasfilename(
            title="L→R CSVを書き出し",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        # すべての字幕キューをタイムライン順に整列
        cues_all: List[Dict] = list(self.subtitle_cues_data or [])
        if not cues_all:
            messagebox.showwarning("警告", "字幕が生成されていません。先に『字幕生成』を実行してください。")
            return
        cues_all.sort(key=lambda c: c.get('start_sec', 0.0))

        # 列ヘッダーは SxxxCyy（UID）
        cols = []
        # マッピング: 列 → セグメント番号
        col_seg_index: List[int] = []
        uid_re = re.compile(r"-S(\d{3})C(\d{2})$")
        for cue in cues_all:
            uid = cue.get('uid') or ''
            cols.append(uid or '')
            m = uid_re.search(uid)
            seg_idx = int(m.group(1)) if m else 0
            col_seg_index.append(seg_idx)

        # ユーティリティ: セグメント→各種情報
        def _seg_outline(seg_idx: int) -> str:
            if seg_idx and self.storyboard_data and seg_idx - 1 < len(self.storyboard_data):
                return self.storyboard_data[seg_idx - 1].get('outline') or ''
            return ''

        def _seg_reader(seg_idx: int) -> str:
            if not seg_idx or seg_idx - 1 >= len(self.parsed_segments):
                return ''
            seg = self.parsed_segments[seg_idx - 1]
            st = getattr(seg, 'speaker_type', None)
            code = str(getattr(st, 'value', 'NA'))
            if code == 'NA':
                return 'ナレーター'
            detail = getattr(seg, 'speaker_detail', '')
            return detail or '話者'

        def _seg_bgm(seg_idx: int) -> str:
            if seg_idx and self.music_prompts_data and seg_idx - 1 < len(self.music_prompts_data):
                m = self.music_prompts_data[seg_idx - 1]
                mood = m.get('mood') or ''
                tags = m.get('tags') or []
                if isinstance(tags, list):
                    tags = ','.join(tags[:4])
                return f"{mood} {tags}".strip()
            return ''

        def _seg_narration(seg_idx: int) -> str:
            if not seg_idx or seg_idx - 1 >= len(self.parsed_segments):
                return ''
            return getattr(self.parsed_segments[seg_idx - 1], 'text', '')

        # 句読点→半角スペース
        def _norm_lines(lines: List[str]) -> str:
            s = ' '.join([ln.strip() for ln in lines if ln and ln.strip()])
            s = s.replace('、', ' ').replace('。', ' ')
            s = re.sub(r"\s+", " ", s).strip()
            # 52文字超はエラー（設計上ここまで来ない想定だが二重に守る）
            if len(s) > 52:
                raise ValueError(f"字幕カードが52文字を超過: {len(s)}文字")
            return s

        # 行ごとのデータ
        rows = []
        rows.append(["SEG"] + cols)
        rows.append(["V5 TC IN"] + [cue.get('start', '') for cue in cues_all])
        rows.append(["V4 TC OUT"] + [cue.get('end', '') for cue in cues_all])
        rows.append(["V3 注釈"] + ['' for _ in cues_all])
        # 1セル=1テロップ（52文字以内）
        try:
            rows.append(["V2 字幕"] + [_norm_lines(cue.get('lines', [])) for cue in cues_all])
        except Exception as e:
            messagebox.showerror("エラー", f"字幕の文字数制約に違反しています:\n{e}")
            return
        rows.append(["V1 映像"] + [_seg_outline(seg_idx) for seg_idx in col_seg_index])
        rows.append(["A1 ナレ"] + [_seg_narration(seg_idx) for seg_idx in col_seg_index])
        rows.append(["A2 読み手"] + [_seg_reader(seg_idx) for seg_idx in col_seg_index])
        rows.append(["A3 SE"] + ['' for _ in cues_all])
        rows.append(["A4 BGM"] + [_seg_bgm(seg_idx) for seg_idx in col_seg_index])

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            self.log_message(f"📤 L→R CSVを書き出しました: {file_path}", "SUCCESS")
            messagebox.showinfo("完了", f"CSVを書き出しました\n{file_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"CSV書き出しに失敗しました:\n{e}")

    def _save_json_via_dialog(self, kind: str):
        """文字コンテ/BGMをJSON保存（ボタン用）"""
        from tkinter import filedialog
        if kind == 'storyboard' and not self.storyboard_data:
            messagebox.showwarning("警告", "保存する文字コンテがありません")
            return
        if kind == 'music' and not self.music_prompts_data:
            messagebox.showwarning("警告", "保存するBGM雰囲気がありません")
            return
        default_name = 'storyboard.json' if kind == 'storyboard' else 'music_prompts.json'
        file_path = filedialog.asksaveasfilename(
            title="JSONファイルを保存",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        if kind == 'storyboard':
            self.export_storyboard_json(Path(file_path))
        else:
            self.export_music_prompts_json(Path(file_path))
    
    def update_storyboard_display(self):
        """文字コンテ表示更新"""
        self.storyboard_display.delete('1.0', tk.END)
        
        if not self.storyboard_data:
            self.storyboard_display.insert('1.0', "まだ文字コンテが生成されていません。\n\n📝 「文字コンテ生成」ボタンをクリックして台本から自動生成してください。")
            return
        
        slug = self._get_title_slug()
        display_text = "🎬 文字コンテ一覧\n" + "="*50 + "\n\n"
        
        for i, scene in enumerate(self.storyboard_data, 1):
            scene_id = scene.get("scene_id", f"SC-{i:03d}")
            outline = scene.get("outline", "概要なし")
            shotlist = scene.get("shotlist", [])
            keywords = scene.get("stock_keywords", [])
            
            uid = f"{slug}-{scene_id}"
            display_text += f"📋 {uid}: {outline}\n"
            display_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # ショット情報
            if shotlist:
                display_text += "🎯 ショット:\n"
                for shot in shotlist:
                    shot_type = shot.get("shot", "不明")
                    shot_desc = shot.get("desc", "説明なし")
                    display_text += f"   [{shot_type}] {shot_desc}\n"
            
            # 検索キーワード
            if keywords:
                display_text += "\n🔍 素材キーワード:\n"
                for keyword in keywords:
                    display_text += f"   • {keyword}\n"
                
                # 検索リンク生成
                display_text += "\n🌐 検索リンク:\n"
                keyword_query = "+".join(keywords[:3])  # 最初の3つのキーワード
                display_text += f"   Shutterstock: https://www.shutterstock.com/search/{keyword_query}\n"
                display_text += f"   Adobe Stock: https://stock.adobe.com/search?k={keyword_query}\n"
                display_text += f"   Getty Images: https://www.gettyimages.com/search/2/image?phrase={keyword_query}\n"
            
            display_text += "\n" + "="*50 + "\n\n"
        
        # コピー用キーワード一覧
        all_keywords = []
        for scene in self.storyboard_data:
            all_keywords.extend(scene.get("stock_keywords", []))
        
        if all_keywords:
            display_text += "📋 全キーワード一覧（コピー用）:\n"
            display_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            display_text += ", ".join(set(all_keywords))  # 重複除去
        
        self.storyboard_display.insert('1.0', display_text)
    
    def update_music_display(self):
        """BGM表示更新"""
        self.music_display.delete('1.0', tk.END)
        
        if not self.music_prompts_data:
            self.music_display.insert('1.0', "まだBGM雰囲気が生成されていません。\n\n🎵 「BGM雰囲気生成」ボタンをクリックして台本から自動生成してください。")
            return
        
        slug = self._get_title_slug()
        display_text = "🎵 BGM雰囲気一覧\n" + "="*50 + "\n\n"
        
        for i, music in enumerate(self.music_prompts_data, 1):
            cue_id = music.get("cue_id", f"M-{i:03d}")
            mood = music.get("mood", "雰囲気不明")
            bpm = music.get("bpm", "不明")
            style = music.get("style", "スタイル不明")
            suno_prompt = music.get("suno_prompt", "")
            keywords = music.get("stock_keywords", [])
            
            uid = f"{slug}-{cue_id}"
            display_text += f"🎶 {uid}: {mood}\n"
            display_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            display_text += f"📊 BPM: {bpm}\n"
            display_text += f"🎼 スタイル: {style}\n"
            
            if suno_prompt:
                display_text += f"\n🤖 Suno AIプロンプト:\n   {suno_prompt}\n"
            
            if keywords:
                display_text += "\n🔍 検索キーワード:\n"
                for keyword in keywords:
                    display_text += f"   • {keyword}\n"
                
                # 音楽検索リンク
                display_text += "\n🌐 音楽検索リンク:\n"
                keyword_query = "+".join(keywords[:3])
                display_text += f"   AudioJungle: https://audiojungle.net/search/{keyword_query}\n"
                display_text += f"   Pond5: https://www.pond5.com/royalty-free-music/1/{keyword_query}\n"
                display_text += f"   Artlist: https://artlist.io/royalty-free-music/search/{keyword_query}\n"
            
            display_text += "\n" + "="*50 + "\n\n"
        
        self.music_display.insert('1.0', display_text)
    
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    app = EnhancedIntegratedWorkspace()
    app.run()

if __name__ == "__main__":
    # Top-level crash guard with logging
    try:
        main()
    except Exception as e:
        import traceback
        from pathlib import Path as _Path
        log_dir = _Path("output/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        tb_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        (log_dir / "gui_crash.log").write_text(tb_text, encoding="utf-8")
        print(tb_text)
        # Avoid hard crash without context; exit non-zero to signal error to launcher
        raise
