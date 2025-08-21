import os, json, time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class CostTracker:
    """
    ElevenLabs API使用量とコスト追跡システム
    
    Features:
    - 文字数ベースのコスト計算 (1文字=1クレジット)
    - セッション別・累積コスト管理
    - 使用ログのJSON出力
    - モデル別料金対応
    """
    
    # ElevenLabs API 料金表 (クレジット/文字)
    MODEL_COSTS = {
        "eleven_v3": 1.0,  # V3モデル: 1クレジット/文字
        "eleven_multilingual_v2": 1.0,  # V2モデル: 1クレジット/文字
        "eleven_flash_v2_5": 0.3,  # Flash V2.5: 0.3クレジット/文字
    }
    
    # 2025年6月までのV3特別割引
    V3_DISCOUNT_RATE = 0.2  # 80%割引 = 20%料金
    V3_DISCOUNT_END = "2025-06-30"
    
    def __init__(self, log_dir: str = "output/logs"):
        """
        CostTracker初期化
        
        Args:
            log_dir: ログファイル出力ディレクトリ
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # セッション情報
        self.session_start = datetime.now()
        self.session_requests: List[Dict] = []
        self.session_total_chars = 0
        self.session_total_credits = 0.0
        
        # ログファイルパス
        self.log_file = self.log_dir / "usage_log.json"
        
    def track_request(self, text: str, model_id: str = "eleven_v3", voice_id: str = "unknown") -> float:
        """
        APIリクエストを追跡し、コストを計算
        
        Args:
            text: TTS生成テキスト
            model_id: 使用したElevenLabsモデルID
            voice_id: 使用した音声ID
            
        Returns:
            float: このリクエストのコスト（クレジット）
        """
        char_count = len(text)
        base_cost = self.MODEL_COSTS.get(model_id, 1.0) * char_count
        
        # V3モデルの特別割引適用
        if model_id == "eleven_v3" and self._is_discount_active():
            actual_cost = base_cost * self.V3_DISCOUNT_RATE
            discount_applied = True
        else:
            actual_cost = base_cost
            discount_applied = False
            
        # リクエスト記録
        request_data = {
            "timestamp": datetime.now().isoformat(),
            "text": text[:100] + "..." if len(text) > 100 else text,  # 最初の100文字のみ記録
            "char_count": char_count,
            "model_id": model_id,
            "voice_id": voice_id,
            "base_cost": base_cost,
            "actual_cost": actual_cost,
            "discount_applied": discount_applied
        }
        
        self.session_requests.append(request_data)
        self.session_total_chars += char_count
        self.session_total_credits += actual_cost
        
        return actual_cost
        
    def get_session_stats(self) -> Dict:
        """
        現在のセッション統計を取得
        
        Returns:
            Dict: セッション統計情報
        """
        return {
            "session_start": self.session_start.isoformat(),
            "duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "requests_count": len(self.session_requests),
            "total_characters": self.session_total_chars,
            "total_credits": round(self.session_total_credits, 3),
            "estimated_cost_jpy": round(self.session_total_credits * 1.5, 2),  # 1クレジット≈1.5円想定
            "average_chars_per_request": round(self.session_total_chars / max(len(self.session_requests), 1), 1)
        }
        
    def get_cost_summary(self) -> str:
        """
        コスト要約を文字列で取得
        
        Returns:
            str: 表示用コスト要約
        """
        stats = self.get_session_stats()
        
        discount_note = ""
        if any(req["discount_applied"] for req in self.session_requests):
            discount_note = " (V3割引適用)"
            
        return (
            f"💰 API Usage Cost: ¥{stats['estimated_cost_jpy']} "
            f"({stats['requests_count']} requests, {stats['total_characters']} chars, "
            f"{stats['total_credits']} credits{discount_note})"
        )
        
    def save_usage_log(self) -> str:
        """
        使用ログをJSONファイルに保存
        
        Returns:
            str: 保存されたファイルパス
        """
        log_data = {
            "session_info": self.get_session_stats(),
            "requests": self.session_requests,
            "system_info": {
                "model_costs": self.MODEL_COSTS,
                "v3_discount_active": self._is_discount_active(),
                "log_generated": datetime.now().isoformat()
            }
        }
        
        # 既存ログの読み込み（累積記録用）
        all_logs = []
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        all_logs = existing_data
                    else:
                        all_logs = [existing_data]
            except (json.JSONDecodeError, IOError):
                all_logs = []
                
        # 新しいセッションデータを追加
        all_logs.append(log_data)
        
        # ファイル保存
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(all_logs, f, ensure_ascii=False, indent=2)
            
        return str(self.log_file)
        
    def get_total_usage(self) -> Dict:
        """
        累積使用量を計算（過去のログファイルを含む）
        
        Returns:
            Dict: 累積使用統計
        """
        total_requests = len(self.session_requests)
        total_chars = self.session_total_chars
        total_credits = self.session_total_credits
        
        # 過去のログを読み込み
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    all_logs = json.load(f)
                    if isinstance(all_logs, list):
                        for log_session in all_logs[:-1]:  # 現在のセッション以外
                            session_info = log_session.get("session_info", {})
                            total_requests += session_info.get("requests_count", 0)
                            total_chars += session_info.get("total_characters", 0)
                            total_credits += session_info.get("total_credits", 0)
            except (json.JSONDecodeError, IOError):
                pass
                
        return {
            "total_requests": total_requests,
            "total_characters": total_chars,
            "total_credits": round(total_credits, 3),
            "estimated_total_cost_jpy": round(total_credits * 1.5, 2)
        }
        
    def _is_discount_active(self) -> bool:
        """
        V3モデルの特別割引が有効かチェック
        
        Returns:
            bool: 割引有効フラグ
        """
        try:
            discount_end = datetime.strptime(self.V3_DISCOUNT_END, "%Y-%m-%d")
            return datetime.now() < discount_end
        except ValueError:
            return False