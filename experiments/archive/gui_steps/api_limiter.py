"""
API制限・コスト管理システム

開発・テスト時に課金APIの使用量を制限し、意図しない高額請求を防ぐ
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import json
from datetime import datetime, timedelta

class APIType(Enum):
    """API種別"""
    ELEVENLABS_TTS = "elevenlabs_tts"
    OPENAI_GPT = "openai_gpt"
    SUNO_MUSIC = "suno_music"
    
class LimitMode(Enum):
    """制限モード"""
    DEVELOPMENT = "development"  # 開発モード（厳しい制限）
    TESTING = "testing"         # テストモード（中程度制限）
    PRODUCTION = "production"   # 本番モード（制限なし）
    DEMO = "demo"              # デモモード（極小制限）

@dataclass
class APILimit:
    """API制限設定"""
    max_requests_per_hour: int = 10
    max_requests_per_day: int = 50
    max_characters_per_request: int = 200
    max_total_characters_per_day: int = 2000
    max_cost_per_day_usd: float = 5.0

@dataclass
class APIUsage:
    """API使用量記録"""
    requests_count: int = 0
    characters_count: int = 0
    estimated_cost_usd: float = 0.0
    last_reset: datetime = None

class APILimiter:
    """API使用量制限・監視システム"""
    
    # 事前定義された制限設定
    LIMIT_PRESETS = {
        LimitMode.DEMO: APILimit(
            max_requests_per_hour=3,
            max_requests_per_day=10,
            max_characters_per_request=100,
            max_total_characters_per_day=500,
            max_cost_per_day_usd=1.0
        ),
        LimitMode.DEVELOPMENT: APILimit(
            max_requests_per_hour=10,
            max_requests_per_day=50,
            max_characters_per_request=300,
            max_total_characters_per_day=3000,
            max_cost_per_day_usd=5.0
        ),
        LimitMode.TESTING: APILimit(
            max_requests_per_hour=30,
            max_requests_per_day=200,
            max_characters_per_request=1000,
            max_total_characters_per_day=15000,
            max_cost_per_day_usd=20.0
        ),
        LimitMode.PRODUCTION: APILimit(
            max_requests_per_hour=1000,
            max_requests_per_day=10000,
            max_characters_per_request=10000,
            max_total_characters_per_day=1000000,
            max_cost_per_day_usd=1000.0
        )
    }
    
    # 概算コスト（文字あたりUSD）
    COST_ESTIMATES = {
        APIType.ELEVENLABS_TTS: 0.00018,  # $0.18 per 1K chars
        APIType.OPENAI_GPT: 0.00002,     # $0.02 per 1K chars (rough)
        APIType.SUNO_MUSIC: 0.1          # Per generation (flat)
    }
    
    def __init__(self, mode: LimitMode = LimitMode.DEVELOPMENT):
        """
        Args:
            mode: 制限モード
        """
        self.mode = mode
        self.limits = self.LIMIT_PRESETS[mode]
        self.usage_file = f"api_usage_{mode.value}.json"
        self.usage = self._load_usage()
    
    def _load_usage(self) -> Dict[str, APIUsage]:
        """使用量記録をファイルから読み込み"""
        if not os.path.exists(self.usage_file):
            return {}
        
        try:
            with open(self.usage_file, 'r') as f:
                data = json.load(f)
                
            usage = {}
            for api_type, values in data.items():
                usage[api_type] = APIUsage(
                    requests_count=values.get('requests_count', 0),
                    characters_count=values.get('characters_count', 0),
                    estimated_cost_usd=values.get('estimated_cost_usd', 0.0),
                    last_reset=datetime.fromisoformat(values.get('last_reset', datetime.now().isoformat()))
                )
            
            return usage
            
        except Exception as e:
            print(f"⚠️ 使用量ファイル読み込みエラー: {e}")
            return {}
    
    def _save_usage(self):
        """使用量記録をファイルに保存"""
        data = {}
        for api_type, usage in self.usage.items():
            data[api_type] = {
                'requests_count': usage.requests_count,
                'characters_count': usage.characters_count,
                'estimated_cost_usd': usage.estimated_cost_usd,
                'last_reset': usage.last_reset.isoformat()
            }
        
        with open(self.usage_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _reset_daily_usage_if_needed(self, api_type: str):
        """必要に応じて日次使用量をリセット"""
        if api_type not in self.usage:
            self.usage[api_type] = APIUsage(last_reset=datetime.now())
            return
        
        last_reset = self.usage[api_type].last_reset
        if datetime.now() - last_reset > timedelta(days=1):
            self.usage[api_type] = APIUsage(last_reset=datetime.now())
    
    def check_limits(self, api_type: APIType, text_length: int) -> tuple[bool, str]:
        """
        API使用前の制限チェック
        
        Args:
            api_type: API種別
            text_length: 使用予定文字数
            
        Returns:
            (使用可能か, 理由メッセージ)
        """
        if self.mode == LimitMode.PRODUCTION:
            return True, "本番モード：制限なし"
        
        api_key = api_type.value
        self._reset_daily_usage_if_needed(api_key)
        
        current_usage = self.usage.get(api_key, APIUsage())
        
        # リクエスト数制限チェック
        if current_usage.requests_count >= self.limits.max_requests_per_day:
            return False, f"日次リクエスト数上限 ({self.limits.max_requests_per_day}) に達しました"
        
        # 文字数制限チェック
        if text_length > self.limits.max_characters_per_request:
            return False, f"1回あたり文字数上限 ({self.limits.max_characters_per_request}) を超過: {text_length}文字"
        
        total_chars_after = current_usage.characters_count + text_length
        if total_chars_after > self.limits.max_total_characters_per_day:
            return False, f"日次文字数上限 ({self.limits.max_total_characters_per_day}) を超過予定"
        
        # コスト制限チェック
        estimated_cost = text_length * self.COST_ESTIMATES.get(api_type, 0.0001)
        total_cost_after = current_usage.estimated_cost_usd + estimated_cost
        if total_cost_after > self.limits.max_cost_per_day_usd:
            return False, f"日次コスト上限 (${self.limits.max_cost_per_day_usd}) を超過予定: ${total_cost_after:.2f}"
        
        return True, f"使用可能 (コスト: ${estimated_cost:.3f})"
    
    def record_usage(self, api_type: APIType, text_length: int):
        """API使用量を記録"""
        api_key = api_type.value
        self._reset_daily_usage_if_needed(api_key)
        
        if api_key not in self.usage:
            self.usage[api_key] = APIUsage(last_reset=datetime.now())
        
        estimated_cost = text_length * self.COST_ESTIMATES.get(api_type, 0.0001)
        
        self.usage[api_key].requests_count += 1
        self.usage[api_key].characters_count += text_length
        self.usage[api_key].estimated_cost_usd += estimated_cost
        
        self._save_usage()
        
        print(f"📊 API使用量記録: {api_type.value} | {text_length}文字 | ${estimated_cost:.3f}")
    
    def get_usage_report(self) -> str:
        """使用量レポートを生成"""
        report = [f"\n📊 API使用量レポート ({self.mode.value}モード)"]
        report.append("=" * 50)
        
        total_cost = 0.0
        
        for api_type, usage in self.usage.items():
            report.append(f"\n🔌 {api_type}:")
            report.append(f"  リクエスト数: {usage.requests_count}/{self.limits.max_requests_per_day}")
            report.append(f"  文字数: {usage.characters_count:,}/{self.limits.max_total_characters_per_day:,}")
            report.append(f"  推定コスト: ${usage.estimated_cost_usd:.3f}")
            report.append(f"  最終リセット: {usage.last_reset.strftime('%Y-%m-%d %H:%M')}")
            
            total_cost += usage.estimated_cost_usd
        
        report.append(f"\n💰 総推定コスト: ${total_cost:.3f}/${self.limits.max_cost_per_day_usd}")
        
        return "\n".join(report)

def create_test_limiter(mode: LimitMode = LimitMode.DEVELOPMENT) -> APILimiter:
    """テスト用のAPIリミッターを作成"""
    return APILimiter(mode)

# 使用例・テスト
if __name__ == "__main__":
    # デモモード（非常に厳しい制限）でテスト
    limiter = create_test_limiter(LimitMode.DEMO)
    
    print("🚨 API制限システムテスト (DEMOモード)")
    
    # テスト用テキスト
    test_texts = [
        "短いテストです。",  # 8文字
        "中程度の長さのテストテキストです。これくらいの長さではどうでしょうか。",  # 37文字
        "非常に長いテストテキストです。" * 10  # 150文字
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n--- テスト {i} ---")
        print(f"テキスト: {text[:50]}...")
        print(f"文字数: {len(text)}")
        
        # 制限チェック
        allowed, reason = limiter.check_limits(APIType.ELEVENLABS_TTS, len(text))
        print(f"判定: {'✅ 許可' if allowed else '❌ 拒否'}")
        print(f"理由: {reason}")
        
        if allowed:
            # 使用量記録（実際にはAPIを呼ばない）
            limiter.record_usage(APIType.ELEVENLABS_TTS, len(text))
    
    # 使用量レポート表示
    print(limiter.get_usage_report())