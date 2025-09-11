"""
Simple TTS Fallback Client
シンプルTTSフォールバッククライアント

外部依存なしの基本的なTTS機能実装
"""

import os
import json
import time
import urllib.error
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

# Load .env file manually (fallback for when python-dotenv is not available)
def load_env_if_exists():
    """環境変数読み込み"""
    env_paths = [
        Path(".env"),
        Path("..") / "minivt_pipeline" / ".env",
        Path(__file__).parent.parent / "minivt_pipeline" / ".env"
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            os.environ[key] = value
            except Exception:
                pass
            break

# Load environment variables at module level
load_env_if_exists()

@dataclass
class SimpleTTSResult:
    """シンプルTTS結果"""
    success: bool
    output_file: str = ""
    error_message: str = ""
    duration_sec: float = 0.0
    cost_usd: float = 0.0
    characters_processed: int = 0

class SimpleTTSClient:
    """シンプルTTSクライアント（フォールバック用）"""
    
    def __init__(self):
        """初期化"""
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # ボイス設定
        self.voices = {
            "NA": os.getenv("ELEVENLABS_VOICE_ID_NARRATION", "EXAVITQu4vr4xnSDxMaL"),
            "DL": os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", "WQz3clzUdMqvBf0jswZQ"),
            "FEMALE": os.getenv("ELEVENLABS_VOICE_ID_FEMALE", "WQz3clzUdMqvBf0jswZQ"),
            "MALE": os.getenv("ELEVENLABS_VOICE_ID_MALE", "3JDquces8E8bkmvbh6Bc"),
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """API接続テスト"""
        if not self.api_key:
            return False, "ELEVENLABS_API_KEYが設定されていません"
        
        try:
            # 簡単なHTTPリクエストで接続テスト
            import urllib.request
            import urllib.parse
            import ssl
            
            # SSL証明書検証を無効化（テスト用）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # ElevenLabsのvoices API endpoint
            url = "https://api.elevenlabs.io/v1/voices"
            headers = {
                "xi-api-key": self.api_key,
                "accept": "application/json"
            }
            
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
                if response.status == 200:
                    return True, "API接続成功"
                else:
                    return False, f"API応答エラー: HTTP {response.status}"
                    
        except Exception as e:
            # 一部のキーは voices_read 権限がないため /voices が401になる。
            # その場合でも TTS が許可されているかを最小テキストで検証する。
            try:
                tts_result = self.generate_tts_simple("テスト", self.voices["NA"], "_ping_tts.mp3")
                # 生成物はテストなので削除
                try:
                    Path("_ping_tts.mp3").unlink(missing_ok=True)
                except Exception:
                    pass
                if tts_result.success:
                    return True, "TTS許可あり（voices_readなし）"
                else:
                    return False, f"TTS不可: {tts_result.error_message}"
            except Exception as ee:
                return False, f"接続エラー: {str(e)} / TTS検証失敗: {str(ee)}"
    
    def check_generation_limits(self, text: str) -> Tuple[bool, str]:
        """生成制限チェック（簡易版）"""
        char_count = len(text)
        
        if char_count > 1000:
            return False, f"文字数制限超過: {char_count}/1000文字"
        
        return True, f"制限OK: {char_count}文字"
    
    def generate_tts_simple(self, text: str, voice_id: str, output_file: str) -> SimpleTTSResult:
        """簡易TTS生成（urllib使用）"""
        if not self.api_key:
            return SimpleTTSResult(
                success=False,
                error_message="ELEVENLABS_API_KEYが設定されていません"
            )
        
        try:
            # voice_id 正規化（表示文字列が混入してもID抽出）
            vid = (voice_id or "").strip()
            if ' ' in vid or '(' in vid:
                import re as _re
                m = _re.search(r"([A-Za-z0-9]{12,})", vid)
                if m:
                    vid = m.group(1)
            if not vid:
                return SimpleTTSResult(success=False, error_message="ボイスIDが無効です")
            import urllib.request
            import urllib.parse
            import ssl
            
            # SSL証明書検証を無効化（テスト用）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # API設定
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            # リクエストデータ
            data = {
                "text": text,
                "model_id": "eleven_v3",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            json_data = json.dumps(data).encode('utf-8')
            request = urllib.request.Request(url, data=json_data, headers=headers)
            
            with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
                if response.status == 200:
                    # 音声データ保存
                    output_path = Path(output_file)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.read())
                    
                    # 結果作成
                    duration = len(text) / 4.0  # 概算
                    cost = len(text) * 0.00018  # 概算
                    
                    return SimpleTTSResult(
                        success=True,
                        output_file=str(output_path),
                        duration_sec=duration,
                        cost_usd=cost,
                        characters_processed=len(text)
                    )
                else:
                    error_content = response.read().decode('utf-8', errors='ignore')
                    # デバッグ用詳細出力
                    print(f"🔍 API Debug Info:")
                    print(f"  URL: {url}")
                    print(f"  Voice ID: {voice_id}")
                    print(f"  Text: {text}")
                    print(f"  Request Headers: {headers}")
                    print(f"  Request Data: {json.dumps(data, ensure_ascii=False)}")
                    print(f"  Response Status: {response.status}")
                    print(f"  Response Content: {error_content}")
                    
                    return SimpleTTSResult(
                        success=False,
                        error_message=f"API エラー: HTTP {response.status} - {error_content[:200]}"
                    )
                    
        except urllib.error.HTTPError as e:
            # HTTPエラーの詳細情報
            error_content = ""
            try:
                error_content = e.read().decode('utf-8', errors='ignore')
            except:
                pass
                
            print(f"🔍 HTTP Error Debug Info:")
            print(f"  URL: {url}")
            print(f"  Voice ID: {voice_id}")
            print(f"  Text: {text}")
            print(f"  Request Headers: {headers}")
            print(f"  Request Data: {json.dumps(data, ensure_ascii=False)}")
            print(f"  HTTP Status: {e.code}")
            print(f"  Error Content: {error_content}")
            
            return SimpleTTSResult(
                success=False,
                error_message=f"TTS生成エラー: HTTP Error {e.code}: {error_content[:200] if error_content else str(e)}"
            )
        except Exception as e:
            return SimpleTTSResult(
                success=False,
                error_message=f"TTS生成エラー: {str(e)}"
            )
    
    def get_usage_report(self) -> str:
        """使用統計レポート（簡易版）"""
        return "🎤 シンプルTTSクライアント\n使用統計機能は制限モードでは利用できません"

def create_simple_client() -> SimpleTTSClient:
    """シンプルクライアント作成"""
    return SimpleTTSClient()

# テスト実行
if __name__ == "__main__":
    print("🎤 Simple TTS Client テスト")
    
    client = create_simple_client()
    
    # 接続テスト
    connected, message = client.test_connection()
    print(f"接続テスト: {'✅' if connected else '❌'} {message}")
    
    if connected:
        # 簡単な生成テスト
        test_text = "テストです"
        result = client.generate_tts_simple(test_text, client.voices["NA"], "test_simple.mp3")
        
        if result.success:
            print(f"✅ 生成成功: {result.output_file}")
            print(f"📏 時間: {result.duration_sec:.1f}秒")
            print(f"💰 コスト: ${result.cost_usd:.4f}")
        else:
            print(f"❌ 生成失敗: {result.error_message}")
