"""
Enhanced TTS Client with API Limiting and Pronunciation Dictionary
API制限・発音辞書統合TTSクライアント

ElevenLabs TTS + API制限 + 発音辞書 + コスト管理の統合システム
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading
from pydub import AudioSegment

# Import analysis modules
from api_limiter import APILimiter, APIType, LimitMode, create_test_limiter
from pronunciation_dict import PronunciationDictionary, create_orion_dictionary

@dataclass
class TTSRequest:
    """TTS生成リクエスト"""
    text: str
    voice_id: str
    output_file: str
    speaker_type: str = "NA"  # NA, DL, QT
    apply_pronunciation: bool = True
    rate: float = 1.0

@dataclass
class TTSResult:
    """TTS生成結果"""
    success: bool
    output_file: str = ""
    error_message: str = ""
    duration_sec: float = 0.0
    cost_usd: float = 0.0
    characters_processed: int = 0

class TTSError(Exception):
    """TTS生成エラー"""
    pass

class EnhancedTTSClient:
    """拡張TTSクライアント"""
    
    # デフォルト音声ID
    DEFAULT_VOICES = {
        "NA": "EXAVITQu4vr4xnSDxMaL",  # ナレーション用
        "DL": "21m00Tcm4TlvDq8ikWAM",  # 対話用（例）
        "QT": "AZnzlk1XvdvUeBnXmlld",  # 引用用（例）
    }
    
    def __init__(self, limit_mode: LimitMode = LimitMode.DEVELOPMENT):
        """
        Args:
            limit_mode: API制限モード
        """
        # API key確認
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise TTSError("ELEVENLABS_API_KEY environment variable is required")
        
        # 制限・辞書システム初期化
        self.api_limiter = create_test_limiter(limit_mode)
        self.pronunciation_dict = create_orion_dictionary()
        
        # 音声設定
        self.voices = self._load_voice_config()
        
        # 生成統計
        self.generation_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'total_characters': 0,
            'total_cost_usd': 0.0,
            'blocked_requests': 0
        }
    
    def _load_voice_config(self) -> Dict[str, str]:
        """音声設定の読み込み"""
        config = self.DEFAULT_VOICES.copy()
        
        # 環境変数からオーバーライド
        config["NA"] = os.getenv("ELEVENLABS_VOICE_ID_NARRATION", config["NA"])
        config["DL"] = os.getenv("ELEVENLABS_VOICE_ID_DIALOGUE", config["DL"])
        config["QT"] = os.getenv("ELEVENLABS_VOICE_ID_QUOTE", config["QT"])
        
        return config
    
    def _prepare_text(self, text: str, apply_pronunciation: bool = True) -> str:
        """テキストの前処理（発音辞書適用）"""
        if not apply_pronunciation:
            return text
        
        # 発音辞書適用（SSML形式）
        processed_text = self.pronunciation_dict.apply_pronunciation_to_text(text, "ssml")
        
        return processed_text
    
    def _estimate_duration(self, text: str, rate: float = 1.0) -> float:
        """音声時間の推定（概算）"""
        # 日本語の平均読み上げ速度: 約4文字/秒
        chars = len(text.replace(' ', '').replace('\n', ''))
        base_duration = chars / 4.0
        return base_duration / rate
    
    def check_generation_limits(self, text: str) -> Tuple[bool, str]:
        """
        TTS生成前の制限チェック
        
        Args:
            text: 生成予定テキスト
            
        Returns:
            (生成可能か, 理由メッセージ)
        """
        return self.api_limiter.check_limits(APIType.ELEVENLABS_TTS, len(text))
    
    def generate_tts(self, request: TTSRequest, 
                     progress_callback: Optional[callable] = None) -> TTSResult:
        """
        TTS音声生成（メイン関数）
        
        Args:
            request: TTS生成リクエスト
            progress_callback: 進捗コールバック関数(message: str)
            
        Returns:
            TTS生成結果
        """
        self.generation_stats['total_requests'] += 1
        
        try:
            if progress_callback:
                progress_callback("TTS生成開始...")
            
            # 制限チェック
            allowed, reason = self.check_generation_limits(request.text)
            if not allowed:
                self.generation_stats['blocked_requests'] += 1
                return TTSResult(
                    success=False,
                    error_message=f"API制限により拒否: {reason}"
                )
            
            if progress_callback:
                progress_callback("テキスト前処理中...")
            
            # テキスト前処理
            processed_text = self._prepare_text(request.text, request.apply_pronunciation)
            
            # 音声ID選択
            voice_id = request.voice_id or self.voices.get(request.speaker_type, self.voices["NA"])
            
            if progress_callback:
                progress_callback(f"ElevenLabs API呼び出し中... (音声ID: {voice_id[:8]}...)")
            
            # TTS生成実行
            result = self._call_elevenlabs_api(
                text=processed_text,
                voice_id=voice_id,
                output_file=request.output_file,
                rate=request.rate,
                progress_callback=progress_callback
            )
            
            if result.success:
                # 使用量記録
                self.api_limiter.record_usage(APIType.ELEVENLABS_TTS, len(request.text))
                
                # 統計更新
                self.generation_stats['successful_requests'] += 1
                self.generation_stats['total_characters'] += len(request.text)
                self.generation_stats['total_cost_usd'] += result.cost_usd
                
                if progress_callback:
                    progress_callback(f"生成完了: {result.output_file}")
            
            return result
            
        except Exception as e:
            error_msg = f"TTS生成エラー: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            
            return TTSResult(
                success=False,
                error_message=error_msg
            )
    
    def _call_elevenlabs_api(self, text: str, voice_id: str, output_file: str, 
                           rate: float = 1.0, progress_callback: Optional[callable] = None) -> TTSResult:
        """ElevenLabs API呼び出し"""
        
        # API設定
        # voice_id 正規化
        vid = (voice_id or "").strip()
        if ' ' in vid or '(' in vid:
            try:
                import re as _re
                m = _re.search(r"([A-Za-z0-9]{12,})", vid)
                if m:
                    vid = m.group(1)
            except Exception:
                pass
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # リクエストデータ
        data = {
            "text": text,
            "model_id": "eleven_v3",  # 最新モデル（alpha）
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        try:
            # API呼び出し
            if progress_callback:
                progress_callback("API応答待機中...")
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            # レスポンス確認
            if response.status_code != 200:
                error_msg = f"ElevenLabs API エラー: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:200]}"
                raise TTSError(error_msg)
            
            # 音声データ保存
            if progress_callback:
                progress_callback("音声ファイル保存中...")
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # 速度調整（必要に応じて）
            if rate != 1.0:
                if progress_callback:
                    progress_callback(f"速度調整中... (×{rate})")
                
                self._adjust_playback_rate(output_path, rate)
            
            # 結果作成
            duration = self._estimate_duration(text, rate)
            cost = len(text) * 0.00018  # ElevenLabs概算コスト
            
            return TTSResult(
                success=True,
                output_file=str(output_path),
                duration_sec=duration,
                cost_usd=cost,
                characters_processed=len(text)
            )
            
        except requests.RequestException as e:
            raise TTSError(f"API通信エラー: {str(e)}")
        except Exception as e:
            raise TTSError(f"音声生成エラー: {str(e)}")
    
    def _adjust_playback_rate(self, audio_file: Path, rate: float):
        """音声速度調整"""
        try:
            # pydubを使用した速度調整
            audio = AudioSegment.from_mp3(str(audio_file))
            
            # 速度変更（ピッチ維持）
            # 注意: この方法はピッチも変わります。高品質な速度調整にはより高度な処理が必要
            adjusted_audio = audio.speedup(playback_speed=rate)
            
            # 上書き保存
            adjusted_audio.export(str(audio_file), format="mp3")
            
        except Exception as e:
            # 速度調整失敗は警告のみ（元ファイルは保持）
            print(f"⚠️ 速度調整失敗: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """API接続テスト"""
        try:
            test_text = "テスト"
            test_output = Path("temp_test_audio.mp3")
            
            # 制限チェック
            allowed, reason = self.check_generation_limits(test_text)
            if not allowed:
                return False, f"制限によりテスト不可: {reason}"
            
            # 短いテスト生成
            result = self._call_elevenlabs_api(
                text=test_text,
                voice_id=self.voices["NA"],
                output_file=str(test_output)
            )
            
            # テストファイル削除
            if test_output.exists():
                test_output.unlink()
            
            if result.success:
                return True, "接続成功"
            else:
                return False, result.error_message
                
        except Exception as e:
            return False, f"接続テストエラー: {str(e)}"
    
    def get_usage_report(self) -> str:
        """使用統計レポート生成"""
        stats = self.generation_stats
        api_report = self.api_limiter.get_usage_report()
        
        report = [
            "🎤 TTS生成統計",
            "=" * 30,
            f"総リクエスト数: {stats['total_requests']}",
            f"成功: {stats['successful_requests']}",
            f"ブロック: {stats['blocked_requests']}",
            f"総文字数: {stats['total_characters']:,}",
            f"推定コスト: ${stats['total_cost_usd']:.3f}",
            "",
            "API制限状況:",
            api_report
        ]
        
        return "\n".join(report)

# テスト・デモ用の便利関数
def create_test_client(mode: LimitMode = LimitMode.DEVELOPMENT) -> EnhancedTTSClient:
    """テスト用TTSクライアント作成"""
    return EnhancedTTSClient(mode)

# 使用例・テスト
if __name__ == "__main__":
    print("🎤 Enhanced TTS Client テスト")
    
    # テスト用クライアント作成（DEMOモードで安全に）
    try:
        client = create_test_client(LimitMode.DEMO)
        
        # 接続テスト
        print("\n📡 API接続テスト中...")
        connected, message = client.test_connection()
        print(f"結果: {'✅ 成功' if connected else '❌ 失敗'}")
        print(f"詳細: {message}")
        
        if connected:
            # サンプルテキストでテスト
            print("\n🎯 サンプル生成テスト...")
            
            test_request = TTSRequest(
                text="ニーチェは「神は死んだ」と宣言しました。",
                voice_id="",  # デフォルト使用
                output_file="test_output.mp3",
                speaker_type="NA",
                apply_pronunciation=True
            )
            
            def progress_callback(message: str):
                print(f"📊 {message}")
            
            result = client.generate_tts(test_request, progress_callback)
            
            if result.success:
                print(f"✅ 生成成功: {result.output_file}")
                print(f"📏 時間: {result.duration_sec:.1f}秒")
                print(f"💰 コスト: ${result.cost_usd:.4f}")
            else:
                print(f"❌ 生成失敗: {result.error_message}")
        
        # 使用統計表示
        print("\n📊 使用統計:")
        print(client.get_usage_report())
        
    except TTSError as e:
        print(f"❌ TTSクライアントエラー: {e}")
        print("💡 ELEVENLABS_API_KEY 環境変数を設定してください")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
