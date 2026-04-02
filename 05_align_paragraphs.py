#!/usr/bin/env python3
"""B列とC列の改行位置を揃える"""
import json, os, subprocess
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT = "yotayamaguchi2@gmail.com"
client = OpenAI()

PROMPT = """以下のBテキストとCテキストを、意味のまとまりで段落分割してください。

ルール：
・Bを意味のまとまりで5〜8段落に分割する
・Cも同じ段落数に分割する（BとCの段落が1対1で対応するように）
・内容は一切変えない、改行を入れるだけ
・段落の区切りは改行2つ（空行）で表現する
・出力は以下の形式で：

===B===
（段落分割したBテキスト）
===C===
（段落分割したCテキスト）

【Bテキスト】
{b_text}

【Cテキスト】
{c_text}"""


def gog_get(range_str):
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def gog_update(range_str, values):
    vj = json.dumps(values, ensure_ascii=False)
    cmd = ["gog", "sheets", "update", SHEET_ID, range_str, "--values-json", vj, "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def split_paragraphs(b_text, c_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=4000,
            messages=[{"role": "user", "content": PROMPT.format(b_text=b_text[:1500], c_text=c_text[:1500])}]
        )
        output = res.choices[0].message.content.strip()

        if "===B===" in output and "===C===" in output:
            parts = output.split("===C===")
            b_part = parts[0].split("===B===")[1].strip()
            c_part = parts[1].strip()
            return b_part, c_part
    except Exception as e:
        print(f"  ⚠️ API error: {e}")
    return None, None


def main():
    print("📊 データ取得中...")
    data = gog_get("シート1!A:C")
    if not data:
        print("❌ 取得失敗")
        return
    values = data.get("values", data) if isinstance(data, dict) else data

    processed = 0
    for i in range(1, len(values)):
        row = values[i]
        b_val = row[1] if len(row) > 1 else ""
        c_val = row[2] if len(row) > 2 else ""
        row_num = i + 1

        if not b_val or not c_val or len(c_val) < 50:
            continue

        print(f"  [{processed+1}] 行{row_num} (B={len(b_val)}文字, C={len(c_val)}文字)")
        new_b, new_c = split_paragraphs(b_val, c_val)

        if new_b and new_c:
            gog_update(f"シート1!B{row_num}", [[new_b]])
            gog_update(f"シート1!C{row_num}", [[new_c]])
            b_paras = len([p for p in new_b.split("\n\n") if p.strip()])
            c_paras = len([p for p in new_c.split("\n\n") if p.strip()])
            print(f"    → B={b_paras}段落, C={c_paras}段落")
            processed += 1
        else:
            print(f"    → スキップ")

    print(f"\n✅ {processed}行を段落分割しました")


if __name__ == "__main__":
    main()
