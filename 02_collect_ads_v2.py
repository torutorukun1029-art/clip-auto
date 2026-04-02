#!/usr/bin/env python3
"""全ターゲットのad_all_sentenceをスプシに書き込む"""
import json, os, subprocess, requests
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DPRO_EMAIL    = os.environ["DPRO_EMAIL"]
DPRO_PASSWORD = os.environ["DPRO_PASSWORD"]
FIREBASE_API_KEY = "AIzaSyACvJBtwGAk7ZHKzNhWiRY4_g-q0oF8VGQ"
DPRO_API_URL  = "https://api.kashika-20mile.com/api/v1/items"
SHEET_ID      = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT       = "yotayamaguchi2@gmail.com"
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


def gog_get(range_str):
    """gog CLIでデータ取得"""
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    return data.get("values", data) if isinstance(data, dict) else data


def get_existing_b_column():
    """スプシのB列を全取得して既存テキストのリストを返す（類似度チェック用）"""
    print("📊 既存データ確認中...")
    values = gog_get("シート1!B:B")
    existing = []
    for row in values:
        if row and row[0]:
            existing.append(row[0].strip())
    print(f"  既存B列: {len(existing)}件")
    return existing


def is_similar_to_existing(text, existing_texts, threshold=0.8):
    """既存テキストとの類似度チェック（完全一致 or 80%以上類似）"""
    text_short = text[:200]
    for existing in existing_texts:
        if text == existing:
            return True, "完全一致"
        if SequenceMatcher(None, text_short, existing[:200]).ratio() >= threshold:
            return True, "類似"
    return False, ""


def main():
    print("🔑 ログイン中...")
    token = get_token()
    print("✅ ログイン成功！")

    # 既存のB列テキストを取得（重複チェック用）
    existing_texts = get_existing_b_column()

    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
    all_rows = []
    seen_texts = []  # 今回取得分の重複チェック（類似度チェック用にリスト）
    skipped_empty = 0
    skipped_dup = 0
    skipped_existing = 0
    skipped_similar = 0

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
                    ad_text = (item.get("ad_all_sentence") or "").replace("\n", " ").strip()
                    play_count = str(item.get("play_count", "") or "")
                    share_url = item.get("production_share_url") or item.get("production_url") or ""

                    # 空・Noneチェック
                    if not ad_text:
                        skipped_empty += 1
                        continue

                    # 今回取得分の類似度チェック
                    is_dup, _ = is_similar_to_existing(ad_text, seen_texts)
                    if is_dup:
                        skipped_dup += 1
                        print(f"    重複スキップ(今回内): {ad_text[:40]}...")
                        continue

                    # 既存データとの類似度チェック
                    is_sim, reason = is_similar_to_existing(ad_text, existing_texts)
                    if is_sim:
                        if reason == "完全一致":
                            skipped_existing += 1
                        else:
                            skipped_similar += 1
                        print(f"    重複スキップ({reason}): {ad_text[:40]}...")
                        continue

                    seen_texts.add(ad_text)
                    all_rows.append([label, ad_text, "", "", "", share_url, "", play_count])

        print(f"  [{label}] {len([r for r in all_rows if r[0] == label])}件")

    print(f"\n📊 新規: {len(all_rows)}件")
    print(f"  スキップ: 空={skipped_empty} 今回重複={skipped_dup} 既存完全一致={skipped_existing} 既存類似={skipped_similar}")

    if not all_rows:
        print("\n✅ 新規データなし")
        return

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
