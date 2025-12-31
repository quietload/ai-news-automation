# 📰 AI News Automation Pipeline

Automatically generates and uploads YouTube news content using AI.

## 📋 Overview

| Content | Schedule | Format | Duration |
|---------|----------|--------|----------|
| **Daily Shorts** | Mon-Fri 18:00 KST | Vertical (1080x1920) | ~60s |
| **Weekly Video** | Sat 18:00 KST | Horizontal (1920x1080) | ~3min |
| **Sunday** | Rest day 😴 | - | - |

## 🚀 Features

- ✅ News fetching from NewsData.io (14 categories)
- ✅ AI image generation (GPT Image 1.5)
- ✅ Text-to-speech narration (OpenAI TTS - Nova voice)
- ✅ Multi-language subtitles (EN, KO, JA, ZH, ES)
- ✅ Synchronized audio-image timing
- ✅ Auto-generated thumbnails
- ✅ YouTube scheduled upload
- ✅ Duplicate news prevention

## 📁 File Structure

```
news/
├── news_dual.py           # Main generator
├── run_daily_shorts.py    # Daily shorts runner
├── run_weekly_video.py    # Weekly video runner
├── upload_video.py        # YouTube uploader
├── create_ending_images.py # Ending image generator
├── n8n_workflow.json      # Automation schedule
├── .env                   # API keys (create from .env.example)
├── .env.example           # API keys template
├── used_news.json         # Duplicate tracking
├── assets/
│   ├── ending_shorts.png  # Shorts ending image
│   └── ending_video.png   # Video ending image
├── output/                # Generated content
└── logs/                  # Execution logs
```

## ⚙️ Setup

### 1. Install Dependencies

```bash
pip install requests python-dotenv pillow
```

### 2. Install FFmpeg

```bash
# Windows (with Chocolatey)
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

### 3. Configure API Keys

Create `.env` file:

```env
NEWSDATA_API_KEY=pub_xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

### 4. YouTube OAuth Setup

1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials
4. Download as `client_secrets.json`
5. Run once to authorize:
   ```bash
   python upload_video.py --file test.mp4 --title "Test"
   ```

### 5. Create Ending Images

```bash
python create_ending_images.py
```

## 🎮 Usage

### Manual Generation

```bash
# Daily Shorts (8 news)
python news_dual.py --count 8 --shorts-only

# Weekly Video (13 news by category)
python news_dual.py --count 13 --video-only --by-category

# Both
python news_dual.py --count 8
```

### Automated (with n8n)

1. Import `n8n_workflow.json` into n8n
2. Activate the workflow
3. Keep n8n server running

```bash
# Start n8n
npx n8n
# or
docker start n8n
```

## 📅 Schedule (n8n)

| Day | Time (KST) | Content |
|-----|------------|---------|
| Mon | 17:00 → 18:00 | Shorts |
| Tue | 17:00 → 18:00 | Shorts |
| Wed | 17:00 → 18:00 | Shorts |
| Thu | 17:00 → 18:00 | Shorts |
| Fri | 17:00 → 18:00 | Shorts |
| **Sat** | 17:00 → 18:00 | **Weekly Video** |
| Sun | - | Rest |

*17:00 = Generation starts, 18:00 = YouTube publish time*

## 💰 Monthly Cost Estimate

| Item | Calculation | Cost |
|------|-------------|------|
| Daily Shorts | $0.59 × 22 days | $12.98 |
| Weekly Video | $1.40 × 4 weeks | $5.60 |
| **Total** | | **~$18.58** |

*Based on GPT Image 1.5 medium quality pricing*

## 🔧 Configuration

### News Categories (14)

```
world, business, technology, science, health,
sports, entertainment, environment, politics,
crime, education, food, lifestyle, tourism
```

### Subtitle Languages

| Code | Language |
|------|----------|
| en | English |
| ko | Korean |
| ja | Japanese |
| zh | Chinese |
| es | Spanish |

## 📝 Output Files

Each generation creates:

```
output/
├── {timestamp}_Shorts.mp4
├── {timestamp}_shorts_thumbnail.png
├── {timestamp}_shorts_subtitles_en.srt
├── {timestamp}_shorts_subtitles_ko.srt
├── {timestamp}_shorts_subtitles_ja.srt
├── {timestamp}_shorts_subtitles_zh.srt
├── {timestamp}_shorts_subtitles_es.srt
├── {timestamp}_shorts_script.txt
├── {timestamp}_shorts_audio.mp3
├── {timestamp}_shorts_*.png (images)
└── {timestamp}_summary.json
```

## 🐛 Troubleshooting

### API Errors

- **NewsData 422**: Free plan limit (size=10 max). Already handled with multi-category fetching.
- **OpenAI Policy Violation**: Content blocked. Automatically tries next news.

### FFmpeg Not Found

```bash
# Add to PATH or install via package manager
choco install ffmpeg
```

### YouTube Upload Limit

- New channels: 15 videos/day
- API quota: 10,000 units/day
- Wait 24 hours or use different Google account

## 📄 License

MIT License
