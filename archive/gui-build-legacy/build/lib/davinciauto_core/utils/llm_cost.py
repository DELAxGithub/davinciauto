import os, json
from datetime import datetime
from pathlib import Path
from typing import Dict


class LLMCostTracker:
    """
    Lightweight, provider-agnostic LLM cost estimator.
    - Estimates tokens from characters (configurable)
    - Applies per-1K-token input/output unit costs from env
    - Persists usage logs to JSON
    
    Env vars:
      LLM_TOKENS_PER_CHAR        (default: 0.33)
      LLM_IN_COST_PER_1K_TOKENS  (default: 0.0 USD)
      LLM_OUT_COST_PER_1K_TOKENS (default: 0.0 USD)
      LLM_CURRENCY_RATE_USD_JPY  (default: 160.0)
    """

    def __init__(self, log_dir: str = "output/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "llm_usage.json"

        self.tokens_per_char = float(os.getenv("LLM_TOKENS_PER_CHAR", "0.33"))
        self.in_cost_per_1k = float(os.getenv("LLM_IN_COST_PER_1K_TOKENS", "0.0"))
        self.out_cost_per_1k = float(os.getenv("LLM_OUT_COST_PER_1K_TOKENS", "0.0"))
        self.usd_jpy = float(os.getenv("LLM_CURRENCY_RATE_USD_JPY", "160.0"))

    def estimate(self, provider: str, model: str, prompt_chars: int, completion_chars: int) -> Dict:
        in_tokens = prompt_chars * self.tokens_per_char
        out_tokens = completion_chars * self.tokens_per_char
        in_cost_usd = (in_tokens / 1000.0) * self.in_cost_per_1k
        out_cost_usd = (out_tokens / 1000.0) * self.out_cost_per_1k
        total_usd = in_cost_usd + out_cost_usd
        total_jpy = total_usd * self.usd_jpy
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "provider": provider,
            "model": model,
            "prompt_chars": prompt_chars,
            "completion_chars": completion_chars,
            "in_tokens_est": round(in_tokens, 1),
            "out_tokens_est": round(out_tokens, 1),
            "cost_usd": round(total_usd, 4),
            "cost_jpy": round(total_jpy, 2),
        }
        self._append_log(record)
        return record

    def _append_log(self, record: Dict) -> None:
        data = []
        if self.log_file.exists():
            try:
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = [data]
            except Exception:
                data = []
        data.append(record)
        self.log_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

