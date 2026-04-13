# clip-auto
YouTubeの動画を自動で切り抜き、縦型ショート動画として非公開アップロードするシステム。

---

## 必要な環境
- Mac（M1/M2/M3/M4）
- Python 3.11（※3.14は非対応）
- ffmpeg
- Chrome（YouTubeのCookieを使うため）

---

## セットアップ手順

### Step 1. リポジトリをクローン
```bash
git clone https://github.com/torutorukun1029-art/clip-auto.git
cd clip-auto
```

### Step 2. Python 3.11をインストール
```bash
brew install python@3.11
/opt/homebrew/bin/python3.11 --version
# Python 3.11.x と表示されればOK
```

### Step 3. ffmpegをインストール
```bash
brew install ffmpeg
```

### Step 4. 仮想環境を作成
```bash
/opt/homebrew/bin/python3.11 -m venv clip_env
source clip_env/bin/activate
pip install -r requirements.txt
```

### Step 5. APIキーを設定
`.env`ファイルをルートに作成して以下を記入：
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

**OpenAI APIキー：** https://platform.openai.com → API keys → Create new secret key

**Anthropic APIキー：** https://console.anthropic.com → API Keys → Create Key

### Step 6. YouTube認証のセットアップ（一番難しいステップ）

**6-1. Google Cloud Consoleでプロジェクト作成**
1. https://console.cloud.google.com にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」→「YouTube Data API v3」を有効化

**6-2. OAuth認証情報を作成**
1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
2. アプリケーションの種類：「デスクトップアプリ」
3. JSONをダウンロードして`client_secret.json`という名前でルートに保存

**6-3. テストユーザーを追加**
1. 「APIとサービス」→「OAuth同意画面」→「対象」
2. 「テストユーザー」に自分のGmailアドレスを追加

**6-4. 初回認証**
```bash
source clip_env/bin/activate
export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d'=' -f2)
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d'=' -f2)
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"
python clip_auto.py
```
→ ブラウザが開くのでGoogleアカウントでログインして認証完了

### Step 7. 処理対象チャンネルのURLを設定
```bash
echo "[]" > processed.json
python fetch_channel_videos.py
```

---

## 実行方法

```bash
source clip_env/bin/activate
export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d'=' -f2)
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d'=' -f2)
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:$PATH"

python clip_auto.py                                      # 未処理を順番に自動処理
python clip_auto.py 株本                                 # キーワードで動画を検索
python clip_auto.py 'https://youtube.com/watch?v=xxxxx' # URLで直接指定
```

---

## 自動実行（毎日12時）
```bash
crontab -e
# 以下を追加
0 12 * * * ~/clip-auto/run_clip.sh
```
※Macの電源が入っていることが条件

---

## トラブルシューティング

**YouTube認証トークンが切れた場合**
```bash
rm token.json
python clip_auto.py
```

**Bot判定でダウンロード失敗する場合**
ChromeでYouTubeにログインした状態で実行してください。

**JSONパースエラーが出た場合**
自動でスキップされるので無視してOK。

---

## コスト（10分動画1本あたり）

| ツール | コスト |
|--------|--------|
| Whisper API | 約9円 |
| Claude API | 約3〜5円 |
| YouTube Data API | 無料 |
| **合計** | **約14円/本** |
