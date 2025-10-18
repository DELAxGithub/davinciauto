import os, time, requests
from typing import Dict, Any, Optional

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
RATE_LIMIT_SLEEP = float(os.getenv("RATE_LIMIT_SLEEP", "0.3"))
HTTP_PROXY = os.getenv("HTTP_PROXY") or None
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or None

PROXIES = {}
if HTTP_PROXY: PROXIES["http"] = HTTP_PROXY
if HTTPS_PROXY: PROXIES["https"] = HTTPS_PROXY

def request_json(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str,str]]=None,
    params: Optional[Dict[str,Any]]=None
) -> Dict[str, Any]:
    """薄いJSON HTTPラッパー（簡易リトライ）"""
    for attempt in range(3):
        try:
            resp = requests.request(
                method.upper(), url,
                headers=headers, params=params,
                timeout=HTTP_TIMEOUT, proxies=PROXIES
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(RATE_LIMIT_SLEEP * (attempt + 1))
    return {}
