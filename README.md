# 📰 AI News Automation Pipeline

Automatically generates and uploads YouTube news content using AI.

## 📋 Overview

| Content | Schedule | Format | Duration |
|---------|----------|--------|----------|
| **Daily Shorts** | Mon-Fri 21:00 KST | Vertical (1080x1920) | ~60s |
| **Weekly Video** | Sat 21:00 KST | Horizontal (1920x1080) | ~5min |
| **Sunday** | Rest day 😴 | - | - |

## 🚀 Features

- ✅ News fetching from RSS feeds (real-time) or NewsData.io
- ✅ AI text generation (GPT-5 mini with minimal reasoning)
- ✅ AI image generation (GPT Image 1.5)
- ✅ Text-to-speech narration (GPT-4o mini TTS - Marin voice)
- ✅ Multi-language subtitles (EN, KO, JA, ZH, ES)
- ✅ Synchronized audio-image timing
- ✅ Auto-generated thumbnails
- ✅ YouTube scheduled upload
- ✅ Duplicate news prevention
- ✅ Korean news sources for World category

## 📁 File Structure

```
news/
├── news_dual.py                    # Main generator
├── news_rss.py                     # RSS feed fetcher
├── upload_video.py                 # YouTube uploader
├── upload_instagram.py             # Instagram uploader (optional)
│
├── # NewsData.io runners
├── run_daily_shorts.py             # Daily shorts (scheduled)
├── run_daily_shorts_now.py         # Daily shorts (immediate)
├── run_weekly_video.py             # Weekly video (scheduled)
├── run_weekly_video_now.py         # Weekly video (immediate)
│
├── # RSS runners (recommended)
├── run_daily_shorts_rss.py         # Daily shorts RSS (scheduled)
├── run_daily_shorts_rss_now.py     # Daily shorts RSS (immediate)
├── run_weekly_video_rss.py         # Weekly video RSS (scheduled)
├── run_weekly_video_rss_now.py     # Weekly video RSS (immediate)
│
├── # n8n workflows
├── n8n_daily_shorts_scheduled.json
├── n8n_weekly_video_scheduled.json
├── n8n_daily_shorts_rss_scheduled.json
├── n8n_weekly_video_rss_scheduled.json
│
├── .env                            # API keys
├── client_secrets.json             # YouTube OAuth
├── used_news_daily.json            # Daily duplicate tracking
├── used_news_weekly.json           # Weekly duplicate tracking
├── used_news_rss_daily.json        # RSS daily tracking
├── used_news_rss_weekly.json       # RSS weekly tracking
├── assets/
│   ├── ending_shorts.png
│   └── ending_video.png
├── output/                         # Generated content
├── logs/                           # Execution logs
└── n8n_data/                       # n8n database
```

## ⚙️ Setup

### 1. Install Dependencies

```bash
pip install requests python-dotenv pillow feedparser
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
NEWSDATA_API_KEY=pub_xxxxxxxxxxxxx   # Optional if using RSS
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
# Daily Shorts with RSS (10 news, recommended)
python news_dual.py --count 10 --shorts-only --use-rss

# Weekly Video with RSS (20 news by category)
python news_dual.py --count 20 --video-only --by-category --use-rss

# Using NewsData.io (12h delay, not recommended)
python news_dual.py --count 10 --shorts-only
```

### Runner Scripts

```bash
# RSS (recommended - real-time news)
python run_daily_shorts_rss_now.py    # Immediate upload
python run_weekly_video_rss_now.py    # Immediate upload

# NewsData.io (12h delay)
python run_daily_shorts_now.py
python run_weekly_video_now.py
```

### Automated (with n8n)

1. Start n8n:
   ```powershell
   $env:N8N_USER_FOLDER = "D:\workspace\news\n8n_data"
   npx n8n
   ```

2. Import workflow:
   - `n8n_daily_shorts_rss_scheduled.json` (recommended)
   - `n8n_weekly_video_rss_scheduled.json` (recommended)

3. Set timezone to `Asia/Seoul`

4. Activate workflows

## 📅 Schedule

| Day | Time (KST) | Content |
|-----|------------|---------|
| Mon | 20:00 → 21:00 | Daily Shorts (10 news) |
| Tue | 20:00 → 21:00 | Daily Shorts (10 news) |
| Wed | 20:00 → 21:00 | Daily Shorts (10 news) |
| Thu | 20:00 → 21:00 | Daily Shorts (10 news) |
| Fri | 20:00 → 21:00 | Daily Shorts (10 news) |
| **Sat** | 20:00 → 21:00 | **Weekly Video (20 news)** |
| Sun | - | Rest |

*20:00 = Generation starts, 21:00 = YouTube publish time (Korean Prime Time)*

## 📰 News Sources

### RSS Feeds (Recommended)

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

### NewsData.io (Alternative)

- 8 global categories
- 12-hour delay on free plan
- 200 credits/day limit

## 💰 Monthly Cost Estimate

| Item | Calculation | Cost |
|------|-------------|------|
| Daily Shorts | $0.65 × 22 days | $14.30 |
| Weekly Video | $2.00 × 4 weeks | $8.00 |
| **Total** | | **~$22.30** |

*Based on GPT-5 mini + GPT Image 1.5 + GPT-4o mini TTS pricing*

## 🔧 Configuration

### News Count

| Content | News Count |
|---------|------------|
| Daily Shorts | 7 stories |
| Weekly Video | 20 stories |

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
├── {timestamp}_shorts_subtitles_*.srt
├── {timestamp}_Video.mp4
├── {timestamp}_video_thumbnail.jpg
├── {timestamp}_video_subtitles_*.srt
├── {timestamp}_summary.json
└── {timestamp}_*.png (images)
```

## 🐛 Troubleshooting

### RSS Feed Errors

- Some feeds may be temporarily unavailable
- System automatically falls back to next source
- Check `logs/` for details

### NewsData.io Errors

- **size > 10**: Free plan max is 10
- **timeframe**: Paid feature only
- Use RSS instead (recommended)

### FFmpeg Not Found

```bash
choco install ffmpeg
# Or add to PATH manually
```

### YouTube Upload Limit

- New channels: 15 videos/day
- API quota: 10,000 units/day (resets 17:00 KST)
- Upload: 1,600 units, Thumbnail: 50 units

### n8n Process Not Stopping

```powershell
# Force kill Python processes
taskkill /f /im python.exe
```

## 📄 License

MIT License
