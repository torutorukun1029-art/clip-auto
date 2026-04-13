import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

CHANNEL_ID = "UCpyLspcoiv6-m1-lfhF6dNw"

def get_youtube():
    creds = Credentials.from_authorized_user_file("token.json")
    return build("youtube", "v3", credentials=creds)

def get_all_videos(youtube, channel_id):
    print("動画一覧を取得中...")
    videos = []
    page_token = None
    while True:
        res = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            maxResults=50,
            order="date",
            pageToken=page_token
        ).execute()
        for item in res["items"]:
            url = f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            title = item["snippet"]["title"]
            videos.append({"url": url, "title": title})
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return videos

def main():
    youtube = get_youtube()
    videos = get_all_videos(youtube, CHANNEL_ID)
    print(f"全{len(videos)}本取得完了")

    processed = []
    try:
        with open("processed.json") as f:
            processed = json.load(f)
    except:
        pass

    urls = [v["url"] for v in videos]
    unprocessed = [u for u in urls if u not in processed]
    print(f"未処理: {len(unprocessed)}本")

    with open("channel_urls.json", "w") as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)
    print("channel_urls.jsonに保存しました")

    for v in videos[:10]:
        print(f"  {v['title'][:40]}")

if __name__ == "__main__":
    main()
