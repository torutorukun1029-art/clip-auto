#!/usr/bin/env python3
"""C列が空白の行をB列からリライトして埋める"""
import json, os, subprocess, sys
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT = "yotayamaguchi2@gmail.com"
client = OpenAI()

RULES = open(Path(__file__).parent / "CLAUDE.md", encoding="utf-8").read()

# 03_rewrite.pyのプロンプトを読み込み
import importlib.util
spec = importlib.util.spec_from_file_location("rewrite", Path(__file__).parent / "03_rewrite.py")
rewrite_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rewrite_mod)


def gog_get(range_str):
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def gog_update(range_str, values):
    vj = json.dumps(values, ensure_ascii=False)
    cmd = ["gog", "sheets", "update", SHEET_ID, range_str, "--values-json", vj, "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def main():
    print("📊 データ取得中...")
    data = gog_get("シート1!B:C")
    if not data:
        print("❌ 取得失敗")
        return
    values = data.get("values", data) if isinstance(data, dict) else data

    # C列が空白でB列100文字以上の行を特定
    targets = []
    for i, row in enumerate(values):
        if i == 0: continue
        b = row[0] if len(row) > 0 else ""
        c = row[1] if len(row) > 1 else ""
        if b and len(b) > 100 and (not c or len(c.strip()) < 10):
            targets.append((i + 1, b))

    print(f"C列空白: {len(targets)}行")

    written = 0
    for idx, (row_num, ad_text) in enumerate(targets):
        b_len = len(ad_text)
        print(f"  [{idx+1}/{len(targets)}] 行{row_num} (B={b_len}文字)", end="", flush=True)

        result = None
        for attempt in range(3):
            result = rewrite_mod.rewrite(ad_text)
            if not result or len(result) < 50:
                continue
            if "申し訳" in result or "できません" in result:
                result = None
                continue
            break

        if result and len(result) >= 50:
            # 末尾に「採用代行ならトルトルくん」がなければ追加
            if "採用代行ならトルトルくん" not in result:
                result = result.rstrip() + " 採用代行ならトルトルくん"
            gog_update(f"シート1!C{row_num}", [[result]])
            print(f" → {len(result)}文字 ✅")
            written += 1
        else:
            print(f" → スキップ")

    print(f"\n✅ {written}行を書き込みました")


if __name__ == "__main__":
    main()
