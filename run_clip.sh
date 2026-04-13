#!/bin/bash
cd ~/dpro_notify
source clip_env/bin/activate
export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d'=' -f2)
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d'=' -f2)
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"
python fetch_channel_videos.py && python clip_auto.py >> ~/dpro_notify/clip_log.txt 2>&1
