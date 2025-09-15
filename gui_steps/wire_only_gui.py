#!/usr/bin/env python3
"""
Text Adjust Wireframe GUI (UI only, no backend logic)

縦リストでオリジナル/最終文/文字コンテ/テロップ/BGMを編集できる
ワイヤーフレーム。保存や生成などはモック（未実装）です。
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText


class TextAdjustWireframeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧠 Text Adjust Wireframe (UI Only)")
        self.root.geometry("1400x900")

        # Apply safe theme BEFORE creating widgets
        self._init_theme_and_colors()

        self._build_toolbar()
        self._build_main()
        self._populate_sample_rows()

        # Force an initial draw
        self.root.update_idletasks()

    # === UI builders ===
    def _build_toolbar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, padx=10, pady=(10, 0))

        project = ttk.LabelFrame(bar, text="プロジェクト")
        project.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(project, text="新規", command=self._not_implemented).pack(side=tk.LEFT, padx=4)
        ttk.Button(project, text="開く", command=self._not_implemented).pack(side=tk.LEFT, padx=4)
        ttk.Button(project, text="保存", command=self._not_implemented).pack(side=tk.LEFT, padx=4)

        llm = ttk.LabelFrame(bar, text="LLM")
        llm.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(llm, text="モデル:").pack(side=tk.LEFT, padx=(6, 2))
        self.var_model = tk.StringVar(value="gpt-4o")
        ttk.Combobox(llm, textvariable=self.var_model, values=["gpt-4o", "gpt-4o-mini", "claude-3.7"], state="readonly", width=12).pack(side=tk.LEFT)
        ttk.Label(llm, text="温度:").pack(side=tk.LEFT, padx=(10, 2))
        self.var_temp = tk.DoubleVar(value=0.7)
        ttk.Spinbox(llm, from_=0.0, to=2.0, increment=0.1, textvariable=self.var_temp, width=5).pack(side=tk.LEFT)
        ttk.Button(llm, text="プリセット", command=self._not_implemented).pack(side=tk.LEFT, padx=6)

        export = ttk.LabelFrame(bar, text="エクスポート")
        export.pack(side=tk.RIGHT)
        ttk.Button(export, text="CSV（縦）", command=self._not_implemented).pack(side=tk.LEFT, padx=6)

    def _build_main(self):
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left: vertical list
        left = ttk.LabelFrame(main, text="行リスト（縦）")
        main.add(left, weight=2)

        cols = ("line", "role", "character", "original", "final", "story", "telop", "bgm")
        self.tree = ttk.Treeview(left, columns=cols, show="headings")
        headers = [
            ("line", "#", 50),
            ("role", "種類", 60),
            ("character", "キャラ", 120),
            ("original", "オリジナル", 260),
            ("final", "最終文", 260),
            ("story", "文字コンテ", 160),
            ("telop", "テロップ", 160),
            ("bgm", "BGM", 100),
        ]
        for key, label, width in headers:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor=tk.W)
        sbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=10)
        sbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_row)

        # Right: detail + candidates
        right = ttk.PanedWindow(main, orient=tk.VERTICAL)
        main.add(right, weight=3)

        detail = ttk.LabelFrame(right, text="詳細エディタ")
        right.add(detail, weight=4)

        ttk.Label(detail, text="オリジナル（読取専用）").pack(anchor=tk.W, padx=10)
        self.txt_original = ScrolledText(detail, height=5, wrap=tk.WORD, state="disabled")
        self.txt_original.pack(fill=tk.X, padx=10, pady=(0, 10))

        nb = ttk.Notebook(detail)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        f1 = ttk.Frame(nb); nb.add(f1, text="ナレーション原稿")
        self.txt_final = ScrolledText(f1, height=8, wrap=tk.WORD); self.txt_final.pack(fill=tk.BOTH, expand=True)

        f2 = ttk.Frame(nb); nb.add(f2, text="文字コンテ")
        self.txt_story = ScrolledText(f2, height=6, wrap=tk.WORD); self.txt_story.pack(fill=tk.BOTH, expand=True)

        f3 = ttk.Frame(nb); nb.add(f3, text="注釈テロップ")
        self.txt_telop = ScrolledText(f3, height=4, wrap=tk.WORD); self.txt_telop.pack(fill=tk.BOTH, expand=True)

        meta = ttk.Frame(detail); meta.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(meta, text="BGMタグ:").pack(side=tk.LEFT)
        self.var_bgm = tk.StringVar()
        ttk.Entry(meta, textvariable=self.var_bgm).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Label(meta, text="話速:").pack(side=tk.LEFT, padx=(10, 2))
        self.var_rate = tk.DoubleVar(value=1.0)
        ttk.Spinbox(meta, from_=0.5, to=2.0, increment=0.05, textvariable=self.var_rate, width=6).pack(side=tk.LEFT)
        self.var_locked = tk.BooleanVar(value=False)
        ttk.Checkbutton(meta, text="ロック", variable=self.var_locked).pack(side=tk.LEFT, padx=10)

        notes_frame = ttk.Frame(detail); notes_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 8))
        ttk.Label(notes_frame, text="メモ:").pack(anchor=tk.W)
        self.txt_notes = ScrolledText(notes_frame, height=3, wrap=tk.WORD)
        self.txt_notes.pack(fill=tk.BOTH, expand=True)

        actions = ttk.Frame(detail); actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(actions, text="保存（UIのみ）", command=self._save_current_to_row).pack(side=tk.LEFT)

        # Candidates (mock)
        candidates = ttk.LabelFrame(right, text="LLM候補（モック）")
        right.add(candidates, weight=2)

        cand_toolbar = ttk.Frame(candidates); cand_toolbar.pack(fill=tk.X, padx=10, pady=(10, 0))
        ttk.Button(cand_toolbar, text="再生成", command=self._not_implemented).pack(side=tk.LEFT)
        ttk.Button(cand_toolbar, text="採用", command=self._adopt_selected_candidate).pack(side=tk.LEFT, padx=5)
        ttk.Button(cand_toolbar, text="差分", command=self._not_implemented).pack(side=tk.LEFT)

        body = ttk.Frame(candidates); body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.list_candidates = tk.Listbox(body, activestyle="dotbox")
        self.list_candidates.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2 = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.list_candidates.yview)
        self.list_candidates.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

    def _init_theme_and_colors(self):
        style = ttk.Style()
        # Prefer clam (image-free, robust) then classic
        try:
            theme = None
            if "clam" in style.theme_names():
                theme = "clam"
            elif "classic" in style.theme_names():
                theme = "classic"
            elif "alt" in style.theme_names():
                theme = "alt"
            elif "default" in style.theme_names():
                theme = "default"
            if theme:
                style.theme_use(theme)
        except Exception:
            pass

        # Base colors to avoid black window
        try:
            self.root.configure(bg="white")
        except Exception:
            pass
        # ttk default background/foregrounds
        try:
            style.configure(".", background="white", foreground="black")
            style.configure("TFrame", background="white")
            style.configure("TLabelframe", background="white")
            style.configure("TLabelframe.Label", background="white", foreground="black")
            style.configure("TNotebook", background="white")
            style.configure("TNotebook.Tab", background="white")
            style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
            style.map("Treeview", background=[("selected", "#cce5ff")])
            style.configure("TButton", background="#f5f5f5")
        except Exception:
            pass

    # === data ===
    def _populate_sample_rows(self):
        samples = [
            (1, "NA", "-", "転職した同期の投稿を見て 焦りを感じたことはありませんか", "", "", "", "calm_a"),
            (2, "NA", "-", "転職は脱出なのか それとも逃避なのか", "", "", "", "calm_b"),
            (3, "DL", "同僚A", "うちの会社 もう限界かもね", "", "", "", "minor"),
            (4, "NA", "-", "金曜日の飲み会 愚痴と不満のオンパレード", "", "", "", "no_bgm"),
        ]
        for row in samples:
            self.tree.insert("", tk.END, values=row)
        # Preload candidates (mock)
        self._set_mock_candidates()

    def _set_mock_candidates(self):
        self.list_candidates.delete(0, tk.END)
        for i in range(1, 6):
            self.list_candidates.insert(tk.END, f"候補{i}: 読みやすく整えた例文（モック）")

    # === events ===
    def _on_select_row(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        # original
        self.txt_original.configure(state="normal")
        self.txt_original.delete("1.0", tk.END)
        self.txt_original.insert("1.0", vals[3])
        self.txt_original.configure(state="disabled")
        # fill editable fields from row
        self.txt_final.delete("1.0", tk.END)
        self.txt_final.insert("1.0", vals[4])
        self.txt_story.delete("1.0", tk.END)
        self.txt_story.insert("1.0", vals[5])
        self.txt_telop.delete("1.0", tk.END)
        self.txt_telop.insert("1.0", vals[6])
        self.var_bgm.set(vals[7])
        self.txt_notes.delete("1.0", tk.END)
        # mock flags
        self.var_locked.set(False)
        self.var_rate.set(1.0)

    def _save_current_to_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("情報", "行を選択してください")
            return
        item = sel[0]
        vals = list(self.tree.item(item)["values"])
        vals[4] = self.txt_final.get("1.0", tk.END).strip()
        vals[5] = self.txt_story.get("1.0", tk.END).strip()
        vals[6] = self.txt_telop.get("1.0", tk.END).strip()
        vals[7] = self.var_bgm.get().strip()
        self.tree.item(item, values=vals)
        messagebox.showinfo("保存", "UI上で保存しました（モック）")

    def _adopt_selected_candidate(self):
        sel_c = self.list_candidates.curselection()
        if not sel_c:
            messagebox.showinfo("情報", "候補を選択してください")
            return
        text = self.list_candidates.get(sel_c[0])
        # mock adopt → put into final
        self.txt_final.delete("1.0", tk.END)
        self.txt_final.insert("1.0", text)

    def _not_implemented(self):
        messagebox.showinfo("未実装", "この機能はワイヤーフレームのため未実装です")

    # === lifecycle ===
    def run(self):
        # Theme and colors already set in __init__
        self.root.mainloop()


def main():
    # silence macOS system Tk deprecation noise
    os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
    app = TextAdjustWireframeApp()
    app.run()


if __name__ == "__main__":
    main()
