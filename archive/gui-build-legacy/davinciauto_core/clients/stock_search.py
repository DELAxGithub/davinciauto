"""
Multi-provider stock search client (images/videos/audio).
Providers: Pexels, Unsplash, Storyblocks, Getty(iStock), Pixabay, Freesound

.env 例:
  ENABLE_PEXELS=1
  ENABLE_UNSPLASH=1
  ENABLE_STORYBLOCKS=1
  ENABLE_GETTY=1
  ENABLE_PIXABAY=0
  ENABLE_FREESOUND=0

  PEXELS_API_KEY=...
  UNSPLASH_ACCESS_KEY=...
  STORYBLOCKS_API_KEY=...         # 契約形態に応じて Bearer など
  GETTY_IMAGES_API_KEY=...
  GETTY_IMAGES_API_SECRET=...     # 一部エンドポイントで使用
  PIXABAY_API_KEY=...
  FREESOUND_API_KEY=...

CLI 例:
  python -m clients.stock_search --query "city morning" --type video --limit 3
"""
import os, argparse
from typing import Dict, Any, List
from ..utils.net import request_json

# -------- ENV toggles --------
EN_PEXELS = os.getenv("ENABLE_PEXELS", "0") == "1"
EN_UNSPLASH = os.getenv("ENABLE_UNSPLASH", "0") == "1"
EN_STORYBLOCKS = os.getenv("ENABLE_STORYBLOCKS", "0") == "1"
EN_GETTY = os.getenv("ENABLE_GETTY", "0") == "1"
EN_PIXABAY = os.getenv("ENABLE_PIXABAY", "0") == "1"
EN_FREESOUND = os.getenv("ENABLE_FREESOUND", "0") == "1"

# -------- API Keys --------
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
STORYBLOCKS_KEY = os.getenv("STORYBLOCKS_API_KEY", "")
GETTY_KEY = os.getenv("GETTY_IMAGES_API_KEY", "")
GETTY_SECRET = os.getenv("GETTY_IMAGES_API_SECRET", "")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY", "")

# -------- Base URLs (一部は将来.envで差し替え可能に) --------
PEXELS_IMG_URL = os.getenv("PEXELS_IMAGE_SEARCH_URL", "https://api.pexels.com/v1/search")
PEXELS_VID_URL = os.getenv("PEXELS_VIDEO_SEARCH_URL", "https://api.pexels.com/videos/search")
UNSPLASH_URL = os.getenv("UNSPLASH_SEARCH_URL", "https://api.unsplash.com/search/photos")
# Storyblocks の正式エンドポイントは契約形態に依存: 下記は代表例/占位（必要に応じて差替）
SB_VID_URL = os.getenv("STORYBLOCKS_VIDEO_SEARCH_URL", "https://api.storyblocks.com/api/v2/videos/search")
SB_IMG_URL = os.getenv("STORYBLOCKS_IMAGE_SEARCH_URL", "https://api.storyblocks.com/api/v2/images/search")
GETTY_IMG_URL = os.getenv("GETTY_IMAGE_SEARCH_URL", "https://api.gettyimages.com/v3/search/images")
GETTY_VID_URL = os.getenv("GETTY_VIDEO_SEARCH_URL", "https://api.gettyimages.com/v3/search/videos")
PIXABAY_IMG_URL = os.getenv("PIXABAY_IMAGE_SEARCH_URL", "https://pixabay.com/api/")
PIXABAY_VID_URL = os.getenv("PIXABAY_VIDEO_SEARCH_URL", "https://pixabay.com/api/videos/")
FREESOUND_URL = os.getenv("FREESOUND_SEARCH_URL", "https://freesound.org/apiv2/search/text/")

# -------- Normalized Result Schema --------
# { provider, kind: image|video|audio, id, title, url, preview, duration, width, height, extra }
def norm(provider: str, kind: str, **kw) -> Dict[str, Any]:
    d = {"provider": provider, "kind": kind}
    d.update(kw)
    return d

