import hmac
import hashlib
import time

# ▼▼▼ ご自身のキーに書き換えてください ▼▼▼
PUBLIC_KEY = 'test_3ff8cc205beb8a755f6b18937b70b5b46a378a2446d3db0403c64e96917'
PRIVATE_KEY = 'test_4c30fd82b764076e97783febdb431bd95f9d3b1d24da19176bc875c8b58'
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

def generate_curl_command():
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # キーワード検索用の正しいリソースパス `/api/v2/stock-items/search` を使用します
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    resource = '/api/v2/stock-items/search'
    expires = int(time.time() + 300)
    hmac_data = f"{resource}{expires}".encode('utf-8')
    private_key_bytes = PRIVATE_KEY.encode('utf-8')
    signature = hmac.new(private_key_bytes, hmac_data, hashlib.sha256).hexdigest()

    print("▼▼▼ 以下のcurlコマンドをターミナルにコピー＆ペーストして実行してください ▼▼▼")
    print("curl -v -X GET \\")
    print(f"  -H 'x-storyblocks-public-key: {PUBLIC_KEY}' \\")
    print(f"  -H 'x-storyblocks-expires: {expires}' \\")
    print(f"  -H 'x-storyblocks-signature: {signature}' \\")
    print(f"  'https://api.storyblocks.com{resource}?keywords=city&project_id=v-conte-search-01&user_id=test-user-01&content_type=video'")

if __name__ == '__main__':
    if 'YOUR_PUBLIC_KEY' in PUBLIC_KEY or 'YOUR_PRIVATE_KEY' in PRIVATE_KEY:
        print("エラー: PUBLIC_KEY と PRIVATE_KEY を書き換えてください。")
    else:
        generate_curl_command()