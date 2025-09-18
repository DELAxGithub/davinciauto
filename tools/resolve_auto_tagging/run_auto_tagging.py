#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- 必要なライブラリをすべてインポート ---
import sys
import os
import subprocess
import base64
import yaml
import argparse
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# --- DaVinci Resolve APIのパス設定 ---
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")
try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("エラー: DaVinci Resolveのスクリプトモジュールが見つかりません。")
    sys.exit(1)

# --- .envファイルから環境変数を読み込み ---
# DaVinci Resolve のコンソール等では __file__ が無い場合があるため考慮
try:
    _BASE_DIR = Path(__file__).resolve().parent
except NameError:
    _BASE_DIR = Path(os.getcwd())

_ENV_PATH = _BASE_DIR / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    # カレントや上位ディレクトリを探索
    _found = find_dotenv()
    load_dotenv(_found if _found else None)

# --- これまでの設定と関数をすべて統合 ---

# グローバル設定
THUMBNAIL_DIR = "thumbnails" # 一時的なサムネイル保存場所
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mxf', '.avi', '.braw')
FFMPEG_PATH = '/opt/homebrew/bin/ffmpeg'
VOCAB_FILE = os.getenv("VOCAB_FILE", "controlled_vocab.yaml")

# --- LLM プロバイダ設定 ---
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

def get_openai_client():
    try:
        from openai import OpenAI  # 遅延インポート（未インストール環境を考慮）
    except ImportError:
        raise RuntimeError("openai パッケージが見つかりません。--provider gemini で実行するか、'pip install openai' を行ってください。")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません")
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が見つかりません")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(GEMINI_MODEL)
    except ImportError:
        raise RuntimeError("google-generativeai が未インストールです。'pip install google-generativeai pillow' を実行してください。")

def timecode_to_seconds(timecode_str, fps):
    try:
        clean_tc = timecode_str.replace(';', ':')
        parts = clean_tc.split(':')
        h, m, s, f = [int(p) for p in parts]
        return (h * 3600) + (m * 60) + s + (f / float(fps))
    except Exception:
        return None

def extract_thumbnail(clip_path, output_dir, midpoint_seconds):
    base_filename = os.path.basename(clip_path)
    output_filename = os.path.join(output_dir, f"{base_filename}.jpg")

    if os.path.exists(output_filename):
        os.remove(output_filename) # 念のため古いファイルを削除

    try:
        command = [FFMPEG_PATH, '-i', clip_path, '-ss', str(midpoint_seconds), '-vframes', '1', '-q:v', '3', '-y', output_filename]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_filename
    except Exception as e:
        print(f"❌ サムネイル抽出に失敗: {e}")
        return None

