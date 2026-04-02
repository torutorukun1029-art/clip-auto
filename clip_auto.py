import os, subprocess, json
import yt_dlp
from openai import OpenAI
import anthropic
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

YOUTUBE_URL = "https://www.youtube.com/watch?v=BI-1UVWO9LA"
CLIP_DURATION = 60
NUM_CLIPS = 2
OUTPUT_DIR = "./clips"

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_video(url):
    print("動画をダウンロード中...")
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "outtmpl": f"{OUTPUT_DIR}/original.%(ext)s",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "動画")
    return f"{OUTPUT_DIR}/original.mp4", title

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

【伸びる切り抜きの優先基準】
以下の要素が3つ以上含まれる箇所を優先してください：
□ 具体的な金額・数字が出る（「〇〇万円」「年収〇〇」等）
□ 感情が動く瞬間（怒り・驚き・涙・ブチギレ）
□ 「実は」「本当は」「ぶっちゃけ」等の暴露ワード
□ 特定人物にフォーカスした話
□ 失敗談・やらかし・業界の裏話

【タイトルの型】
① [人名]が[感情動詞]！[具体的状況]
② [数字]万円の[対象]を[動詞]方法
③ 絶対に[ネガティブ動詞]たくない[対象]の特徴
④ 本当にあった[ネガティブ][名詞]の話

【避けること】
- ノウハウ・How to系だけの内容（人間ドラマがないもの）
- タイトルが説明的すぎるもの
- 感情の動きがないシーン

JSONのみで返してください：
{{"clips": [{{"start": 開始秒数, "end": 終了秒数, "title": "タイトル30文字以内", "reason": "選んだ理由（どの基準に該当するか）"}}]}}"""

    response = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

def cut_clips(video_path, clips):
    print("動画をカット中...")
    clip_paths = []
    for i, clip in enumerate(clips["clips"]):
        out = f"{OUTPUT_DIR}/clip_{i+1}.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(clip["start"]),
            "-to", str(clip["end"]),
            "-i", video_path,
            "-c:v", "libx264", "-c:a", "aac", out
        ], check=True, capture_output=True)
        clip_paths.append((out, clip["title"]))
        print(f"  clip_{i+1}.mp4 -> {clip['title']}")
    return clip_paths

def get_youtube_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json",
            scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
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
                "channelId": "UCpyLspcoiv6-m1-lfhF6dNw",
                "categoryId": "22"
            },
            "status": {"privacyStatus": "private"}
        },
        media_body=MediaFileUpload(clip_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    print(f"  完了: https://youtube.com/watch?v={response['id']}")
    return response["id"]

def main():
    video_path, original_title = download_video(YOUTUBE_URL)
    print(f"元動画: {original_title}")
    transcript = transcribe(video_path)
    clips = find_clips(transcript, NUM_CLIPS, CLIP_DURATION)
    print("\n選ばれた箇所:")
    for i, c in enumerate(clips["clips"]):
        print(f"  {i+1}. {c['title']} ({c['start']}s-{c['end']}s)")
        print(f"     {c['reason']}")
    clip_paths = cut_clips(video_path, clips)
    youtube = get_youtube_service()
    for path, title in clip_paths:
        upload_clip(youtube, path, title)
    print("\n全工程完了!")

if __name__ == "__main__":
    main()
