# 📰 AI News Automation Pipeline

Automatically generates and uploads YouTube news content using AI.

**GitHub**: https://github.com/quietload/ai-news-automation

## 📋 Overview

| Content | Schedule (KST) | Format | Duration |
|---------|----------------|--------|----------|
| **Daily Shorts (US)** | Mon-Fri 09:00 | Vertical (1080x1920) | ~60s |
| **Daily Shorts (KR)** | Mon-Fri 21:00 | Vertical (1080x1920) | ~60s |
| **Weekly Video** | Sat 22:00 | Horizontal (1920x1080) | ~4min |

## 🚀 Features

- ✅ Real-time news from 38+ RSS sources
- ✅ AI text generation (GPT-5 mini with minimal reasoning)
- ✅ AI image generation (GPT Image 1.5)
- ✅ Text-to-speech (GPT-4o mini TTS - Marin voice)
- ✅ Multi-language subtitles (EN, KO, JA, ZH, ES)
- ✅ Auto-generated thumbnails (Weekly Video)
- ✅ YouTube scheduled upload
- ✅ Duplicate news prevention
- ✅ 2x daily uploads (US + Korea prime time)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Text Generation | GPT-5 mini (reasoning_effort: minimal) |
| Image Generation | GPT Image 1.5 |
| Text-to-Speech | GPT-4o mini TTS (Marin voice) |
| Video Processing | FFmpeg |
| Automation | n8n |
| News Source | RSS Feeds (38 sources) |

## 📁 Project Structure

```
news/
├── news_dual.py                    # Main generator
├── news_rss.py                     # RSS feed fetcher
├── upload_video.py                 # YouTube uploader
│
├── # Runner Scripts (RSS - Recommended)
├── run_daily_shorts_rss_morning.py # Morning shorts (US time)
├── run_daily_shorts_rss.py         # Evening shorts (KR time)
├── run_daily_shorts_rss_now.py     # Immediate upload
├── run_weekly_video_rss.py         # Weekly video (scheduled)
├── run_weekly_video_rss_now.py     # Weekly video (immediate)
│
├── # n8n Workflows
├── n8n_daily_shorts_rss_morning_scheduled.json  # 08:00 KST
├── n8n_daily_shorts_rss_scheduled.json          # 20:00 KST
├── n8n_weekly_video_rss_scheduled.json          # Sat 21:00 KST
│
├── .env                            # API keys
├── client_secrets.json             # YouTube OAuth
├── assets/                         # Ending images
├── output/                         # Generated content
├── logs/                           # Execution logs
└── n8n_data/                       # n8n database
```

## ⚙️ Setup

### 1. Install Dependencies

```bash
pip install requests python-dotenv pillow feedparser google-auth google-auth-oauthlib google-api-python-client openai
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
# Daily Shorts (6 news)
python news_dual.py --count 6 --shorts-only --use-rss

# Weekly Video (16 news, 2 per category)
python news_dual.py --count 16 --video-only --by-category --use-rss
```

### Immediate Upload

```bash
python run_daily_shorts_rss_now.py    # Shorts
python run_weekly_video_rss_now.py    # Weekly Video
```

### Automated (n8n)

```powershell
# Start n8n
$env:N8N_USER_FOLDER = "D:\workspace\news\n8n_data"
npx n8n
```

Import workflows:
- `n8n_daily_shorts_rss_morning_scheduled.json` (US time)
- `n8n_daily_shorts_rss_scheduled.json` (Korea time)
- `n8n_weekly_video_rss_scheduled.json` (Saturday)

## 📅 Schedule

| Time (KST) | Days | Content | Target |
|------------|------|---------|--------|
| 08:00 → 09:00 | Tue-Sat | Daily Shorts (6 news) | 🇺🇸 US (Mon-Fri evening) |
| 20:00 → 21:00 | Mon-Fri | Daily Shorts (6 news) | 🇰🇷 Korea (Prime Time) |
| 21:00 → 22:00 | Sat | Weekly Video (16 news) | 🌏 Global |

*First time = Generation, Second time = YouTube publish*

## 📰 News Sources (38 RSS Feeds)

| Category | Sources |
|----------|---------|
| World | Korea Herald, Korea Times, Yonhap, Arirang, BBC, Al Jazeera, DW |
| Business | BBC, CNBC, Bloomberg, Financial Times, MarketWatch |
| Technology | BBC, TechCrunch, Ars Technica, The Verge, Wired |
| Science | BBC, Science Daily, Nature, New Scientist, Space.com |
| Health | BBC, WebMD, Medical News Today |
| Sports | BBC, ESPN, Sky Sports, Sports Illustrated |
| Entertainment | BBC, Variety, Hollywood Reporter, Entertainment Weekly |
| Environment | BBC, Guardian, Climate News, Mongabay |

## 💰 Monthly Cost Estimate

| Item | Calculation | Cost |
|------|-------------|------|
| Daily Shorts (2x) | $0.50 × 2 × 22 days | ~$22 |
| Weekly Video | $1.50 × 4 weeks | ~$6 |
| **Total** | | **~$28** |

*Based on GPT-5 mini + GPT Image 1.5 + GPT-4o mini TTS pricing*

## 📊 Content Specs

| Spec | Daily Shorts | Weekly Video |
|------|--------------|--------------|
| News Count | 6 stories | 16 stories (2 per category) |
| Duration | ~60 seconds | ~4 minutes |
| Resolution | 1080x1920 (9:16) | 1920x1080 (16:9) |
| Narration | ~118 words | ~400 words |
| Images | 2 per news | 3 per news |
| Thumbnail | None (YouTube auto) | AI Generated |

## 📝 Output Files

```
output/
├── {timestamp}_Shorts.mp4
├── {timestamp}_shorts_*.png
├── {timestamp}_shorts_subtitles_*.srt
├── {timestamp}_Video.mp4
├── {timestamp}_video_*.png
├── {timestamp}_video_thumbnail.jpg
├── {timestamp}_video_subtitles_*.srt
└── {timestamp}_summary.json
```

## 🐛 Troubleshooting

### YouTube API Quota Exceeded
- Daily quota: 10,000 units (resets 17:00 KST)
- Upload uses ~1,600 units
- Wait until quota resets

### FFmpeg Not Found
```bash
choco install ffmpeg
```

### n8n Timezone Issue
- Set timezone to `Asia/Seoul` in workflow settings

## 📄 License

MIT License
