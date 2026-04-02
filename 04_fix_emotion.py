#!/usr/bin/env python3
"""G列が50文字以下の抽象的な行だけ再生成して上書き"""
import json, os, subprocess, anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT  = "yotayamaguchi2@gmail.com"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PROMPT_TEMPLATE = """以下の広告を見た視聴者の感情の流れを、視聴者の内なる独り言として番号付きで書いて。
広告の具体的な数字・言葉・状況をそのまま使うこと。
絶対に抽象的な表現だけにしないこと。
ステップ数は広告の長さに応じて自由に決めてOK。

---
以下の広告について書いて：

"""


def gog_get(range_str):
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"❌ gog get error: {result.stderr.strip()}")
        return []
    return json.loads(result.stdout)


def gog_update(range_str, values):
    values_json = json.dumps(values, ensure_ascii=False)
    cmd = ["gog", "sheets", "update", SHEET_ID, range_str,
           "--values-json", values_json, "--account", ACCOUNT]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  ❌ gog update error: {result.stderr.strip()}")
        return False
    return True


def get_emotion_flow(ad_text):
    if not ad_text or len(ad_text) < 10:
        return ""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE + ad_text[:1000]}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"  ⚠️ Anthropic API error: {e}")
        return ""


def main():
    print("📊 スプシからデータ取得中...")
    data = gog_get("シート1!A2:H")
    if not data:
        print("❌ データなし")
        return

    values = data.get("values", data) if isinstance(data, dict) else data
    print(f"  {len(values)}行取得")

    # G列が50文字以下の行を特定
    targets = []
    for i, row in enumerate(values):
        g_val = row[6] if len(row) > 6 else ""
        ad_text = row[1] if len(row) > 1 else ""
        if len(g_val) <= 50 and ad_text and len(ad_text) >= 10:
            row_num = i + 2
            targets.append((row_num, ad_text, g_val))

    print(f"  G列50文字以下: {len(targets)}件")
    if not targets:
        print("✅ 対象なし")
        return

    print("🧠 再生成中...\n")
    for idx, (row_num, ad_text, old_val) in enumerate(targets):
        emotion = get_emotion_flow(ad_text)
        preview = emotion[:60].replace("\n", " ") + "..." if len(emotion) > 60 else emotion.replace("\n", " ")
        print(f"  [{idx+1}/{len(targets)}] 行{row_num}: {preview}")
        gog_update(f"シート1!G{row_num}", [[emotion]])

    print(f"\n✅ {len(targets)}件 上書き完了！")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
