# 📰 AI News Automation Pipeline v2.2

Automatically generates and uploads YouTube news content using AI.

**GitHub**: https://github.com/quietload/ai-news-automation

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Text Generation | GPT-5 mini (reasoning_effort: minimal) |
| Image Generation | GPT Image 1.5 |
| Text-to-Speech | GPT-4o mini TTS (Marin voice) |
| News Source | 38 RSS feeds (real-time) |
| Automation | n8n |

## 📊 Content Specs

| Spec | Daily Shorts | Weekly Video |
|------|--------------|--------------|
| News Count | 6 stories | 16 stories (2 per category) |
| Duration | ~60 seconds | ~4 minutes |
| Resolution | 1080x1920 (9:16) | 1920x1080 (16:9) |
| Narration | ~118 words | ~400 words |
| Images | 2 per news | 3 per news |
| Thumbnail | None (YouTube auto) | AI Generated |

## 📅 Schedule

| Time (KST) | Days | Content | Target Audience |
|------------|------|---------|-----------------|
| 11:30 → 12:00 | Tue-Sat | Daily Shorts (6 news) | 🇺🇸 US (Mon-Fri 10PM ET / 7PM PT) |
| 23:30 → 00:00 | Mon-Fri | Daily Shorts (6 news) | 🇰🇷 Korea (Late Night) |
| 11:30 → 12:00 | Sun | Weekly Video (16 news) | 🌏 Global |

*First time = Generation, Second time = YouTube publish*

## 📁 Project Structure

```
news/
├── news_dual.py                    # Main generator
├── news_rss.py                     # RSS feed fetcher
├── upload_video.py                 # YouTube uploader
│
├── # Runner Scripts
├── run_daily_shorts_rss_morning.py # Noon Shorts (US primetime)
├── run_daily_shorts_rss.py         # Midnight Shorts (Korea)
├── run_daily_shorts_rss_now.py     # Immediate upload
├── run_weekly_video_rss.py         # Weekly Video (scheduled)
├── run_weekly_video_rss_now.py     # Weekly Video (immediate)
│
├── # n8n Workflows
├── n8n_daily_shorts_rss_morning_scheduled.json  # 11:00 KST (Tue-Sat)
├── n8n_daily_shorts_rss_scheduled.json          # 23:00 KST (Mon-Fri)
├── n8n_weekly_video_rss_scheduled.json          # 11:00 KST (Sun)
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
pip install requests python-dotenv pillow feedparser openai google-auth google-auth-oauthlib google-api-python-client
```

### 2. Install FFmpeg

```bash
# Windows
choco install ffmpeg
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
$env:N8N_USER_FOLDER = "D:\workspace\news\n8n_data"
npx n8n
```

Import workflows and set timezone to `Asia/Seoul`.

## 📰 News Sources (38 RSS Feeds)

| Category | Sources |
|----------|---------|
| World | Korea Herald, Korea Times, Yonhap, BBC, Al Jazeera, DW |
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
| Daily Shorts | $0.50 × 2 × 22 days | ~$22 |
| Weekly Video | $1.50 × 4 weeks | ~$6 |
| **Total** | | **~$28** |

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

## 📄 License

MIT License