# -------- Providers --------
def search_pexels(query: str, kind: str, limit: int) -> List[Dict[str,Any]]:
    if not PEXELS_KEY: return []
    headers = {"Authorization": PEXELS_KEY}
    out = []
    if kind in ("image","any"):
        js = request_json("GET", PEXELS_IMG_URL, headers=headers, params={"query": query, "per_page": limit})
        for it in js.get("photos", []):
            out.append(norm(
                "pexels", "image",
                id=it.get("id"),
                title=it.get("alt") or "",
                url=it.get("url"),
                preview=(it.get("src") or {}).get("medium"),
                width=it.get("width"), height=it.get("height"),
                extra={"photographer": it.get("photographer")}
            ))
    if kind in ("video","any"):
        js = request_json("GET", PEXELS_VID_URL, headers=headers, params={"query": query, "per_page": limit})
        for it in js.get("videos", []):
            files = it.get("video_files", [])
            best = sorted(files, key=lambda x: x.get("width",0)*x.get("height",0), reverse=True)[0] if files else {}
            out.append(norm(
                "pexels", "video",
                id=it.get("id"),
                title=it.get("user", {}).get("name",""),
                url=it.get("url"),
                preview=(it.get("video_pictures") or [{}])[0].get("picture"),
                duration=it.get("duration"),
                width=best.get("width"), height=best.get("height"),
                extra={"file_url": best.get("link")}
            ))
    return out[:limit]

def search_unsplash(query: str, limit: int) -> List[Dict[str,Any]]:
    if not UNSPLASH_KEY: return []
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    js = request_json("GET", UNSPLASH_URL, headers=headers, params={"query": query, "per_page": limit})
    out=[]
    for it in js.get("results", []):
        urls = it.get("urls",{})
        out.append(norm(
            "unsplash","image",
            id=it.get("id"), title=it.get("alt_description",""),
            url=urls.get("full"), preview=urls.get("small"),
            width=it.get("width"), height=it.get("height"),
            extra={"user": (it.get("user") or {}).get("username")}
        ))
    return out

def search_storyblocks(query: str, kind: str, limit: int) -> List[Dict[str,Any]]:
    if not STORYBLOCKS_KEY: return []
    # 認証は契約内容により "Authorization: Bearer <token>" など。ここでは API_KEY を想定。
    headers = {"Authorization": STORYBLOCKS_KEY}
    out=[]
    if kind in ("video","any"):
        js = request_json("GET", SB_VID_URL, headers=headers, params={"query": query, "limit": limit})
        for it in js.get("items", []):
            out.append(norm(
                "storyblocks","video",
                id=it.get("id"), title=it.get("title",""),
                url=it.get("preview_url") or it.get("url"),
                preview=it.get("thumbnail_url"),
                duration=it.get("duration"),
                width=it.get("width"), height=it.get("height"),
                extra={"license": it.get("license")}
            ))
    if kind in ("image","any"):
        js = request_json("GET", SB_IMG_URL, headers=headers, params={"query": query, "limit": limit})
        for it in js.get("items", []):
            out.append(norm(
                "storyblocks","image",
                id=it.get("id"), title=it.get("title",""),
                url=it.get("preview_url") or it.get("url"),
                preview=it.get("thumbnail_url"),
                width=it.get("width"), height=it.get("height"),
                extra={"license": it.get("license")}
            ))
    return out[:limit]

