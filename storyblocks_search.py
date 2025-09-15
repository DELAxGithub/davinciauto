import requests
import json
import time
import hmac
import hashlib
import os
try:
    from dotenv import load_dotenv
    # スクリプト自身の場所を基準に .env ファイルのパスを解決
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv() # 見つからない場合はカレントディレクトリを探す（フォールバック）
except ImportError:
    print("Warning: python-dotenv がインストールされていません。'pip install python-dotenv' の実行をおすすめします。")

# ==============================================================================
# ▼▼▼ 設定項目 ▼▼▼
# ==============================================================================
# .envファイルに STORYBLOCKS_PUBLIC_KEY と STORYBLOCKS_PRIVATE_KEY を設定してください
PUBLIC_KEY = os.getenv('STORYBLOCKS_PUBLIC_KEY')
PRIVATE_KEY = os.getenv('STORYBLOCKS_PRIVATE_KEY')

# 出力されるHTMLファイルの名前
OUTPUT_HTML_PATH = 'storyblocks_report.html'

# 1つのキーワードあたり何件の結果を取得するか
SEARCH_RESULT_COUNT = 12
# ==============================================================================


def get_storyblocks_auth_headers(resource_path: str, private_key: str, public_key: str) -> dict:
    """
    Storyblocks APIのHMAC認証ヘッダーを生成します。
    公式ドキュメントに基づいた正しいHMAC生成ロジックを使用します。
    """
    expires = str(int(time.time() + 300))  # 5分後に有効期限切れ

    # キー: privateKey + expires, メッセージ: resource
    hmac_key = (private_key + expires).encode('utf-8')
    hmac_message = resource_path.encode('utf-8')
    
    signature = hmac.new(hmac_key, hmac_message, hashlib.sha256).hexdigest()
    
    return {
        'x-storyblocks-public-key': public_key,
        'x-storyblocks-expires': expires,
        'x-storyblocks-signature': signature,
    }
# メインの処理
def main():
    storyboard_data = [
        {'cut_number': '1', 'search_keyword_english': 'night office building lights city'},
        {'cut_number': '2', 'search_keyword_english': 'man looking at computer screen night'},
        {'cut_number': '3', 'search_keyword_english': 'hand clicking mouse computer'},
        {'cut_number': '4', 'search_keyword_english': 'social media likes animation'},
        {'cut_number': '5', 'search_keyword_english': 'starry sky galaxy abstract meeting room'},
        {'cut_number': '6', 'search_keyword_english': 'constellation animation connecting stars'},
        {'cut_number': '7', 'search_keyword_english': 'constellation historical people abstract'},
    ]
    html_content = """
    <!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
    <title>Storyblocks 映像素材 検索レポート</title>
    <style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:2em;background-color:#f4f4f9;color:#333}h1{color:#1a1a2e}.cut-section{margin-bottom:3em;border-top:2px solid #ddd;padding-top:2em}.cut-header{font-size:1.8em;font-weight:bold;margin-bottom:1em;color:#16213e}.results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1.5em}.video-item{background-color:#fff;border-radius:8px;box-shadow:0 4px 8px rgba(0,0,0,.1);overflow:hidden;transition:transform .2s}.video-item:hover{transform:translateY(-5px)}.video-item img{display:block;width:100%;height:auto}.video-item a{text-decoration:none}</style></head><body>
    <h1>Storyblocks 映像素材 検索レポート</h1>
    """
    for cut in storyboard_data:
        cut_number = cut['cut_number']
        keyword = cut['search_keyword_english']
        print(f"[{cut_number}/{len(storyboard_data)}] \"{keyword}\" を検索中...")
        html_content += f'<div class="cut-section"><div class="cut-header">Cut {cut_number}: "{keyword}"</div><div class="results-grid">'
        
        # APIエンドポイントとパラメータを stock_search.py に合わせる
        resource = '/api/v2/videos/search'
        api_url = f"https://api.storyblocks.com{resource}"
        
        # ★★★ 公式ドキュメントに基づいた正しいHMAC認証方式に戻しました ★★★
        headers = get_storyblocks_auth_headers(resource, PRIVATE_KEY, PUBLIC_KEY)
        
        params = {
            'query': keyword,
            'limit': SEARCH_RESULT_COUNT
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            results = response.json()
            if not results.get('items'): # ★ レスポンスのキーを 'items' に修正
                html_content += "<p>素材が見つかりませんでした。</p>"
            else:
                for item in results['items']: # ★ レスポンスのキーを 'items' に修正
                    thumb_url = item.get('thumbnail_url')
                    details_url = item.get('details_url')
                    if thumb_url and details_url:
                        html_content += f'<div class="video-item"><a href="{details_url}" target="_blank" rel="noopener noreferrer"><img src="{thumb_url}" loading="lazy"></a></div>'
        except requests.exceptions.RequestException as e:
            print(f"  エラー: APIリクエストに失敗しました - {e}")
            html_content += f"<p>APIリクエスト中にエラーが発生しました: {e}</p>"
        html_content += '</div></div>'
    html_content += '</body></html>'

    with open(OUTPUT_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n完了！ レポートが {OUTPUT_HTML_PATH} として保存されました。")
    print("このファイルをブラウザで開いて結果を確認してください。")

if __name__ == '__main__':
    if not PUBLIC_KEY or not PRIVATE_KEY:
        print("エラー: 環境変数 STORYBLOCKS_PUBLIC_KEY と STORYBLOCKS_PRIVATE_KEY が設定されていません。")
        print("スクリプトと同じフォルダに .env ファイルを作成し、以下のように記述してください。")
        print("\nSTORYBLOCKS_PUBLIC_KEY=your_public_key")
        print("STORYBLOCKS_PRIVATE_KEY=your_private_key")
    else:
        main()