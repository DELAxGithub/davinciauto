#!/usr/bin/env bash
set -euo pipefail

# repo_tree.sh
# Print a concise repository tree focused on source files.
# Usage: ./scripts/repo_tree.sh [root=. ] [max_depth=3]

ROOT_DIR="${1:-.}"
MAX_DEPTH="${2:-3}"

has_cmd() { command -v "$1" >/dev/null 2>&1; }

# Build a file list using ripgrep if available, otherwise fallback to find
gather_files() {
  if has_cmd rg; then
    rg --files "$ROOT_DIR" \
      --hidden \
      -g '!**/.git/**' \
      -g '!**/.venv/**' \
      -g '!**/__pycache__/**' \
      -g '!**/output/**' \
      -g '!**/thumbnails/**' \
      -g '!**/*.mp3' -g '!**/*.wav' -g '!**/*.m4a' -g '!**/*.flac' \
      -g '!**/*.zip' -g '!**/*.tar' -g '!**/*.tgz' \
      -g '!**/*.exe' -g '!**/*.dmg' \
      -g '!**/DaVinci Auto GUI.app/**' \
      -g '!**/*.bin' -g '!**/*.pdf' \
      -g '!**/*.xml' \
      -g '!**/.DS_Store' \
      -g '!**/*.pyc' \
      -g '!**/*.so' \
      -g '!**/*.o' \
      -g '!**/*.class' \
      -g '!**/node_modules/**' \
      | LC_ALL=C sort
  else
    # Fallback: find text-like files only
    find "$ROOT_DIR" \( \
        -path '*/.git' -o \
        -path '*/.venv' -o \
        -path '*/__pycache__' -o \
        -path '*/output' -o \
        -path '*/thumbnails' -o \
        -path '*/node_modules' -o \
        -path '*/DaVinci Auto GUI.app' \
      \) -prune -o \
      -type f \( \
        -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.json' -o \
        -name '*.html' -o -name '*.css' -o -name '*.md' -o -name '*.txt' -o \
        -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.ini' -o \
        -name '*.csv' \
      \) -print | LC_ALL=C sort
  fi
}

# Render a tree view up to MAX_DEPTH by directory depth
render_tree() {
  awk -v maxd="$MAX_DEPTH" -v root="$ROOT_DIR" '
    BEGIN {
      # Normalize root path (remove trailing / and ./)
      gsub(/\/$/, "", root);
      if (root == ".") root = "";
      print "Repo tree (depth=" maxd ")";
    }
    {
      path = $0;
      # strip root prefix
      if (root != "" && index(path, root "/") == 1) {
        path = substr(path, length(root)+2);
      }
      n = split(path, seg, "/");
      if (n > maxd) {
        # collapse deeper paths to the directory at max depth
        out = "";
        for (i=1; i<=maxd-1; i++) out = out seg[i] "/";
        out = out seg[maxd] "/...";
        key = out;
      } else {
        key = path;
      }
      seen[key] = 1;
    }
    END {
      # print grouped unique entries sorted
      n=asorti(seen, idx);
      for (i=1; i<=n; i++) {
        p = idx[i];
        # indent by depth
        depth = split(p, seg, "/");
        indent = "";
        for (k=1; k<depth; k++) indent = indent "  ";
        print indent "- " p;
      }
    }
  '
}

gather_files | render_tree

