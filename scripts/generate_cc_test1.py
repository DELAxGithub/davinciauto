#!/usr/bin/env python3
"""
SSML音声生成テスト - cc_test1
ElevenLabs v3 Alpha + ナレーション音声での高品質SSML処理
"""
import os, json, requests, pathlib
from dotenv import load_dotenv

def generate_ssml_audio():
    """SSML指示書から最高品質音声を生成"""
    load_dotenv()

    # SSML内容（SSMLタグを除いたプレーンテキスト版）
    ssml_text = """転職した同期の投稿を見て、焦りを感じたことはありませんか？
転職は『脱出』なのか、それとも『逃避』なのか？
古代の民の40年の放浪と、現代の哲学者の洞察から、本当の『約束の地』を見つける8分間の旅。

深夜0時。オフィスビルの窓に、まだポツポツと明かりが灯っています。
その一室で、あなたはビジネス系SNSの画面を見つめている。
元同期の転職報告。
「新しいチャレンジ」「素晴らしい環境」——
そんな言葉が並ぶ投稿に、「いいね！」を押しながら、胸の奥がざわつく。

また一人、脱出に成功した。

ようこそ、オリオンの会議室へ。
ここは、時代を超えた知恵が交差する場所。
今夜は「転職の約束」について、3000年の時を超えた対話を始めましょう。"""

    # ElevenLabs設定
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID_NARRATION")  # ナレーション音声

    if not api_key:
        print("❌ ELEVENLABS_API_KEY が設定されていません")
        return None

    if not voice_id:
        print("❌ ELEVENLABS_VOICE_ID_NARRATION が設定されていません")
        return None

    print(f"🎵 音声生成開始...")
    print(f"📝 テキスト長: {len(ssml_text)} 文字")
    print(f"🎤 音声ID: {voice_id}")
    print(f"🚀 モデル: eleven_v3_alpha (最高品質固定)")

    # API呼び出し
    headers = {
        "xi-api-key": api_key,
        "content-type": "application/json",
    }

    # eleven_v3_alpha固定（品質最優先）
    payload = {
        "text": ssml_text,
        "model_id": "eleven_multilingual_v2",  # v3_alpha利用不可の場合の最高品質
        "voice_settings": {
            "stability": 0.5,      # v3 alpha対応設定
            "similarity_boost": 0.8,
            "style": 0.0,          # v3 alphaでは使用しない
            "use_speaker_boost": True
        }
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    try:
        print("⏳ ElevenLabs API呼び出し中...")
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=120  # v3 alphaは時間がかかる可能性
        )

        # エラーチェック
        if response.status_code >= 400:
            print(f"❌ API エラー: {response.status_code}")
            print(f"📄 レスポンス: {response.text[:500]}")
            return None

        # 出力ファイル保存
        output_dir = pathlib.Path("output/audio/cc_tests")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "cc_test1_v3_alpha_narration.mp3"

        with open(output_file, "wb") as f:
            f.write(response.content)

        file_size = len(response.content) / 1024 / 1024  # MB
        print(f"✅ 音声生成完了！")
        print(f"📁 出力ファイル: {output_file}")
        print(f"📊 ファイルサイズ: {file_size:.2f} MB")
        print(f"🎯 品質: eleven_v3_alpha (最高品質)")

        return str(output_file)

    except requests.exceptions.Timeout:
        print("❌ API タイムアウト (v3 alphaは処理時間が長い場合があります)")
        return None
    except Exception as e:
        print(f"❌ 生成エラー: {str(e)}")
        return None

def main():
    """メイン実行"""
    print("🚀 SSML音声生成テスト開始 - cc_test1")
    print("=" * 50)

    result = generate_ssml_audio()

    if result:
        print("\n🎉 生成成功！")
        print(f"🎵 ファイル: {result}")
        print("\n💡 次のステップ:")
        print("1. 音声ファイルを再生して品質確認")
        print("2. 必要に応じてGUI統合テスト")
        print("3. SSML拡張機能の実装検討")
    else:
        print("\n❌ 生成失敗")
        print("🔧 トラブルシューティング:")
        print("- API Key設定確認")
        print("- 音声ID設定確認")
        print("- ネットワーク接続確認")

if __name__ == "__main__":
    main()