def search_getty(query: str, kind: str, limit: int) -> List[Dict[str,Any]]:
    if not GETTY_KEY: return []
    headers = {"Api-Key": GETTY_KEY}
    out=[]
    if kind in ("image","any"):
        js = request_json("GET", GETTY_IMG_URL, headers=headers, params={"phrase": query, "page_size": limit})
        for it in js.get("images", []):
            disp = (it.get("display_sizes") or [{}])[0]
            out.append(norm(
                "getty","image",
                id=it.get("id"), title=it.get("title",""),
                url=it.get("referral_destinations",[{}])[0].get("uri"),
                preview=disp.get("uri"),
                width=None, height=None,
                extra={"collection": it.get("collection_name")}
            ))
    if kind in ("video","any"):
        js = request_json("GET", GETTY_VID_URL, headers=headers, params={"phrase": query, "page_size": limit})
        for it in js.get("videos", []):
            disp = (it.get("display_sizes") or [{}])[0]
            out.append(norm(
                "getty","video",
                id=it.get("id"), title=it.get("title",""),
                url=it.get("referral_destinations",[{}])[0].get("uri"),
                preview=disp.get("uri"),
                duration=it.get("clip_length"),
                extra={"collection": it.get("collection_name")}
            ))
    return out

def search_pixabay(query: str, kind: str, limit: int) -> List[Dict[str,Any]]:
    if not PIXABAY_KEY: return []
    out=[]
    if kind in ("image","any"):
        js = request_json("GET", PIXABAY_IMG_URL, params={"key": PIXABAY_KEY, "q": query, "per_page": limit, "safesearch": "true"})
        for it in js.get("hits", []):
            out.append(norm(
                "pixabay","image",
                id=it.get("id"), title=it.get("tags",""),
                url=it.get("pageURL"), preview=it.get("previewURL"),
                width=it.get("imageWidth"), height=it.get("imageHeight")
            ))
    if kind in ("video","any"):
        js = request_json("GET", PIXABAY_VID_URL, params={"key": PIXABAY_KEY, "q": query, "per_page": limit, "safesearch": "true"})
        for it in js.get("hits", []):
            vids = it.get("videos",{}).get("medium") or {}
            out.append(norm(
                "pixabay","video",
                id=it.get("id"), title=it.get("tags",""),
                url=it.get("pageURL"), preview=it.get("userImageURL"),
                width=vids.get("width"), height=vids.get("height"),
                extra={"file_url": vids.get("url")}
            ))
    return out

def search_freesound(query: str, limit: int) -> List[Dict[str,Any]]:
    if not FREESOUND_KEY: return []
    headers = {"Authorization": f"Token {FREESOUND_KEY}"}
    js = request_json("GET", FREESOUND_URL, headers=headers, params={"query": query, "page_size": limit})
    out=[]
    for it in js.get("results", []):
        previews = it.get("previews") or {}
        out.append(norm(
            "freesound","audio",
            id=it.get("id"), title=it.get("name",""),
            url=f"https://freesound.org/people/{(it.get('username') or '')}/sounds/{it.get('id')}/",
            preview=previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3"),
            duration=it.get("duration"),
            extra={"license": it.get("license")}
        ))
    return out

# -------- Dispatcher --------
def multi_search(query: str, kind: str="any", limit: int=5) -> List[Dict[str,Any]]:
    results: List[Dict[str,Any]] = []
    if EN_PEXELS:
        results += search_pexels(query, kind, limit)
    if EN_UNSPLASH and kind in ("image","any"):
        results += search_unsplash(query, limit)
    if EN_STORYBLOCKS:
        results += search_storyblocks(query, kind, limit)
    if EN_GETTY:
        results += search_getty(query, kind, limit)
    if EN_PIXABAY:
        results += search_pixabay(query, kind, limit)
    if EN_FREESOUND and kind in ("audio","any"):
        results += search_freesound(query, limit)
    # 重複除去（urlベース簡易）
    seen=set(); uniq=[]
    for r in results:
        k = (r.get("provider"), r.get("url") or r.get("preview"))
        if k in seen: continue
        seen.add(k); uniq.append(r)
    # 上位 limit*providers 程度になりがち。呼び出し側でページング推奨
    return uniq

# -------- CLI --------
def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--type", default="any", choices=["any","image","video","audio"])
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
    rows = multi_search(args.query, args.type, args.limit)
    # 人間可読
    for r in rows:
        print(f"[{r['provider']:11s}] {r['kind']:5s} | {r.get('title','')[:40]} | {r.get('url') or r.get('preview')}")

if __name__ == "__main__":
    _cli()
