import os
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_youtube():
    creds = Credentials.from_authorized_user_file("token.json")
    return build("youtube", "v3", credentials=creds)

def get_channel_id(youtube):
    res = youtube.search().list(
        part="snippet",
        q="stocksun web マーケ",
        type="channel",
        maxResults=5
    ).execute()
    for item in res["items"]:
        print(item["snippet"]["channelTitle"], item["snippet"]["channelId"])

def main():
    youtube = get_youtube()
    print("=== チャンネルID確認 ===")
    get_channel_id(youtube)

if __name__ == "__main__":
    main()
