#!/usr/bin/env python3
"""
DaVinci Auto GUI Launcher
デスクトップから起動用のランチャー
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """GUIランチャーメイン"""
    # このスクリプトのディレクトリ
    script_dir = Path(__file__).parent
    
    # GUIスクリプトのパス
    gui_script = script_dir / "enhanced_integrated_workspace.py"
    
    # ディレクトリを移動
    os.chdir(script_dir)
    
    print("🎬 DaVinci Auto GUI 起動中...")
    print(f"📂 作業ディレクトリ: {script_dir}")
    print(f"🐍 Python: {sys.executable}")
    print(f"🎯 GUIスクリプト: {gui_script}")
    
    if not gui_script.exists():
        print("❌ GUIスクリプトが見つかりません")
        input("Enterキーを押して終了...")
        return
    
    try:
        # Python環境の確認
        print("🔍 環境チェック中...")
        
        # GUI起動
        print("🚀 GUI起動...")
        subprocess.run([sys.executable, str(gui_script)], check=True)
        
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによる中断")
    except subprocess.CalledProcessError as e:
        print(f"❌ GUI起動エラー: {e}")
        input("Enterキーを押して終了...")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        input("Enterキーを押して終了...")

if __name__ == "__main__":
    main()