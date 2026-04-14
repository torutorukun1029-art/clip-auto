#!/usr/bin/env python3
"""バズり広告→リライト→感情の流れ→段落整形→週次シートに追記"""
import json, os, subprocess, importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT  = "yotayamaguchi2@gmail.com"

HEADER = ["会社名", "競合広告原文", "トルトル式全文リライト", "判断",
          "メモ", "動画URL", "ターゲット状態", "感情の流れ", "再生数"]

COLUMN_WIDTHS = [
    ("A:A", 180),  # 会社名
    ("B:B", 480),  # 競合広告原文
    ("C:C", 480),  # トルトル式全文リライト
    ("D:D", 80),   # 判断
    ("E:E", 180),  # メモ
    ("F:F", 240),  # 動画URL
    ("G:G", 140),  # ターゲット状態
    ("H:H", 480),  # 感情の流れ
    ("I:I", 90),   # 再生数
]


def _load(filename, modname):
    path = Path(__file__).parent / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_rewrite_mod = _load("03_rewrite.py", "rewrite_mod")
_emotion_mod = _load("04_add_emotion.py", "emotion_mod")
_align_mod   = _load("05_align_paragraphs.py", "align_mod")

rewrite          = _rewrite_mod.rewrite
get_emotion_flow = _emotion_mod.get_emotion_flow
split_paragraphs = _align_mod.split_paragraphs


def _gog_metadata():
    r = subprocess.run(
        ["gog", "sheets", "metadata", SHEET_ID, "-a", ACCOUNT, "-j"],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ❌ metadata error: {r.stderr.strip()}")
        return []
    meta = json.loads(r.stdout)
    return [s.get("properties", {}).get("title", "") for s in meta.get("sheets", [])]


def _gog_add_tab(name):
    r = subprocess.run(
        ["gog", "sheets", "add-tab", SHEET_ID, name, "-a", ACCOUNT],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ❌ add-tab error: {r.stderr.strip()}")
    return r.returncode == 0


def _q(tab):
    """A1記法用にシート名をシングルクォートで囲む（/などの特殊文字対応）"""
    return "'" + tab.replace("'", "''") + "'"


def _gog_append(tab, rows):
    vj = json.dumps(rows, ensure_ascii=False)
    r = subprocess.run(
        ["gog", "sheets", "append", SHEET_ID, f"{_q(tab)}!A:I",
         "--values-json", vj, "-a", ACCOUNT],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ❌ append error: {r.stderr.strip()}")
    return r.returncode == 0


def _apply_formatting(tab):
    """列幅と折り返し設定を適用"""
    for cols, width in COLUMN_WIDTHS:
        r = subprocess.run(
            ["gog", "sheets", "resize-columns", SHEET_ID, f"{_q(tab)}!{cols}",
             "--width", str(width), "-a", ACCOUNT],
            capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print(f"  ⚠️ resize {cols}: {r.stderr.strip()}")
    r = subprocess.run(
        ["gog", "sheets", "format", SHEET_ID, f"{_q(tab)}!A:I",
         "--format-json", '{"wrapStrategy":"WRAP","verticalAlignment":"TOP"}',
         "--format-fields",
         "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment",
         "-a", ACCOUNT],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ⚠️ format: {r.stderr.strip()}")


def ensure_weekly_sheet():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    name = f"{monday.year}_{monday.month}/{monday.day}~"
    tabs = _gog_metadata()
    if name not in tabs:
        print(f"📊 シート「{name}」を新規作成中...")
        if _gog_add_tab(name):
            _gog_append(name, [HEADER])
            _apply_formatting(name)
            print(f"✅ シート「{name}」作成完了")
    return name


def _pc(v):
    if not v:
        return 0
    try:
        return int(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return 0


def process_buzz_ads(buzz_ads, dry_run=False):
    """バズり広告に対してリライト→感情→段落整形を実行し、週次シートに追記"""
    if not buzz_ads:
        return

    tab = ensure_weekly_sheet()
    rows = []

    for idx, ad in enumerate(buzz_ads, 1):
        company = ad.get("product_name") or ad.get("advertiser_name") or ""
        b_text  = (ad.get("ad_all_sentence") or "").strip()
        url     = ad.get("production_share_url") or ad.get("production_url") or ""
        play    = _pc(ad.get("play_count"))
        label   = ad.get("label", "")

        if not b_text:
            print(f"\n  ⏭️ [{idx}/{len(buzz_ads)}] {company}: 文字起こしなし、スキップ")
            continue

        print(f"\n🔥 [{idx}/{len(buzz_ads)}] {company} ({len(b_text)}文字)")

        print(f"  ✏️ リライト中...")
        c_text = rewrite(b_text)
        if c_text:
            print(f"  → リライト{len(c_text)}文字")
        else:
            print(f"  → リライト失敗")

        print(f"  🧠 感情の流れ生成中...")
        emotion = get_emotion_flow(b_text)

        if c_text:
            print(f"  📐 段落整形中...")
            new_b, new_c = split_paragraphs(b_text, c_text)
            if new_b and new_c:
                b_text, c_text = new_b, new_c

        rows.append([company, b_text, c_text, "", "", url, label, emotion, str(play)])

    if not rows:
        print("\n✅ 追記対象なし")
        return

    if dry_run:
        print(f"\n[DRY-RUN] 「{tab}」に{len(rows)}件追記予定")
        return

    if _gog_append(tab, rows):
        print(f"\n📊 「{tab}」に{len(rows)}件追記完了")
        print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--ensure-sheet":
        print(ensure_weekly_sheet())
