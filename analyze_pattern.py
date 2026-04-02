import json
import anthropic

client = anthropic.Anthropic()

with open("shorts_data.json") as f:
    shorts = json.load(f)

top30 = shorts[:30]
data_text = "\n".join([
    f"{i+1}. {v['views']:,}回 | {v['title']}"
    for i, v in enumerate(top30)
])

prompt = f"""以下はWebマーケティング会社StockSunのYouTubeショート動画の再生数トップ30です。

{data_text}

このデータから以下を分析してください：

1. 伸びている動画の共通パターン（タイトルの型・テーマの傾向）
2. 再生数が高い順にカテゴリ分類
3. 切り抜き動画を作る際に「どんな内容を切り抜けば伸びるか」の具体的な指針
4. 避けるべきテーマや切り口

ビジネス系YouTubeの切り抜き担当者として実践的に使える分析をしてください。"""

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)

print(response.content[0].text)

with open("pattern_analysis.txt", "w") as f:
    f.write(response.content[0].text)
print("\n分析結果をpattern_analysis.txtに保存しました")
