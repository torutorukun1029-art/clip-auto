import os, subprocess, json
import yt_dlp
from openai import OpenAI
import anthropic
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

import json as _json
try:
    with open('channel_urls.json') as _f:
        YOUTUBE_URLS = _json.load(_f)
except:
    YOUTUBE_URLS = ["https://www.youtube.com/watch?v=BI-1UVWO9LA"]
PROCESSED_FILE = "processed.json"
CLIP_DURATION = 60
NUM_CLIPS = 2
OUTPUT_DIR = "./clips"

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return json.load(f)
    return []

def save_processed(url):
    processed = load_processed()
    processed.append(url)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

def download_video(url):
    print("動画をダウンロード中...")
    import glob
    for old_file in glob.glob("./clips/original.*"):
        os.remove(old_file)
    out = f"{OUTPUT_DIR}/original.mp4"
    subprocess.run([
        "yt-dlp",
        "--remote-components", "ejs:github",
        "--cookies-from-browser", "chrome",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", out,
        url
    ], check=True)
    result = subprocess.run([
        "yt-dlp", "--get-title",
        "--cookies-from-browser", "chrome",
        url
    ], capture_output=True, text=True)
    title = result.stdout.strip() or "動画"
    return out, title

def transcribe(video_path):
    print("文字起こし中...")
    audio_path = f"{OUTPUT_DIR}/audio.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", audio_path
    ], check=True, capture_output=True)
    with open(audio_path, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            language="ja"
        )
    return result

