#!/usr/bin/env python3
"""
話者追跡クロップスクリプト
- 宮地さんの声紋と照合して自動識別
- 話している人の顔にクロップして縦型動画を生成
"""
import cv2
import numpy as np
import subprocess
import soundfile as sf
import torch
from scipy.spatial.distance import cosine
from pyannote.audio import Pipeline, Model, Inference
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os

HF_TOKEN = "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"
MIYAJI_EMBEDDING_PATH = "/Users/yotayamaguchi/dpro_notify/miyaji_embedding.npy"

def get_speaker_timeline(wav_path):
    """話者分離して宮地さんがどちらかを返す"""
    miyaji_emb = np.load(MIYAJI_EMBEDDING_PATH)
    data, sr = sf.read(wav_path)
    waveform = torch.tensor(data).unsqueeze(0).float()
    
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=HF_TOKEN)
    result = pipeline({"waveform": waveform, "sample_rate": sr}, min_speakers=2, max_speakers=2)
    
    # 宮地さんのSPEAKER番号を特定
    sims = [1 - cosine(miyaji_emb, emb) for emb in result.speaker_embeddings]
    miyaji_id = f"SPEAKER_0{np.argmax(sims)}"
    print(f"宮地さん = {miyaji_id} (類似度: {max(sims):.3f})")
    
    # タイムライン生成
    timeline = []
    for turn, _, speaker in result.speaker_diarization.itertracks(yield_label=True):
        timeline.append({
            "start": turn.start,
            "end": turn.end,
            "is_miyaji": speaker == miyaji_id
        })
    return timeline

def get_face_positions(video_path):
    """顔位置を時系列で取得"""
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
        "/tmp/face_detector.tflite"
    )
    base_options = python.BaseOptions(model_asset_path="/tmp/face_detector.tflite")
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=base_options)
    )
    
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    face_timeline = {}
    # 2秒ごとにサンプリング
    for frame_idx in range(0, total_frames, int(fps * 2)):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = video.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)
        sec = frame_idx / fps
        if result.detections:
            faces = sorted([
                (det.bounding_box.origin_x + det.bounding_box.width / 2) / width
                for det in result.detections
            ])
            face_timeline[sec] = faces
    
    video.release()
    return face_timeline, fps, width

def get_crop_x(sec, is_miyaji, face_timeline, width):
    """指定秒数での話者のクロップX座標を返す"""
    # 最近傍の顔データを取得
    times = sorted(face_timeline.keys())
    nearest = min(times, key=lambda t: abs(t - sec))
    faces = face_timeline.get(nearest, [0.5])
    
    if len(faces) >= 2:
        # 2人いる場合：左(0)か右(1)か
        # 宮地さんは左右どちらかを平均で判定
        if is_miyaji:
            # 宮地さんの平均位置が左か右かで決定
            target_x = faces[0] if faces[0] < 0.5 else faces[1]
        else:
            target_x = faces[1] if faces[0] < 0.5 else faces[0]
    else:
        target_x = faces[0]
    
    # クロップ中心X（ピクセル）
    crop_w = int(width * 9/16) if width > width * 9/16 else width
    center_x = int(target_x * width)
    x = max(0, min(center_x - crop_w // 2, width - crop_w))
    return x, crop_w

def create_speaker_crop_video(video_path, wav_path, output_path):
    """話者追跡クロップ動画を生成"""
    print("話者分離中...")
    timeline = get_speaker_timeline(wav_path)
    
    print("顔位置検出中...")
    face_timeline, fps, width = get_face_positions(video_path)
    
    # 宮地さんの平均位置を計算して左右を確定
    miyaji_times = [seg["start"] for seg in timeline if seg["is_miyaji"]]
    miyaji_x_positions = []
    for t in miyaji_times[:10]:
        times = sorted(face_timeline.keys())
        nearest = min(times, key=lambda k: abs(k - t))
        faces = face_timeline.get(nearest, [])
        if faces:
            miyaji_x_positions.append(faces[0])
    
    miyaji_is_left = np.mean(miyaji_x_positions) < 0.5 if miyaji_x_positions else True
    print(f"宮地さんは{'左' if miyaji_is_left else '右'}側")
    
    # ffmpegフィルターを生成
    height = 1080
    crop_w = int(height * 9 / 16)  # 縦型のクロップ幅
    
    # タイムライン毎にクロップ位置を設定
    filter_parts = []
    for i, seg in enumerate(timeline):
        faces_at_start = face_timeline.get(
            min(face_timeline.keys(), key=lambda t: abs(t - seg["start"])), [0.5]
        )
        if len(faces_at_start) >= 2:
            if seg["is_miyaji"]:
                target_x = faces_at_start[0] if miyaji_is_left else faces_at_start[1]
            else:
                target_x = faces_at_start[1] if miyaji_is_left else faces_at_start[0]
        else:
            target_x = faces_at_start[0]
        
        crop_x = max(0, min(int(target_x * width) - crop_w // 2, width - crop_w))
        filter_parts.append(f"between(t,{seg['start']:.2f},{seg['end']:.2f})*{crop_x}")
    
    # x座標の動的計算式
    x_expr = "+".join(filter_parts) if filter_parts else "0"
    
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"crop={crop_w}:{height}:'({x_expr})':0,scale=1080:1920",
        "-c:v", "libx264", "-c:a", "aac", output_path
    ]
    print("動画生成中...")
    subprocess.run(cmd, check=True)
    print(f"完了: {output_path}")

if __name__ == "__main__":
    create_speaker_crop_video(
        "/Users/yotayamaguchi/dpro_notify/clips/original.mp4",
        "/tmp/test_audio.wav",
        "/tmp/speaker_crop_test.mp4"
    )
