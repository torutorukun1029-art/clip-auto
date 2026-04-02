#!/usr/bin/env python3
"""全ターゲットのad_all_sentenceをスプシに書き込む"""
import json, os, subprocess, requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DPRO_EMAIL    = os.environ["DPRO_EMAIL"]
DPRO_PASSWORD = os.environ["DPRO_PASSWORD"]
FIREBASE_API_KEY = "AIzaSyACvJBtwGAk7ZHKzNhWiRY4_g-q0oF8VGQ"
DPRO_API_URL  = "https://api.kashika-20mile.com/api/v1/items"
SHEET_ID      = "18HyR26udaJEEyudyD-6g6CplYAfHQOS1iCpvLgZa3Io"
ACCOUNT       = "torutorukun1029@gmail.com"
TARGETS_FILE  = Path(__file__).parent / "watch_targets.json"


def get_token():
    resp = requests.post(
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
        params={"key": FIREBASE_API_KEY},
        json={"email": DPRO_EMAIL, "password": DPRO_PASSWORD, "returnSecureToken": True},
        timeout=15)
    return resp.json()["idToken"]


def fetch_by_keyword(token, search_kw, adv_names):
    today = datetime.now().strftime("%Y-%m-%d")
    all_items = []
    for page in range(1, 6):
        try:
            resp = requests.get(DPRO_API_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"to_date": today, "interval": 30, "media_type": "video",
                        "version": 2, "keyword_logic": "or",
                        "keyword": f"in:{search_kw}", "page": page},
                timeout=120)
        except requests.exceptions.ReadTimeout:
            print(f"    ⏳ タイムアウト、スキップ")
            break
        try:
            items = resp.json().get("items", [])
        except (requests.exceptions.JSONDecodeError, ValueError):
            break
        if not items:
            break
        matched = [i for i in items if i.get("advertiser_name") in adv_names]
        all_items.extend(matched)
        if not matched:
            break
    return all_items


def gog_append(rows):
    """gog CLIで行をappend"""
    values_json = json.dumps(rows, ensure_ascii=False)
    cmd = [
        "gog", "sheets", "append", SHEET_ID, "シート1!A:H",
        "--values-json", values_json,
        "--account", ACCOUNT
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  ❌ gog error: {result.stderr.strip()}")
    return result.returncode == 0


def main():
    print("🔑 ログイン中...")
    token = get_token()
    print("✅ ログイン成功！")

    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
    all_rows = []

    for target in targets:
        label = target["label"]
        adv_names = set(target["advertiser_names"])
        seen_urls = set()

        print(f"\n🔍 [{label}] 取得中...")
        for kw in target["search_keywords"]:
            print(f"  キーワード: {kw}")
            for item in fetch_by_keyword(token, kw, adv_names):
                url = item.get("production_url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    ad_text = (item.get("ad_all_sentence") or "").replace("\n", " ")
                    play_count = str(item.get("play_count", "") or "")
                    share_url = item.get("production_share_url") or item.get("production_url") or ""
                    all_rows.append([label, ad_text, "", "", "", share_url, "", play_count])

        print(f"  [{label}] {len([r for r in all_rows if r[0] == label])}件")

    print(f"\n📊 合計 {len(all_rows)}件")

    # 50件ずつappend
    for i in range(0, len(all_rows), 50):
        chunk = all_rows[i:i+50]
        print(f"  📤 {i+1}〜{i+len(chunk)}件目を書き込み中...")
        if not gog_append(chunk):
            print("  ❌ 書き込み失敗、中断")
            break

    print("\n✅ 完了！")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
