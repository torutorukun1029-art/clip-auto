import os, json, requests, csv
from datetime import datetime

FIREBASE_API_KEY = "AIzaSyACvJBtwGAk7ZHKzNhWiRY4_g-q0oF8VGQ"
DPRO_API_URL = "https://api.kashika-20mile.com/api/v1/items"
EMAIL = os.environ["DPRO_EMAIL"]
PASSWORD = os.environ["DPRO_PASSWORD"]
SEARCH_KEYWORDS = ["みかみ", "アドネス", "スキルプラス"]
ADVERTISER_NAMES = ["アドネス株式会社", "スキルプラス", "みかみ@AI活用の専門家"]
INTERVAL = 30

def get_token():
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    res = requests.post(url, json={"email": EMAIL, "password": PASSWORD, "returnSecureToken": True})
    res.raise_for_status()
    return res.json()["idToken"]

def fetch_ads(token, keyword, page=1):
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().strftime("%Y-%m-%d")
    params = {"version": 2, "interval": INTERVAL, "keyword_logic": "or", "keyword": f"in:{keyword}", "media_type": "video", "page": page, "to_date": today}
    res = requests.get(DPRO_API_URL, headers=headers, params=params, timeout=60)
    res.raise_for_status()
    return res.json()

token = get_token()
print("認証成功")
all_items = {}

for keyword in SEARCH_KEYWORDS:
    print(f"\n検索: {keyword}")
    data = fetch_ads(token, keyword, 1)
    print(f"レスポンスキー: {list(data.keys())}")
    items = data.get("items", data.get("data", []))
    print(f"取得件数: {len(items)}")
    if items:
        print(f"アイテムキー: {list(items[0].keys())}")
        for item in items:
            if item.get("advertiser_name") in ADVERTISER_NAMES:
                url = item.get("url") or item.get("video_url") or str(item.get("id",""))
                all_items[url] = item

print(f"\n合計: {len(all_items)}件")
if all_items:
    sample = list(all_items.values())[0]
    for k,v in sample.items():
        print(f"  {k}: {str(v)[:100]}")