def load_controlled_vocab(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            vocab_data = yaml.safe_load(f)
            flat_vocab_list = []
            for category in vocab_data.values():
                flat_vocab_list.extend(category)
            return flat_vocab_list
    except FileNotFoundError:
        return None

def resolve_path_with_fallbacks(filename: str):
    """'filename' が絶対パスならそのまま。相対の場合は複数の候補から探索して返す。見つからなければ None。"""
    # 環境変数で明示指定があれば優先
    env_path = os.getenv("VOCAB_PATH")
    if env_path:
        p = Path(os.path.expanduser(env_path))
        if p.exists():
            return str(p)

    # ルートディレクトリのヒント（環境変数）
    for root_env in ("DAVINCIAUTO_ROOT", "PROJECT_ROOT", "REPO_ROOT"):
        root = os.getenv(root_env)
        if root:
            candidate = Path(os.path.expanduser(root)) / filename
            if candidate.exists():
                return str(candidate)

    p = Path(filename)
    if p.is_absolute() and p.exists():
        return str(p)

    # まずはベースディレクトリとCWD直下をチェック
    candidates = [
        _BASE_DIR / filename,
        Path.cwd() / filename,
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    # 上位に最大5階層ほど遡って探索
    for start in {_BASE_DIR, Path.cwd()}:
        cur = start
        for _ in range(5):
            test = cur / filename
            if test.exists():
                return str(test)
            if cur.parent == cur:
                break
            cur = cur.parent

    # サブフォルダ再帰検索（負荷回避のため、既知のルートのみ）
    def _looks_like_app_bundle(path: Path) -> bool:
        s = str(path)
        return ".app/Contents" in s or s.endswith(".app")

    def _find_in_subfolders(root: Path, target: str, max_hits: int = 1):
        hits = []
        try:
            for p in root.rglob(target):
                hits.append(p)
                if len(hits) >= max_hits:
                    break
        except Exception:
            return None
        return str(hits[0]) if hits else None

    roots_to_scan = []
    # ユーザが明示したルート
    for root_env in ("DAVINCIAUTO_ROOT", "PROJECT_ROOT", "REPO_ROOT"):
        rv = os.getenv(root_env)
        if rv:
            pr = Path(os.path.expanduser(rv))
            if pr.exists() and not _looks_like_app_bundle(pr):
                roots_to_scan.append(pr)

    # スクリプト基準/CWD も .app 直下でなければ候補に
    if not _looks_like_app_bundle(_BASE_DIR):
        roots_to_scan.append(_BASE_DIR)
    if not _looks_like_app_bundle(Path.cwd()):
        roots_to_scan.append(Path.cwd())

    for root in roots_to_scan:
        found = _find_in_subfolders(root, filename, max_hits=1)
        if found:
            return found
    return None

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def _mime_type_for(image_path: str) -> str:
    ext = os.path.splitext(image_path.lower())[-1]
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"

def analyze_image_with_ai(image_path, vocabulary, provider=DEFAULT_PROVIDER):
    print(f"🤖 AIが画像を分析中: {os.path.basename(image_path)} ...")
    vocab_string = ", ".join(vocabulary)
    prompt_text = f"""
    あなたはプロの映像編集アシスタントです。
    あなたの仕事は、この映像素材が後から「都市の夜景」「孤独感のあるショット」といったキーワードで簡単に検索できるように、的確なメタデータ（タグ）を付けることです。

    # 指示
    1. まず、この画像に何が写っているか、どんな雰囲気かを簡潔に心の中で分析してください。
    2. その分析に基づき、以下の「管理語彙リスト」から最もふさわしいキーワードを最大8個まで選んでください。
    3. 出力は、選んだキーワードをカンマ区切りにした文字列のみにしてください。

    # ルール
    - 「管理語彙リスト」に存在する単語だけを使用してください。
    - 被写体、場所、アクション、ムードなど、多角的な視点から選んでください。
    - もし画像に人物が写っていなければ、絶対に'people'や'man'のような人物タグを選ばないでください。

    # 管理語彙リスト
    {vocab_string}
    """
    try:
        if provider == "openai":
            base64_image = encode_image_to_base64(image_path)
            mime = _mime_type_for(image_path)
            client = get_openai_client()
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64_image}"}},
                    ],
                }],
                max_tokens=100,
            )
            return response.choices[0].message.content
        elif provider == "gemini":
            try:
                import google.generativeai as genai
            except ImportError:
                raise RuntimeError("google-generativeai が未インストールです。'pip install google-generativeai' を実行してください。")
            model = get_gemini_model()
            file = genai.upload_file(path=image_path)
            result = model.generate_content([prompt_text, file])
            return getattr(result, "text", None) or getattr(result, "candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
        else:
            raise RuntimeError(f"未対応のプロバイダ指定です: {provider}")
    except Exception as e:
        msg = str(e)
        print(f"❌ AIの分析中にエラーが発生しました: {msg}")
        if "insufficient_quota" in msg or "You exceeded your current quota" in msg:
            print("ヒント: OpenAIのクォータ不足です。--provider gemini で実行、または .env の LLM_PROVIDER=gemini を設定してください。")
        return None

# --- Media Pool を再帰的に探索して全クリップを取得 ---
def get_media_pool_clips(folder):
    clip_list = []
    clips = folder.GetClipList()
    if clips:
        clip_list.extend(clips)
    for sub_folder in folder.GetSubFolderList():
        clip_list.extend(get_media_pool_clips(sub_folder))
    return clip_list

# --- メインの実行部分 ---
def main():
    parser = argparse.ArgumentParser(description="DaVinci Resolve clips auto-tagging using OpenAI/Gemini.")
    parser.add_argument("-p", "--provider", choices=["openai", "gemini"], default=DEFAULT_PROVIDER, help="使用するLLMプロバイダ")
    parser.add_argument("--model", default=None, help="モデル名を上書き（プロバイダに応じて）")
    parser.add_argument("-v", "--vocab", default=None, help="管理語彙YAMLのパス（未指定時は自動探索）")
    parser.add_argument("--env", dest="env_file", default=None, help="読み込む .env のパス（Resolve環境などで推奨）")
    args = parser.parse_args()

    # 指定があれば .env を追加読み込み（環境変数を上書き）
    if args.env_file:
        env_path = os.path.expanduser(args.env_file)
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            print(f"警告: 指定の .env が見つかりません: {env_path}")

    # モデル名の上書き
    global OPENAI_MODEL, GEMINI_MODEL
    if args.model:
        if args.provider == "openai":
            OPENAI_MODEL = args.model
        else:
            GEMINI_MODEL = args.model
    # Resolveに接続
    try:
        resolve = dvr_script.scriptapp("Resolve")
        project = resolve.GetProjectManager().GetCurrentProject()
        media_pool = project.GetMediaPool()
        root_folder = media_pool.GetRootFolder()
    except Exception:
        print("エラー: DaVinci Resolveに接続できませんでした。")
        return

    # 管理語彙を読み込む
    vocab_path = args.vocab or resolve_path_with_fallbacks(VOCAB_FILE)
    if not vocab_path:
        print(
            "エラー: 管理語彙ファイルが見つかりません。以下を確認してください:\n"
            f" - {_BASE_DIR / VOCAB_FILE}\n"
            f" - {Path.cwd() / VOCAB_FILE}\n"
            "対処:\n"
            " - --vocab で絶対パスを指定\n"
            " - --env で .env を読み込み、.env に VOCAB_PATH を設定\n"
            " - 環境変数 DAVINCIAUTO_ROOT（または PROJECT_ROOT/REPO_ROOT）をリポジトリルートに設定"
        )
        return
    vocab = load_controlled_vocab(vocab_path)
    if not vocab:
        print(f"エラー: 管理語彙ファイル '{vocab_path}' の読み込みに失敗しました。")
        return

    # 一時サムネイル用のフォルダを作成
    # スクリプトがある場所にフォルダを作成
    script_dir = os.path.dirname(os.path.realpath(__file__)) if '__file__' in locals() else os.getcwd()
    thumbnail_output_dir = os.path.join(script_dir, THUMBNAIL_DIR)
    os.makedirs(thumbnail_output_dir, exist_ok=True)
    
    # Media Poolのクリップを走査（サブフォルダまで再帰的に探索）
    print("--- Media Poolの全クリップを検索中... ---")
    all_clips = get_media_pool_clips(root_folder)
    
    print("--- 自動タグ付け処理を開始 ---")
    for clip in all_clips:
        file_path = clip.GetClipProperty("File Path")
        
        if file_path and file_path.lower().endswith(VIDEO_EXTENSIONS):
            clip_name = clip.GetName()
            print(f"\n▶️  処理対象クリップ: {clip_name}")

            # 1. サムネイル抽出
            duration_tc = clip.GetClipProperty("Duration")
            fps = clip.GetClipProperty("FPS")
            duration_sec = timecode_to_seconds(duration_tc, fps)
            
            if not duration_sec or duration_sec <= 0:
                print("⚠️ 時間が取得できずスキップします。")
                continue

            thumb_path = extract_thumbnail(file_path, thumbnail_output_dir, duration_sec / 2.0)
            if not thumb_path:
                continue

            # 2. AIで分析
            ai_tags_str = analyze_image_with_ai(thumb_path, vocab, provider=args.provider)
            os.remove(thumb_path) # サムネイルはすぐに削除
            
            if not ai_tags_str:
                print("⚠️ AIからタグが返されませんでした。")
                continue
            
            # 3. Resolveに書き戻し
            # AIが返す "tag1, tag2, tag3" を "tag1;tag2;tag3" の形式に変換
            tags_for_resolve = ";".join([tag.strip() for tag in ai_tags_str.split(',')])
            
            # SetMetadataを使ってキーワードを書き込む
            success = clip.SetMetadata("Keywords", tags_for_resolve)
            
            if success:
                print(f"✅ キーワードを書き込みました: [{tags_for_resolve}]")
            else:
                print("❌ キーワードの書き込みに失敗しました。")
            
    
    print("--- 全ての処理が完了しました ---")

if __name__ == "__main__":
    main()
