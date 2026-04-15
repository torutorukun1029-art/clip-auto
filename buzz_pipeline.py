#!/usr/bin/env python3
"""バズり広告→リライト→感情の流れ→段落整形→週次シートに追記"""
import json, os, subprocess, importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv(Path(__file__).parent / ".env")

_anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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


TARGET_STATE_PROMPT = """以下の競合広告を見てトルトルくん（採用代行サービス）に問い合わせる可能性がある「視聴者の状態」を1文で言語化してください。

ルール：
・1文・20〜40文字
・形式：「[抱えている悩み・状況]、[属性]」
・属性は「中小企業の経営者」または「人事担当者」のいずれかにする
・採用文脈に置き換える（元広告がAI・フリーランス・ダイエット等でも、採用に困っている経営者・人事の状態として書く）
・抽象的な感情論ではなく、具体的な状況・課題を入れる
・装飾記号（鉤括弧・絵文字・**）は付けない

出力例：
求める人材を確保できず、採用戦略に行き詰っている中小企業の経営者
高額な求人広告に投資するも、応募が全く来ない人事担当者
採用広告費の負担が大きく、効果が見えない中小企業の経営者

---
広告：
{ad_text}

ターゲット状態を1文だけ出力してください。前置き・補足・改行は不要。"""


def get_target_state(ad_text):
    if not ad_text or len(ad_text) < 10:
        return ""
    try:
        msg = _anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": TARGET_STATE_PROMPT.format(
                ad_text=ad_text[:1500])}])
        text = msg.content[0].text.strip()
        # 前後の鉤括弧や記号を除去
        text = text.strip("「」\"'`* \n")
        return text
    except Exception as e:
        print(f"  ⚠️ target_state error: {e}")
        return ""


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
        capture_output=True, text=True, timeout=120)
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


def _get_existing_urls(tab):
    """シートのF列（動画URL）から既存URLを取得"""
    r = subprocess.run(
        ["gog", "sheets", "get", SHEET_ID, f"{_q(tab)}!F:F",
         "-a", ACCOUNT, "-j"],
        capture_output=True, text=True, timeout=30)
    urls = set()
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            for row in data.get("values", [])[1:]:
                if row and row[0]:
                    urls.add(row[0])
        except (json.JSONDecodeError, IndexError):
            pass
    return urls


def _pc(v):
    if not v:
        return 0
    try:
        return int(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return 0


def _process_ads(ads, prefix, dry_run=False):
    """広告に対してリライト→感情→段落整形を実行し、週次シートに追記（URL重複チェック付き）"""
    if not ads:
        return

    tab = ensure_weekly_sheet()
    existing_urls = _get_existing_urls(tab)

    # URL重複を先にフィルタ
    to_process = []
    for ad in ads:
        url = ad.get("production_share_url") or ad.get("production_url") or ""
        b_text = (ad.get("ad_all_sentence") or "").strip()
        if url in existing_urls:
            continue
        if not b_text:
            continue
        to_process.append(ad)

    skipped = len(ads) - len(to_process)
    if skipped:
        print(f"  ⏭️ スキップ: {skipped}件（URL重複 or 文字起こしなし）")

    if not to_process:
        print("\n✅ 追記対象なし")
        return

    print(f"\n📝 リライト対象: {len(to_process)}件")

    if dry_run:
        print(f"[DRY-RUN] 「{tab}」に{len(to_process)}件追記予定")
        return

    written = 0
    BATCH_SIZE = 5
    batch = []

    for idx, ad in enumerate(to_process, 1):
        company = ad.get("label") or ad.get("product_name") or ad.get("advertiser_name") or ""
        b_text  = (ad.get("ad_all_sentence") or "").strip()
        url     = ad.get("production_share_url") or ad.get("production_url") or ""
        play    = _pc(ad.get("play_count"))

        print(f"\n{prefix} [{idx}/{len(to_process)}] {company} ({len(b_text)}文字)")

        try:
            print(f"  ✏️ リライト中...")
            c_text = rewrite(b_text)
            if c_text:
                print(f"  → リライト{len(c_text)}文字")
            else:
                print(f"  → リライト失敗")

            print(f"  🎯 ターゲット状態生成中...")
            target_state = get_target_state(b_text)
            if target_state:
                print(f"  → {target_state}")

            print(f"  🧠 感情の流れ生成中...")
            emotion = get_emotion_flow(b_text)

            if c_text:
                print(f"  📐 段落整形中...")
                new_b, new_c = split_paragraphs(b_text, c_text)
                if new_b and new_c:
                    b_text, c_text = new_b, new_c

            batch.append([company, b_text, c_text or "", "", "", url, target_state, emotion, str(play)])

        except Exception as e:
            print(f"  ❌ 処理エラー（スキップ）: {e}")
            # エラーでも原文だけは書き込む
            batch.append([company, b_text, "", "", "", url, "", "", str(play)])

        # バッチサイズに達したらスプシに書き込み（途中エラーで全件失わない）
        if len(batch) >= BATCH_SIZE or idx == len(to_process):
            if _gog_append(tab, batch):
                written += len(batch)
                print(f"  💾 {written}/{len(to_process)}件書き込み済み")
            else:
                print(f"  ❌ バッチ書き込み失敗（{len(batch)}件）")
            batch = []

    print(f"\n📊 「{tab}」に{written}件追記完了")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


def process_buzz_ads(buzz_ads, dry_run=False):
    """バズり広告のパイプライン"""
    _process_ads(buzz_ads, "🔥", dry_run)


def process_new_ads(new_ads, dry_run=False):
    """新着広告のパイプライン"""
    _process_ads(new_ads, "🆕", dry_run)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--ensure-sheet":
        print(ensure_weekly_sheet())