def find_clips(transcript, num_clips, clip_duration):
    print("Claude が切り抜き箇所を選定中...")
    segments_text = "\n".join([
        f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}"
        for seg in transcript.segments
    ])
    prompt = f"""以下はYouTube動画のトランスクリプトです。

{segments_text}

この動画から切り抜きショートを{num_clips}本作ります。各クリップは約{clip_duration}秒です。

【過去の分析データ（webマーケTV・年収チャンネル）】
# StockSun YouTubeショート動画 再生数分析レポート

## 1. 伸びている動画の共通パターン

### 【タイトルの型】TOP5パターン

```
■ パターン①：数字インパクト型（最強）
「年収は3億円！」「44万円の自転車」「月給30万」
→ 具体的な金額が入ると圧倒的に強い

■ パターン②：感情爆発型
「ブチギレ」「不満爆発」「嬉し泣き」
→ 感情の振れ幅が大きいワードが刺さる

■ パターン③：ネガティブ暴露型
「本当にあった酷い〜」「最低な〜」「絶対に〜したくない」
→ 業界の闘い話・失敗談は鉄板

■ パターン④：疑問形・質問型
「〜はいくらかかるの？」「〜の違いは？」「〜とは！？」
→ 視聴者の知りたい欲求を刺激

■ パターン⑤：人物フィーチャー型
「株本が〜」「岩野と株本の〜」「金子が〜」
→ キャラクター名＋行動で興味喚起
```

---

## 2. カテゴリ別分類（再生数順）

| ランク | カテゴリ | 該当動画数 | 平均再生数 | 代表例 |
|:---:|:---|:---:|---:|:---|
| **S** | 💰金額・年収系 | 3本 | **78,000** | 年収3億、依頼費用、HP制作費用 |
| **A** | 😤感情・衝突系 | 6本 | **14,500** | ブチギレ、不満爆発、マウント |
| **B** | 👎業界暴露・失敗談 | 4本 | **15,200** | 酷い業者、最低な営業、お断り案件 |
| **C** | 🎭キャラ・エピソード系 | 8本 | **10,800** | ぼっち青笹、金子の罪、中上の過去 |
| **D** | 📚ノウハウ・How to系 | 9本 | **8,900** | SEO対策、EC売り方、コンサル術 |

### 【重要な発見】
```
ノウハ

# 年収チャンネル ショート動画分析レポート

## 1. 伸びているタイトルの型・パターン

### 【Tier S：10万回超え確定パターン】

| パターン | 具体例 | 再生数 | 構造 |
|---------|--------|--------|------|
| **本編誘導型** | ↑続きは本編で | 66万・64万 | 気になる場面で切る→本編へ |
| **ドン引き構文** | 為国の〇〇にドン引き | 25万・17万 | 人名＋異常行動＋周囲の反応 |
| **素朴な疑問型** | 大企業のおじちゃんたちって〜 | 28万 | あえてカジュアルな口語 |

### 【Tier A：5万〜15万パターン】

| パターン | 具体例 | 特徴 |
|---------|--------|------|
| **ガチ〇〇構文** | ガチギレ・ガチ説教・ガチ相談 | 「演出じゃない」感を演出 |
| **激詰め・爆発系** | 怒り爆発・激詰め | 感情のピークを予告 |
| **人物対立構文** | 田端と為国が対立 | 有名人同士のぶつかり合い |

### 【Tier B：伸びにくいパターン】

```
❌ ノウハウ系：「稼ぎたい若手が入るべき意外な企業」→ 5.4万
❌ 抽象的教訓系：「みっともない30代にならないために」→ 1.6万
❌ 自己啓発系：「短気な人が幸せになる唯一の方法」→ 0.9万
```

**→ 情報価値＜感情価値 が明確**

---

## 2. 切り抜きで狙うべきシーンの特徴

### 【最優先で狙う場面】

```
🎯 優先度1：空気が凍る瞬間
   - 植本のガチギレに「現場が凍りつく」
   - 誰かが地雷を踏んだ直後の沈黙

🎯 優先度2：周囲がドン引きする瞬間
   - 為国の異常なLINE・遊び方の暴露
 

【トルトルくんTVチャンネルの特性】
採用代行・HR系チャンネル。視聴者は採用担当者・経営者。
伸びているコンテンツの特徴：
- 速報・最新情報系（「神アップデート」「速報」）→ 業界人が食いつく
- 比較系（AvsB、どっちが採用できるか）
- 失敗・リスク系（アカBAN、やらかし事例）
- 具体的な数字系（採用単価○万円、○名採用）

【伸びる切り抜きの本質】
採用担当者・経営者が「ドキッとする」「知らなかった」「うちもやってるかも」と思う瞬間が最強。
感情より「業界の裏側・失敗・具体的数字」が刺さる。

【優先して狙うシーン】
□ 誰かがやらかしている・地雷を踏んでいる瞬間
□ 空気が凍る・周囲がドン引きするリアクション
□ ガチギレ・激詰め・説教・対立が起きている
□ 具体的な金額・年齢・属性（無職・借金・年収など）が出る
□ 「実は」「本当は」「ぶっちゃけ」等の暴露・裏話
□ 立場逆転・論破・恥をかくシーン

【切り抜き構成の型】
- 開始：問題発言・やらかしの直前から
- 終了：周囲のリアクション直後 or 感情が最高潮の瞬間

【タイトルの型】
① [人名]の[異常行動]に[周囲]がドン引き
② [人名]のガチギレに現場が凍りつく
③ [人名]と[人名]が対立「[発言の引用]」
④ [属性（年齢・職業）]の[人名]に[人名]が「[発言]」
⑤ 本当にあった[ネガティブ][名詞]の話
⑥ [数字]万円[状況]に[感情動詞]

【避けるシーン】
- 純粋なノウハウ・How to解説（人間ドラマがない）
- 抽象的な教訓・自己啓発
- 穏やかに・笑顔で終わる会話
- 感情の動きがないシーン

JSONのみで返してください：
{{"clips": [{{"start": 開始秒数, "end": 終了秒数, "title": "タイトル2行。1行目\\n2行目の形式で。合計20文字以内。例：採用費が\\n10万になった話", "reason": "選んだ理由", "hook": "視聴者が続きを見たくなる煽り文句20文字以内", "speakers": 動画に登場する人数（整数）}}]}}"""

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    def try_parse(raw):
        import re
        # コードブロック除去
        raw = re.sub(r"```json|```", "", raw).strip()
        s = raw.find("{")
        e = raw.rfind("}") + 1
        if s == -1 or e == 0:
            raise ValueError("JSON not found")
        candidate = raw[s:e]
        # 重複キーがある場合、最初のJSONオブジェクトだけ取り出す
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(candidate)
        return obj

    text = response.content[0].text
    try:
        return try_parse(text)
    except Exception:
        response2 = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt + "必ずvalidなJSONのみを返してください。マークダウン不要。"}]
        )
        text2 = response2.content[0].text
        return try_parse(text2)


