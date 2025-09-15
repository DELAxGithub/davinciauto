#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import base64
from pathlib import Path
import yaml  # PyYAMLライブラリ
import argparse
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（このスクリプトのあるディレクトリを基準に探索）
ENV_PATH = (Path(__file__).resolve().parent / ".env")
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # CWDからの探索にもフォールバック
    load_dotenv()

# --- 設定項目 ---
THUMBNAIL_DIR = "thumbnails"
VOCAB_FILE = "controlled_vocab.yaml"

# プロバイダ設定（env/CLIで切替）
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

def get_openai_client():
    """OpenAIクライアントを初期化して返す（必要なときのみ）。"""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")  # 任意（OpenAI互換エンドポイント用）
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が見つかりません。.env に 'OPENAI_API_KEY=sk-...' を設定してください。")
    try:
        return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"OpenAIクライアント初期化に失敗: {e}")

def get_gemini_model():
    """Geminiモデルを初期化して返す（必要なときのみ）。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が見つかりません。.env に 'GEMINI_API_KEY=...' を設定してください。")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(GEMINI_MODEL)
    except ImportError:
        raise RuntimeError("google-generativeai が未インストールです。'pip install google-generativeai pillow' を実行してください。")
    except Exception as e:
        raise RuntimeError(f"Geminiモデル初期化に失敗: {e}")

def load_controlled_vocab(filepath):
    """YAMLファイルから管理語彙を読み込む"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # YAMLを読み込んでフラットなリストに変換
            vocab_data = yaml.safe_load(f)
            flat_vocab_list = []
            for category in vocab_data.values():
                flat_vocab_list.extend(category)
            return flat_vocab_list
    except FileNotFoundError:
        print(f"エラー: 管理語彙ファイル '{filepath}' が見つかりません。")
        return None

def encode_image_to_base64(image_path):
    """画像をBase64形式の文字列にエンコードする"""
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
    """画像と管理語彙をAIに送り、タグを生成させる"""
    print(f"🤖  AIが画像を分析中: {os.path.basename(image_path)} ...")

    # 管理語彙リストを文字列に変換
    vocab_string = ", ".join(vocabulary)

    # 新しいプロンプト（編集者向けの明確な役割・目的付与）
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
            # OpenAI Vision
            base64_image = encode_image_to_base64(image_path)
            client = get_openai_client()
            mime = _mime_type_for(image_path)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                max_tokens=100,
            )
            return response.choices[0].message.content

        elif provider == "gemini":
            # Google Gemini Vision（ファイルアップロードでPillow依存を排除）
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
        print(f"❌  AIの分析中にエラーが発生しました: {msg}")
        if "insufficient_quota" in msg or "You exceeded your current quota" in msg:
            print("ヒント: OpenAIのクォータ不足です。--provider gemini で実行、または .env の LLM_PROVIDER=gemini を設定して実行してください。")
        return None


def main():
    parser = argparse.ArgumentParser(description="Analyze thumbnail images and suggest tags from a controlled vocabulary.")
    parser.add_argument(
        "-t", "--thumbnails",
        help="サムネイル画像フォルダへのパス（例: /Users/you/Desktop/resolve_thumbnails/thumbnails）",
        default=None,
    )
    parser.add_argument(
        "-v", "--vocab",
        help="管理語彙YAMLファイルへのパス（デフォルト: controlled_vocab.yaml）",
        default=VOCAB_FILE,
    )
    parser.add_argument(
        "-p", "--provider",
        help="使用プロバイダ（openai / gemini）",
        choices=["openai", "gemini"],
        default=DEFAULT_PROVIDER,
    )
    parser.add_argument(
        "--model",
        help="使用モデル名（プロバイダに応じて解釈: OpenAIなら OPENAI_MODEL、Geminiなら GEMINI_MODEL を上書き）",
        default=None,
    )
    args = parser.parse_args()

    # 管理語彙を読み込む
    vocab = load_controlled_vocab(args.vocab)
    if not vocab:
        return

    # サムネイルフォルダのパスを決定
    project_dir = os.getcwd()
    if args.thumbnails:
        thumbnail_path = os.path.expanduser(args.thumbnails)
    else:
        # カレントディレクトリ直下を優先し、なければ output/thumbnails も探索
        thumbnail_path = os.path.join(project_dir, THUMBNAIL_DIR)
        if not os.path.isdir(thumbnail_path):
            alt_path = os.path.join(project_dir, "output", THUMBNAIL_DIR)
            if os.path.isdir(alt_path):
                thumbnail_path = alt_path

    if not os.path.isdir(thumbnail_path):
        print(
            "エラー: サムネイルフォルダが見つかりません。以下のいずれかを作成/指定してください:\n"
            f" - {os.path.join(project_dir, THUMBNAIL_DIR)}\n"
            f" - {os.path.join(project_dir, 'output', THUMBNAIL_DIR)}\n"
            "または --thumbnails オプションで絶対パスを指定してください。"
        )
        return

    # モデル上書き
    global OPENAI_MODEL, GEMINI_MODEL
    if args.model:
        if args.provider == "openai":
            OPENAI_MODEL = args.model
        elif args.provider == "gemini":
            GEMINI_MODEL = args.model

    print(f"サムネイルフォルダ: {thumbnail_path}")
    print(f"プロバイダ: {args.provider} / モデル: {OPENAI_MODEL if args.provider=='openai' else GEMINI_MODEL}")

    # フォルダ内の画像ファイルを取得（主要拡張子をサポート）
    exts = (".jpg", ".jpeg", ".png", ".webp")
    thumbnail_files = [f for f in os.listdir(thumbnail_path) if f.lower().endswith(exts)]

    if not thumbnail_files:
        print("分析対象のサムネイルが見つかりません。")
        return

    # --- テストのため、最初の1枚だけを分析 ---
    first_image_path = os.path.join(thumbnail_path, thumbnail_files[0])

    generated_tags = analyze_image_with_ai(first_image_path, vocab, provider=args.provider)

    if generated_tags:
        print("\n--- AIによる分析結果 ---")
        print(f"ファイル: {thumbnail_files[0]}")
        print(f"提案されたタグ: {generated_tags}")
        print("--------------------")

if __name__ == "__main__":
    main()
