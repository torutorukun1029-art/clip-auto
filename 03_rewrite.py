#!/usr/bin/env python3
"""競合広告をトルトルくんスタイルでリライトするスクリプト"""
import json, os, subprocess, anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT  = "yotayamaguchi2@gmail.com"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

REWRITE_PROMPT = """【①インプット】
以下の【元の広告】をトルトルくんの広告にリライトしてください。

【②タスク】
・元の広告を1文ずつ対応させ、内容（数字・サービス名・事例）だけトルトルくんに差し替える
・文体・語尾・テンポ・段落数・改行位置は元の広告に完全に合わせる
・元がカジュアルならカジュアル、丁寧なら丁寧、体言止めなら体言止め
・感情の流れ（危機感→希望→CTA）も元の広告と同じタイミングで
・別ジャンル（AI・Web制作・スクールなど）でも採用・人材獲得の文脈に完全置き換え
・フックは「経営者が信じている採用の常識を否定する」形にする
  例：「マイナビを出せば採用できる。これ、間違いです。」「人材紹介に頼めば採用できる。これ、間違いです。」
・求人広告批判は構造的に行う：「掲載前課金制＝掲載した瞬間に広告会社の売上が確定→改善する人がいない」
・人材紹介批判：「採用1人で年収の30〜35%が手数料、100万〜200万が一発でかかる・紹介して終わり」
・「やれ/やめろ」形式の広告はこの分類で置き換える（逆転禁止）
  やれ：Indeed・エアワーク・ジョブメドレー・リファラル採用・ABテスト・スカウト大量送付・トルトルくん
  やめろ：マイナビ・リクナビ・doda・ビズリーチ・人材紹介・SNS採用・片手間採用・運まかせ採用
・C列を空白にするのは原則禁止。音声認識の誤変換・対話形式・意味不明な行でも読み取れる範囲でリライトする
・どうしても自信がない場合は文頭に（修正必要）を付けて出力すること
・B列が100文字以下の場合のみ「対応不可」と返してよい

【③トルトルくん基本情報】
・サービス：採用代行・RPO「トルトルくん」
・担当：東大法学部卒・元リクルート 宮地陸（27歳）
・料金：月10万円〜・1日3,300円〜の定額制（採用人数増えてもコスト変わらず・追加費用なし）
・内容：求人票作成・媒体選定・ABテスト・スカウト送付まで全部代行（13の採用手法からカスタマイズ）
・実績：1年で同時400社以上支援・採用単価40〜70%削減
・事例：施工管理職で初月から二級施工管理技士採用成功 / 飛び込み営業職で月50応募・3採用 / 月10万円〜で2名採用継続達成
・CTA：無料採用相談（1時間・完全無料・枠数限定）のみ。「無料採用シミュレーション」は存在しない
・やめろ側の特徴：マイナビ/リクナビ＝掲載前課金制で改善しない、doda＝コスパ悪い、ビズリーチ＝成果報酬高すぎ、人材紹介＝手数料30〜35%・定着率低い、SNS採用＝再現性ゼロ
・やれ側の特徴：Indeed＝クリック課金で費用対効果高い、エアワーク＝スカウトが安く大量送付、ジョブメドレー＝医療系に強い

【④絶対禁止リスト】
1. 「月10万円」「月10万」→必ず「月10万円〜」（〜必須）
2. 「1日3,300円」→必ず「1日3,300円〜」（〜必須・カンマ必須）
3. 「初期費用」「初期費用0円」「採用代行費0円」→「月10万円〜・追加費用なし」
4. 「SNSで採用」→批判対象。「Indeedやエアワークで採用」に変換
5. 「採用で稼ぐ」「月○万稼ぐ」→禁止（トルトルくんは採用代行を提供する側）
6. 「毎月数十社」→「同時400社以上を支援」
7. 「トルトルくんを見てくれた」→「採用の相談をしてくれた」
8. 「出向費用」「出張費用」→「追加費用」
9. 「無料採用シミュレーション」→「無料採用相談」
10. トルトルくん自身を貶す表現・やれ/やめろの分類逆転→絶対禁止

【⑤リスト形式の段落ルール（必須）】
リスト形式の台本（やれ/やめろ・比較・ステップ紹介など）は必ず以下の構成で段落を作ること：

1行目：[項目名・サービス名など]　[判定・評価・ラベル]
2行目：[補足・理由・説明]

各セットの間には必ず空行を入れる。
1行目と2行目を繋げて1行にしない。

【⑥出力前の自己チェックリスト】
□ 「月10万円〜」「1日3,300円〜」の〜が入っているか
□ 禁止表現（初期費用・採用代行費0円・SNSで採用・毎月数十社）を使っていないか
□ CTAは「無料採用相談」になっているか（シミュレーションは使わない）
□ 元の広告と段落数・行数・語尾・書き出しが一致しているか
□ やれ/やめろの分類ミス・トルトルくん自身を貶す表現はないか
□ 文字数が元の広告の±10%以内に収まっているか（足りなければ事例・説明を追加、多すぎれば削る）

---
【元の広告（{char_count}文字）】
{ad_text}
---
元の広告と同じ段落構成・感情の流れでリライトした広告文のみ出力してください。文字数は{char_count}文字の±10%以内（{min_chars}〜{max_chars}文字）に収めること。"""


def rewrite(ad_text):
    try:
        char_count = len(ad_text)
        min_chars = int(char_count * 0.9)
        max_chars = int(char_count * 1.1)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": REWRITE_PROMPT.format(
                char_count=char_count, min_chars=min_chars, max_chars=max_chars, ad_text=ad_text)}]
        )
        text = message.content[0].text.strip()
        # リライト失敗判定
        if text == "対応不可" or len(text) <= 100:
            return ""
        if "申し訳" in text or "できません" in text or "対応できません" in text:
            return ""
        return text
    except Exception as e:
        print(f"  ⚠️ OpenAI API error: {e}")
        return ""


def gog_get(range_str):
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"❌ gog get error: {result.stderr.strip()}")
        return None
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


def main():
    print("📊 スプシからデータ取得中...")
    data = gog_get("シート1!A2:H")
    if not data:
        print("❌ データなし")
        return

    values = data.get("values", data) if isinstance(data, dict) else data
    print(f"  {len(values)}行取得")

    # 再生数でソートして上位50件（B列あり・C列空）を特定
    candidates = []
    for i, row in enumerate(values):
        ad_text = row[1] if len(row) > 1 else ""
        c_val = row[2] if len(row) > 2 else ""
        play_str = row[7] if len(row) > 7 else ""
        try:
            play_count = int(str(play_str).replace(",", ""))
        except (ValueError, TypeError):
            play_count = 0
        if ad_text and len(ad_text) >= 10:
            row_num = i + 2
            candidates.append((row_num, play_count, ad_text))

    candidates.sort(key=lambda x: x[1], reverse=True)
    targets = candidates[:50]

    print(f"  上位50件: {len(targets)}件")
    if not targets:
        print("✅ 対象なし")
        return

    print(f"  再生数 {targets[0][1]:,} 〜 {targets[-1][1]:,}")

    for idx, (row_num, play_count, ad_text) in enumerate(targets):
        print(f"\n  [{idx+1}/{len(targets)}] 行{row_num} (再生数{play_count:,}, {len(ad_text)}文字)")
        result = rewrite(ad_text)
        if result:
            print(f"  → リライト{len(result)}文字")
            gog_update(f"シート1!C{row_num}", [[result]])
        else:
            print(f"  → スキップ")

    print(f"\n✅ {len(targets)}件 完了！")
    print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
