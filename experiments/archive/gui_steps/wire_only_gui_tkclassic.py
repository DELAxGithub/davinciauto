#!/usr/bin/env python3
"""
Plain Tk Wireframe (no ttk) for macOS dark/black window issues.

できるだけ classic Tk ウィジェットのみで構成したワイヤー。
列テーブルの代わりに簡易リスト表示にしています。
"""

import os
import tkinter as tk
from tkinter import messagebox


def trunc(s, n):
    s = s or ""
    return (s[:n] + "...") if len(s) > n else s


class ClassicWireApp:
    def __init__(self):
        # macOS: silence deprecated Tk warning
        os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

        self.root = tk.Tk(className="ClassicTkWire")
        self.root.title("🧠 Text Adjust Wireframe - Classic Tk")
        self.root.geometry("1400x900")
        self.root.configure(bg="#ffffff")

        # Toolbar
        bar = tk.Frame(self.root, bg="#ffffff")
        bar.pack(fill=tk.X, padx=10, pady=(10, 0))

        def group(label):
            f = tk.LabelFrame(bar, text=label, bg="#ffffff", fg="#000000")
            f.configure(highlightbackground="#cccccc")
            f.pack(side=tk.LEFT, padx=(0, 10))
            return f

        proj = group("プロジェクト")
        tk.Button(proj, text="新規", command=self._ni).pack(side=tk.LEFT, padx=4)
        tk.Button(proj, text="開く", command=self._ni).pack(side=tk.LEFT, padx=4)
        tk.Button(proj, text="保存", command=self._ni).pack(side=tk.LEFT, padx=4)

        llm = group("LLM")
        tk.Label(llm, text="モデル:", bg="#ffffff").pack(side=tk.LEFT, padx=(6, 2))
        self.model_var = tk.StringVar(value="gpt-4o")
        tk.Entry(llm, textvariable=self.model_var, width=12).pack(side=tk.LEFT)
        tk.Label(llm, text="温度:", bg="#ffffff").pack(side=tk.LEFT, padx=(10, 2))
        self.temp_var = tk.DoubleVar(value=0.7)
        tk.Spinbox(llm, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5).pack(side=tk.LEFT)

        exp = group("エクスポート")
        tk.Button(exp, text="CSV（縦）", command=self._ni).pack(side=tk.LEFT, padx=6)

        # Main split
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#e0e0e0", sashwidth=6)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left list (simple Listbox with composite text)
        left_frame = tk.LabelFrame(main, text="行リスト（縦）", bg="#ffffff")
        left_container = tk.Frame(left_frame, bg="#ffffff")
        left_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.listbox = tk.Listbox(left_container, activestyle="dotbox")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_left = tk.Scrollbar(left_container, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb_left.set)
        sb_left.pack(side=tk.RIGHT, fill=tk.Y)

        main.add(left_frame)

        # Right split (detail + candidates)
        right = tk.PanedWindow(main, orient=tk.VERTICAL, bg="#e0e0e0", sashwidth=6)
        main.add(right)

        detail = tk.LabelFrame(right, text="詳細エディタ", bg="#ffffff")
        right.add(detail)

        tk.Label(detail, text="オリジナル（読取専用）", bg="#ffffff").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.txt_original = tk.Text(detail, height=5, wrap=tk.WORD, bg="#ffffff")
        self.txt_original.configure(state=tk.DISABLED)
        self.txt_original.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Tabs substitute: stacked areas with labels
        self.txt_final = self._add_text_block(detail, "ナレーション原稿", 8)
        self.txt_story = self._add_text_block(detail, "文字コンテ", 6)
        self.txt_telop = self._add_text_block(detail, "注釈テロップ", 4)

        meta = tk.Frame(detail, bg="#ffffff"); meta.pack(fill=tk.X, padx=10, pady=(0, 8))
        tk.Label(meta, text="BGMタグ:", bg="#ffffff").pack(side=tk.LEFT)
        self.var_bgm = tk.StringVar(); tk.Entry(meta, textvariable=self.var_bgm).pack(side=tk.LEFT, padx=6)
        tk.Label(meta, text="話速:", bg="#ffffff").pack(side=tk.LEFT, padx=(10, 2))
        self.var_rate = tk.DoubleVar(value=1.0); tk.Spinbox(meta, from_=0.5, to=2.0, increment=0.05, textvariable=self.var_rate, width=6).pack(side=tk.LEFT)
        self.var_locked = tk.BooleanVar(value=False); tk.Checkbutton(meta, text="ロック", variable=self.var_locked, bg="#ffffff").pack(side=tk.LEFT, padx=10)

        notes = tk.Frame(detail, bg="#ffffff"); notes.pack(fill=tk.BOTH, padx=10, pady=(0, 8))
        tk.Label(notes, text="メモ:", bg="#ffffff").pack(anchor=tk.W)
        self.txt_notes = tk.Text(notes, height=3, wrap=tk.WORD, bg="#ffffff"); self.txt_notes.pack(fill=tk.BOTH, expand=True)

        actions = tk.Frame(detail, bg="#ffffff"); actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(actions, text="保存（UIのみ）", command=self._save_current_to_row).pack(side=tk.LEFT)

        # Candidates (simple Listbox)
        cand = tk.LabelFrame(right, text="LLM候補（モック）", bg="#ffffff")
        right.add(cand)
        toolbar = tk.Frame(cand, bg="#ffffff"); toolbar.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Button(toolbar, text="再生成", command=self._ni).pack(side=tk.LEFT)
        tk.Button(toolbar, text="採用", command=self._adopt).pack(side=tk.LEFT, padx=6)
        tk.Button(toolbar, text="差分", command=self._ni).pack(side=tk.LEFT)

        body = tk.Frame(cand, bg="#ffffff"); body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.candidates = tk.Listbox(body, activestyle="dotbox")
        self.candidates.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2 = tk.Scrollbar(body, orient=tk.VERTICAL, command=self.candidates.yview)
        self.candidates.configure(yscrollcommand=sb2.set)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

        # events
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # data
        self._load_samples()
        self._load_mock_candidates()

    def _add_text_block(self, parent, title, height):
        wrapper = tk.Frame(parent, bg="#ffffff"); wrapper.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        tk.Label(wrapper, text=title, bg="#ffffff").pack(anchor=tk.W)
        txt = tk.Text(wrapper, height=height, wrap=tk.WORD, bg="#ffffff")
        txt.pack(fill=tk.BOTH, expand=True)
        return txt

    def _load_samples(self):
        self.rows = [
            {"line":1, "role":"NA", "character":"-", "original":"転職した同期の投稿を見て 焦りを感じたことはありませんか", "final":"", "story":"", "telop":"", "bgm":"calm_a"},
            {"line":2, "role":"NA", "character":"-", "original":"転職は脱出なのか それとも逃避なのか", "final":"", "story":"", "telop":"", "bgm":"calm_b"},
            {"line":3, "role":"DL", "character":"同僚A", "original":"うちの会社 もう限界かもね", "final":"", "story":"", "telop":"", "bgm":"minor"},
            {"line":4, "role":"NA", "character":"-", "original":"金曜日の飲み会 愚痴と不満のオンパレード", "final":"", "story":"", "telop":"", "bgm":"no_bgm"},
        ]
        self.listbox.delete(0, tk.END)
        for r in self.rows:
            text = f"#{r['line']:>3} [{r['role']}] {trunc(r['character'],8):<8} | {trunc(r['original'],50)}"
            self.listbox.insert(tk.END, text)

    def _load_mock_candidates(self):
        self.candidates.delete(0, tk.END)
        for i in range(1, 6):
            self.candidates.insert(tk.END, f"候補{i}: 読みやすく整えた例文（モック）")

    # events/handlers
    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        row = self.rows[idx]
        # fill
        self.txt_original.configure(state=tk.NORMAL)
        self.txt_original.delete("1.0", tk.END)
        self.txt_original.insert("1.0", row["original"]) 
        self.txt_original.configure(state=tk.DISABLED)

        self.txt_final.delete("1.0", tk.END)
        self.txt_final.insert("1.0", row.get("final", ""))
        self.txt_story.delete("1.0", tk.END)
        self.txt_story.insert("1.0", row.get("story", ""))
        self.txt_telop.delete("1.0", tk.END)
        self.txt_telop.insert("1.0", row.get("telop", ""))
        self.var_bgm.set(row.get("bgm", ""))
        self.var_rate.set(1.0)
        self.var_locked.set(False)

    def _save_current_to_row(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("情報", "行を選択してください")
            return
        idx = sel[0]
        row = self.rows[idx]
        row["final"] = self.txt_final.get("1.0", tk.END).strip()
        row["story"] = self.txt_story.get("1.0", tk.END).strip()
        row["telop"] = self.txt_telop.get("1.0", tk.END).strip()
        row["bgm"] = self.var_bgm.get().strip()
        messagebox.showinfo("保存", f"行 {row['line']} をUI内で保存（モック）")

    def _adopt(self):
        sel = self.candidates.curselection()
        if not sel:
            messagebox.showinfo("情報", "候補を選択してください"); return
        text = self.candidates.get(sel[0])
        self.txt_final.delete("1.0", tk.END)
        self.txt_final.insert("1.0", text)

    def _ni(self):
        messagebox.showinfo("未実装", "ワイヤーフレームです")

    def run(self):
        self.root.mainloop()


def main():
    app = ClassicWireApp()
    app.run()


if __name__ == "__main__":
    main()

