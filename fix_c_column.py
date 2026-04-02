#!/usr/bin/env python3
"""C列のCLAUDE.mdルール違反箇所を検出・修正する"""
import json, subprocess, re

SHEET_ID = "1Rw4Ywsk7LIwmDEhtPdmNwoMW_qID9doH45URV7Klttk"
ACCOUNT = "yotayamaguchi2@gmail.com"

# チェックリスト: (検索パターン, 置換先, 説明)
REPLACEMENTS = [
    # 費用表記
    ("掲載前課金なし", "追加費用なし", "掲載前課金なし→追加費用なし"),
    ("初期費用0円", "追加費用なし・月10万円〜の完全定額制", "初期費用0円→定額制表記"),
    ("制作費0円", "追加費用なし・月10万円〜の完全定額制", "制作費0円→定額制表記"),
    ("採用代行費0円", "追加費用なし・月10万円〜の完全定額制", "採用代行費0円→定額制表記"),
    ("採用施策費0円", "追加費用なし・月10万円〜の完全定額制", "採用施策費0円→定額制表記"),
    # チーム表現
    ("専属の元リクルート担当", "元リクルート・Indeed・大手人材企業のマネージャークラスで構成された専属チームが伴走", "専属の元リクルート担当→チーム表記"),
    # 契約期間
    ("最低契約期間なし", "最低契約期間は6ヶ月", "最低契約期間なし→6ヶ月"),
    ("最低契約期間3ヶ月", "最低契約期間は6ヶ月", "最低契約期間3ヶ月→6ヶ月"),
    ("最低契約期間は3ヶ月", "最低契約期間は6ヶ月", "最低契約期間3ヶ月→6ヶ月"),
    # 枠数制限
    ("月100社限定", "受注枠には限りがあります", "月100社限定→枠数表記"),
    ("月20社限定", "受注枠には限りがあります", "月20社限定→枠数表記"),
    ("毎月100社限定", "担当できるリソースに限りがあるため枠数限定", "毎月100社限定→枠数表記"),
    ("毎月20社限定", "担当できるリソースに限りがあるため枠数限定", "毎月20社限定→枠数表記"),
    # 費用表記（月額）
    ("月額10万円", "月10万円〜", "月額10万円→月10万円〜"),
    # サービス表現
    ("トルトルくんを使って応募してくれる人は", "トルトルくんを導入してから応募の質が上がって", "求職者視点→企業視点"),
    ("トルトルくんを使って応募してくれる", "トルトルくんを導入してから応募の質が上がった", "求職者視点→企業視点"),
    # SNS→推奨媒体
    ("SNSで採用", "Indeedやエアワークで採用", "SNS採用→推奨媒体"),
    # 無料採用シミュレーション
    ("無料採用シミュレーション", "無料採用相談", "シミュレーション→相談"),
    # 修正依頼
    ("修正依頼", "改善提案", "修正依頼→改善提案"),
    # 1日3300円（カンマなし）
    ("1日3300円", "1日3,300円〜", "カンマ・〜追加"),
    # いつでも解約OK
    ("いつでも解約OK", "成果が出ない場合はいつでもストップOK", "解約表現修正"),
    ("いつでも解約できます", "成果が出ない場合はいつでもストップできます", "解約表現修正"),
]

# 正規表現パターンのチェック
REGEX_REPLACEMENTS = [
    # \nリテラル文字列が残っている場合（実際の改行ではなくバックスラッシュn）
    (r'(?<!\\)\\n', '\n', "\\n→改行変換"),
    # 月額10万（〜なし）→月10万円〜
    (r'月額(\d+)万円(?!〜)', r'月\1万円〜', "月額→月〜"),
]


def gog_get(range_str):
    cmd = ["gog", "sheets", "get", SHEET_ID, range_str, "--json", "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr}")
        return None
    return json.loads(r.stdout)


def gog_update(range_str, values):
    vj = json.dumps(values, ensure_ascii=False)
    cmd = ["gog", "sheets", "update", SHEET_ID, range_str, "--values-json", vj, "--account", ACCOUNT]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def check_and_fix(text):
    """ルール違反を検出・修正。変更箇所のリストと修正後テキストを返す"""
    fixes = []
    new_text = text

    # 単純文字列置換
    for search, replace, desc in REPLACEMENTS:
        if search in new_text:
            new_text = new_text.replace(search, replace)
            fixes.append(desc)

    # 正規表現置換
    for pattern, replace, desc in REGEX_REPLACEMENTS:
        if re.search(pattern, new_text):
            new_text = re.sub(pattern, replace, new_text)
            fixes.append(desc)

    return new_text, fixes


def main():
    print("📊 B2:C30を取得中...")
    data = gog_get("シート1!B2:C30")
    if not data:
        print("❌ 取得失敗")
        return

    values = data.get("values", data) if isinstance(data, dict) else data

    total_rows_fixed = 0
    total_fixes = 0

    for i, row in enumerate(values):
        row_num = i + 2  # 2行目から
        c_val = row[1] if len(row) > 1 else ""  # B2:C30なのでindex 1がC列

        if not c_val or len(c_val) < 50:
            continue

        new_c, fixes = check_and_fix(c_val)

        if fixes:
            print(f"\n行{row_num}: {len(fixes)}箇所修正")
            for f in fixes:
                print(f"  ・{f}")

            if gog_update(f"シート1!C{row_num}", [[new_c]]):
                print(f"  → 更新OK")
                total_rows_fixed += 1
                total_fixes += len(fixes)
            else:
                print(f"  → 更新失敗")

    print(f"\n{'='*40}")
    print(f"✅ 修正完了: {total_rows_fixed}行 / {total_fixes}箇所")


if __name__ == "__main__":
    main()