def make_srt(segments, start_sec, end_sec, srt_path):
    """指定区間のセグメントをSRTファイルに変換"""
    lines = []
    idx = 1
    for seg in segments:
        if seg.end < start_sec or seg.start > end_sec:
            continue
        s = max(seg.start - start_sec, 0)
        e = min(seg.end - start_sec, end_sec - start_sec)
        def fmt(t):
            h,m = int(t//3600), int((t%3600)//60)
            s2,ms = int(t%60), int((t%1)*1000)
            return f"{h:02}:{m:02}:{s2:02},{ms:03}"
        lines.append(f"{idx}\n{fmt(s)} --> {fmt(e)}\n{seg.text.strip()}\n")
        idx += 1
    with open(srt_path, "w") as f:
        f.write("\n".join(lines))

def cut_clips_pattern_b(video_path, clips, transcript):
    """パターンB: 中央クロップ縦型（字幕なし）"""
    print("パターンB 動画をカット中...")
    clip_paths = []
    for i, clip in enumerate(clips["clips"]):
        out = f"{OUTPUT_DIR}/clip_b_{i+1}.mp4"
        title = clip["title"]
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(clip["start"]),
            "-to", str(clip["end"]),
            "-i", video_path,
            "-vf", "crop=ih*9/16:ih,scale=1080:1920",
            "-c:v", "libx264", "-c:a", "aac", out
        ], check=True, capture_output=True)
        clip_paths.append((out, title + "【縦型】"))
        print(f"  clip_b_{i+1}.mp4 -> {title}【縦型】")
    return clip_paths


