#!/usr/bin/env python3
"""再生数上位50件の感情の流れをAnthropic APIで生成してG列に書き込む"""
import json, os, subprocess, anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT  = "yotayamaguchi2@gmail.com"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def gog_get(range_str):
    """gog sheets getでデータ取得"""
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"❌ gog get error: {result.stderr.strip()}")
        return []
    return json.loads(result.stdout)


def gog_update(range_str, values):
    """gog sheets updateでデータ書き込み"""
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
        prompt = """以下の広告を見た視聴者の感情の流れを、視聴者の内なる独り言として番号付きで書いて。
ステップ数は広告の長さ・内容に応じて自由に決めてOK。
各ステップは具体的に「状況認識＋感情＋内なる言葉」で書くこと。
広告に出てくる具体的な数字・言葉・状況をそのまま使うこと。
絶対に「共感→期待→行動」みたいな抽象的な表現だけにしないこと。

出力例：
①これ、自分の状況そのままだ…
→ 事故の慰謝料って、まさに今の自分の話じゃん

②え、まだ増やせる余地あるの？
→ もう決まってると思ってたけど、まだ変えられるのか？

③じゃあ今もらってる額って少ない可能性ある？
→ もしかして、本来より低い金額で納得しようとしてた？

---
以下の広告について書いて：

""" + ad_text[:1000]
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"  ⚠️ Anthropic API error: {e}")
        return ""


def main():
    # 1. H列（累計再生数）とB列（広告原文）を取得
    print("📊 スプシからデータ取得中...")
    data = gog_get("シート1!A2:H")

    if not data:
        print("❌ データなし")
        return

    # gog --json の結果からvaluesを取り出す
    values = data.get("values", data) if isinstance(data, dict) else data
    print(f"  {len(values)}行取得")

    # 再生数でソートして上位50件を特定（行番号を保持）
    rows_with_index = []
    for i, row in enumerate(values):
        # row: [A, B, C, D, E, F, G, H]
        play_count_str = row[7] if len(row) > 7 else ""
        try:
            play_count = int(str(play_count_str).replace(",", ""))
        except (ValueError, TypeError):
            play_count = 0
        ad_text = row[1] if len(row) > 1 else ""
        rows_with_index.append((i, play_count, ad_text))

    rows_with_index.sort(key=lambda x: x[1], reverse=True)
    top50 = rows_with_index[:50]

    print(f"\n🏆 上位50件（再生数 {top50[0][1]:,} 〜 {top50[-1][1]:,}）")

    # 2. Claude APIで感情の流れを生成して書き込む
    print("🧠 感情の流れ生成中...\n")
    for rank, (idx, play_count, ad_text) in enumerate(top50):
        row_num = idx + 2  # ヘッダー行分+1、0始まり+1
        emotion = get_emotion_flow(ad_text)
        print(f"  [{rank+1}/50] 行{row_num} (再生数{play_count:,}): {emotion}")

        # G列に書き込み
        gog_update(f"シート1!G{row_num}", [[emotion]])

    print("\n✅ 完了！")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
