#!/usr/bin/env python3
"""
Usage audit: report likely-used vs likely-unused files.

Heuristics:
- Build Python import graph for packages: backend, gui_steps, minivt_pipeline/src
- Seed entrypoints: backend.main, backend.eleven_server, gui_steps.launch_gui,
  gui_steps.run_all_steps, minivt_pipeline.src.pipeline
- Walk reachable imports to get used .py files
- Mark everything else as unused (report-only)
- Also list static/html assets under backend/static as used

Run:
  python scripts/usage_audit.py --format markdown > usage_report.md
"""
from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
from typing import Dict, Set, Tuple, List


ROOT = Path(__file__).resolve().parents[1]

PKG_ROOTS = [
    (ROOT / "backend", "backend"),
    (ROOT / "gui_steps", "gui_steps"),
    (ROOT / "minivt_pipeline" / "src", "minivt_pipeline.src"),
]

SEEDS = {
    "backend.main",
    "backend.eleven_server",
    "gui_steps.launch_gui",
    "gui_steps.run_all_steps",
    "minivt_pipeline.src.pipeline",
}


def discover_modules() -> Tuple[Dict[str, Path], Dict[Path, str]]:
    mod_to_path: Dict[str, Path] = {}
    path_to_mod: Dict[Path, str] = {}
    for base, prefix in PKG_ROOTS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            # compute module name
            rel = p.relative_to(ROOT)
            parts = rel.with_suffix("").parts
            mod = ".".join(parts)
            mod_to_path[mod] = p
            path_to_mod[p] = mod
    return mod_to_path, path_to_mod


def parse_imports(py_path: Path, cur_mod: str) -> Set[str]:
    try:
        src = py_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return set()
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name:
                    mods.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            # Resolve absolute or relative imports
            if getattr(node, 'level', 0):
                # relative: strip levels from current module
                base_parts = cur_mod.split('.')
                # remove leaf (the module itself)
                if base_parts:
                    base_parts = base_parts[:-1]
                # go up levels-1 more (level 1 means same package)
                up = max(0, int(node.level) - 1)
                if up > 0:
                    base_parts = base_parts[:-up] if up <= len(base_parts) else []
                rel_prefix = '.'.join(base_parts)
                target = node.module or ''
                full = f"{rel_prefix}.{target}" if target else rel_prefix
                if full:
                    mods.add(full)
            else:
                if node.module:
                    mods.add(node.module)
    return mods


def build_graph(mod_to_path: Dict[str, Path]) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = {m: set() for m in mod_to_path}
    for mod, path in mod_to_path.items():
        imps = parse_imports(path, mod)
        # Normalize: keep only modules within our index (prefix match)
        for imp in imps:
            # try exact; else collapse to prefix
            if imp in mod_to_path:
                graph[mod].add(imp)
                continue
            # consider package parent chains
            parts = imp.split(".")
            while parts:
                cand = ".".join(parts)
                if cand in mod_to_path:
                    graph[mod].add(cand)
                    break
                parts.pop()
    return graph


def reachable(graph: Dict[str, Set[str]], seeds: Set[str]) -> Set[str]:
    seen: Set[str] = set()
    stack: List[str] = [s for s in seeds if s in graph]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        for n in graph.get(m, ()):  # type: ignore
            if n not in seen:
                stack.append(n)
    return seen


def find_static_assets() -> Set[Path]:
    s = set()
    p = ROOT / "backend" / "static"
    if p.exists():
        for f in p.rglob("*"):
            if f.is_file():
                s.add(f)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["text", "markdown"], default="markdown")
    args = ap.parse_args()

    mod_to_path, path_to_mod = discover_modules()
    graph = build_graph(mod_to_path)
    used_mods = reachable(graph, SEEDS)
    used_paths = {mod_to_path[m] for m in used_mods}

    # Mark static assets
    static_used = find_static_assets()

    # Compute sets
    all_python = set(path_to_mod.keys())
    used_python = used_paths
    unused_python = all_python - used_python

    if args.format == "markdown":
        print("# Usage Audit Report\n")
        print("## Used Python Modules (by seeds)")
        for p in sorted(used_python):
            print(f"- `{p.relative_to(ROOT)}`")
        print("\n## Unused Python Modules (candidate)")
        for p in sorted(unused_python):
            print(f"- `{p.relative_to(ROOT)}`")
        print("\n## Static Assets (served)")
        for p in sorted(static_used):
            print(f"- `{p.relative_to(ROOT)}`")
        print("\n## Seeds")
        for s in sorted(SEEDS):
            print(f"- `{s}`")
    else:
        print("Used Python:")
        for p in sorted(used_python):
            print(" ", p)
        print("\nUnused Python:")
        for p in sorted(unused_python):
            print(" ", p)
        print("\nStatic:")
        for p in sorted(static_used):
            print(" ", p)


if __name__ == "__main__":
    main()