def add_text_overlay(video_path, out_path, title, hook):
    from PIL import Image, ImageDraw, ImageFont
    import json as _json
    noto = "/Users/yotayamaguchi/dpro_notify/SourceHanSans-Heavy.otf"
    tmp = out_path + "_tmp.mp4"

    # 元動画のサイズをffprobeで取得
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path
    ], capture_output=True, text=True)
    probe_info = _json.loads(probe.stdout)
    vid_stream = next(s for s in probe_info["streams"] if s["codec_type"] == "video")
    src_w = int(vid_stream["width"])
    src_h = int(vid_stream["height"])

    # 縦型フレーム(1080x1920)内での動画のY位置を計算
    CANVAS_W, CANVAS_H = 1080, 1920
    fitted_h = int(CANVAS_W * src_h / src_w)
    if fitted_h > CANVAS_H:
        fitted_h = CANVAS_H
    video_top_y = (CANVAS_H - fitted_h) // 2
    video_bottom_y = video_top_y + fitted_h

    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-c:a", "aac", tmp
    ], check=True, capture_output=True)

    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    TITLE_MARGIN = 20
    MAX_TW = 880

    # タイトル分割
    if "\n" in title:
        parts = title.split("\n", 1)
        line1, line2 = parts[0], parts[1]
    else:
        line1, line2 = title, ""

    # フォントサイズ自動調整
    for size in range(70, 20, -2):
        font = ImageFont.truetype(noto, size)
        tmp_img = Image.new("RGBA", (2000, 200), (0,0,0,0))
        ImageDraw.Draw(tmp_img).text((20,20), line1, font=font, fill="white")
        bb = tmp_img.getbbox()
        tw = (bb[2]-bb[0]) if bb else 0
        if tw <= MAX_TW:
            break

    font2 = font
    if line2:
        for size2 in range(size, 20, -2):
            font2 = ImageFont.truetype(noto, size2)
            tmp_img2 = Image.new("RGBA", (2000, 200), (0,0,0,0))
            ImageDraw.Draw(tmp_img2).text((20,20), line2, font=font2, fill="white")
            bb2 = tmp_img2.getbbox()
            tw2 = (bb2[2]-bb2[0]) if bb2 else 0
            if tw2 <= MAX_TW:
                break

    LINE_H = size + 10
    PADDING = 20
    total_text_h = LINE_H if not line2 else LINE_H * 2 + 10

    # 黒帯の中央にタイトルを配置
    # 赤帯を動画の上部に直接重ねる
    rect_bottom = video_top_y - 30
    rect_top = max(0, rect_bottom - total_text_h - PADDING * 2)
    draw.rectangle([0, rect_top, CANVAS_W, rect_bottom], fill=(220, 20, 20, 245))

    text_start_y = rect_top + PADDING
    tmp_img = Image.new("RGBA", (2000, 200), (0,0,0,0))
    ImageDraw.Draw(tmp_img).text((20,20), line1, font=font, fill="white", stroke_width=3, stroke_fill="black")
    bb = tmp_img.getbbox()
    tw = (bb[2]-bb[0]) if bb else 0
    draw.text(((CANVAS_W-tw)//2, text_start_y), line1, font=font, fill="white", stroke_width=6, stroke_fill="black")

    if line2:
        tmp_img2 = Image.new("RGBA", (2000, 200), (0,0,0,0))
        ImageDraw.Draw(tmp_img2).text((20,20), line2, font=font2, fill="white", stroke_width=3, stroke_fill="black")
        bb2 = tmp_img2.getbbox()
        tw2 = (bb2[2]-bb2[0]) if bb2 else 0
        draw.text(((CANVAS_W-tw2)//2, text_start_y + LINE_H + 10), line2, font=font2, fill="white", stroke_width=6, stroke_fill="black")

    # 下部「から本編をチェック！」：動画すぐ下の黒帯中央に配置
    bottom_area_top = video_bottom_y + TITLE_MARGIN
    font_small = ImageFont.truetype(noto, 34)
    check_text = "▶  から本編をチェック！"
    tmp3 = Image.new("RGBA", (2000, 100), (0,0,0,0))
    ImageDraw.Draw(tmp3).text((20,20), check_text, font=font_small, fill="white")
    bb3 = tmp3.getbbox()
    tw3 = (bb3[2]-bb3[0]) if bb3 else 0
    check_center_y = (bottom_area_top + CANVAS_H) // 2
    draw.rectangle([0, check_center_y - 40, CANVAS_W, check_center_y + 50], fill=(0, 0, 0, 200))
    draw.text(((CANVAS_W-tw3)//2, check_center_y - 17), check_text, font=font_small, fill="#FFE800", stroke_width=4, stroke_fill="black")

    overlay_path = out_path + "_overlay.png"
    img.save(overlay_path)
    subprocess.run([
        "ffmpeg", "-y", "-i", tmp, "-i", overlay_path,
        "-filter_complex", "overlay=0:0",
        "-c:v", "libx264", "-c:a", "aac", out_path
    ], check=True, capture_output=True)
    os.remove(tmp)
    os.remove(overlay_path)

def cut_clips(video_path, clips):
    print("動画をカット中...")
    clip_paths = []
    for i, clip in enumerate(clips["clips"]):
        out = f"{OUTPUT_DIR}/clip_{i+1}.mp4"
        tmp_cut = f"{OUTPUT_DIR}/clip_{i+1}_cut.mp4"
        title = clip["title"]
        hook = clip.get("hook", "")[:10]
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(clip["start"]),
            "-to", str(clip["end"]),
            "-i", video_path,
            "-c:v", "libx264", "-c:a", "aac", tmp_cut
        ], check=True, capture_output=True)
        add_text_overlay(tmp_cut, out, title, hook)
        os.remove(tmp_cut)
        clip_paths.append((out, title))
        print(f"  clip_{i+1}.mp4 -> {title}")
    return clip_paths

def get_youtube_service():
    from google.auth.transport.requests import Request
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json",
                scopes=["https://www.googleapis.com/auth/youtube.upload",
                        "https://www.googleapis.com/auth/youtube.readonly"]
            )
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as f:
                f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_clip(youtube, clip_path, title):
    print(f"アップロード中: {title}")
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": "切り抜き動画",
                "tags": ["切り抜き", "ビジネス"],
                "categoryId": "22"
            },
            "status": {"privacyStatus": "private"}
        },
        media_body=MediaFileUpload(clip_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    print(f"  完了: https://youtube.com/watch?v={response['id']}")
    return response["id"]


def find_url_by_keyword(keyword):
    """キーワードでチャンネル動画を検索してURLを返す"""
    with open("channel_urls.json") as f:
        urls = json.load(f)
    with open("processed.json") as f:
        processed = json.load(f)

    print(f"「{keyword}」でタイトル検索中...")
    for url in urls:
        result = subprocess.run([
            "yt-dlp", "--get-title", "--no-warnings", url
        ], capture_output=True, text=True)
        title = result.stdout.strip()
        if keyword in title:
            print(f"見つかりました: {title}")
            return url
    print("該当する動画が見つかりませんでした")
    return None

def main():
    import sys

    # 引数あり：URL直接指定 or キーワード検索
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("http"):
            # URL直接指定
            target_url = arg
        else:
            # キーワードで検索
            target_url = find_url_by_keyword(arg)
            if not target_url:
                return
        urls_to_process = [target_url]
    else:
        processed = load_processed()
        urls_to_process = [u for u in YOUTUBE_URLS if u not in processed]
        if not urls_to_process:
            print("全URL処理済みです")
            return

    for url in urls_to_process:
        print(f"処理中: {url}")
        try:
            # ショート動画をスキップ
            info_result = subprocess.run([
                "yt-dlp", "--dump-json",
                "--cookies-from-browser", "chrome",
                url
            ], capture_output=True, text=True)
            if info_result.returncode == 0:
                import json as json2
                info = json2.loads(info_result.stdout)
                duration = info.get("duration", 0)
                width = info.get("width", 0)
                height = info.get("height", 0)
                if duration and duration < 180:
                    print(f"  スキップ（ショート動画: {duration}秒）")
                    save_processed(url)
                    continue
            video_path, original_title = download_video(url)
            break
        except Exception as e:
            print(f"  スキップ（ダウンロード失敗）: {e}")
            save_processed(url)
            continue
    else:
        print("処理できる動画がありませんでした")
        return
    print(f"元動画: {original_title}")
    transcript = transcribe(video_path)
    clips = find_clips(transcript, NUM_CLIPS, CLIP_DURATION)
    print("\n選ばれた箇所:")
    for i, c in enumerate(clips["clips"]):
        print(f"  {i+1}. {c['title']} ({c['start']}s-{c['end']}s)")
        print(f"     {c['reason']}")
    clip_paths = cut_clips(video_path, clips)
    # パターンB：1人動画のみ実行
    any_multi = any(c.get("speakers", 1) >= 2 for c in clips["clips"])
    if not any_multi:
        clip_paths += cut_clips_pattern_b(video_path, clips, transcript)
    else:
        print("対談動画のためパターンBをスキップ")
    youtube = get_youtube_service()
    for path, title in clip_paths:
        upload_clip(youtube, path, title)
    save_processed(url)
    print("\n全工程完了!")

if __name__ == "__main__":
    main()
