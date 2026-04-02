import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

CHANNEL_ID = "UCq_vpWj2ZW8doksXpxkMAnw"

def get_youtube():
    creds = Credentials.from_authorized_user_file("token.json")
    return build("youtube", "v3", credentials=creds)

def get_top_shorts(youtube, channel_id, max_results=200):
    print("ショート取得中...")
    videos = []
    page_token = None

    while len(videos) < max_results:
        res = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            videoDuration="short",
            maxResults=50,
            pageToken=page_token
        ).execute()

        video_ids = [item["id"]["videoId"] for item in res["items"]]
        stats = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids)
        ).execute()

        for item in stats["items"]:
            videos.append({
                "title": item["snippet"]["title"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "url": f"https://youtube.com/shorts/{item['id']}"
            })

        page_token = res.get("nextPageToken")
        if not page_token:
            break

    return sorted(videos, key=lambda x: x["views"], reverse=True)

def main():
    youtube = get_youtube()
    shorts = get_top_shorts(youtube, CHANNEL_ID)

    print(f"\n再生数トップ20:")
    for i, v in enumerate(shorts[:20]):
        print(f"{i+1}. {v['views']:,}回 | {v['title'][:30]}")
        print(f"   {v['url']}")

    with open("shorts_data.json", "w") as f:
        json.dump(shorts, f, ensure_ascii=False, indent=2)
    print(f"\n全{len(shorts)}本をshorts_data.jsonに保存しました")

if __name__ == "__main__":
    main()
