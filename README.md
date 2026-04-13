# clip-auto
YouTube動画を自動で切り抜き、非公開でアップロードするシステム。

## 必要なもの
- Mac（M1/M2/M3）
- Python 3.11以上
- ffmpeg
- 各種APIキー（下記参照）

## セットアップ

### 1. クローン
\`\`\`bash
git clone https://github.com/torutorukun1029-art/clip-auto.git
cd clip-auto
\`\`\`

### 2. 仮想環境
\`\`\`bash
python3 -m venv clip_env
source clip_env/bin/activate
pip install -r requirements.txt
\`\`\`

### 3. ffmpeg
\`\`\`bash
brew install ffmpeg
\`\`\`

### 4. APIキー
.envファイルを作成：
\`\`\`
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
\`\`\`

### 5. YouTube認証
client_secret.jsonを別途入手してルートに配置。初回実行時にブラウザでログイン。

### 6. URL設定
\`\`\`bash
echo "[]" > processed.json
python fetch_channel_videos.py
\`\`\`

## 使い方
\`\`\`bash
source clip_env/bin/activate
export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d'=' -f2)
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d'=' -f2)
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"

python clip_auto.py              # 未処理を順番に
python clip_auto.py 株本         # キーワード指定
python clip_auto.py https://...  # URL直接指定
\`\`\`

## コスト（10分動画1本）
Whisper約9円 + Claude約5円 = 合計約14円
