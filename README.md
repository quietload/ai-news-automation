# 📰 AI News Automation Pipeline v2.5

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

| Spec | Daily Shorts | Weekly Video | Breaking Shorts |
|------|--------------|--------------|-----------------|
| News Count | 6 stories | 16 stories (2/category) | 1 story (deep-dive) |
| Duration | ~2 minutes | No limit | ~2 minutes |
| Resolution | 1080x1920 (9:16) | 1920x1080 (16:9) | 1080x1920 (9:16) |
| Narration | ~250 words | No limit | ~250 words |
| Images | 2 per news | 3 per news | 5 images |
| Style | Charismatic anchor | + commentary/humor | Urgent news tone |

## 🌍 Subtitles (11 Languages)

| Code | Language |
|------|----------|
| en | English |
| ko | 한국어 (Korean) |
| ja | 日本語 (Japanese) |
| zh | 中文 (Chinese) |
| es | Español (Spanish) |
| hi | हिन्दी (Hindi) |
| pt | Português (Portuguese) |
| id | Bahasa Indonesia |
| fr | Français (French) |
| ar | العربية (Arabic) |
| ru | Русский (Russian) |

## 📅 Schedule

| Time (KST) | Days | Content | Target |
|------------|------|---------|--------|
| 11:50 - 12:00 | Tue-Sat | Daily Shorts | 🇺🇸 US Primetime |
| 20:50 - 21:00 | Mon-Fri | Daily Shorts | 🇰🇷 Korea Primetime |
| 11:30 - 12:00 | Sun | Weekly Video | 🌏 Global |
| Every 10min | 24/7 | Breaking News | 🌏 On-demand |

## 🔥 Breaking News

**Trigger Conditions:**
- Breaking keywords (breaking, dies, war, earthquake, etc.) **AND**
- 5+ different news sources reporting the same story
- **Daily limit: Max 3 per day**

**Keywords:**
```
breaking, just in, urgent, developing, alert
dies, dead, killed, assassination
war, invasion, attack, explosion, bombing, missile
earthquake, tsunami, hurricane, typhoon, wildfire
crash, collapse, bankruptcy, default
resigns, impeached, arrested, indicted
record, historic, first ever, unprecedented
```

**Detection Flow:**
```
n8n (10min interval) -> run_breaking_news.py -> detect_breaking_news()
    |
Scan 38 RSS feeds -> Filter breaking keywords -> Group similar (40%)
    |
5+ sources? -> Generate Shorts -> Upload -> Email alert
```

## 🔍 News Filtering

| Filter | Description |
|--------|-------------|
| Local News | Skips US/UK/AU cities, local councils, school boards |
| Similar Articles | Skips 50%+ title similarity (Jaccard) |
| Auto-fill | Fills from other categories if short |
| Duplicates | Tracks separately: daily/weekly/breaking |

## 📁 Project Structure

```
news/
├── news_dual.py                    # Main generator
├── news_rss.py                     # RSS fetcher + breaking detection
├── upload_video.py                 # YouTube uploader
│
├── # Runner Scripts
├── run_daily_shorts_rss_morning.py # Noon Shorts (US)
├── run_daily_shorts_rss.py         # Evening Shorts (Korea)
├── run_daily_shorts_rss_now.py     # Immediate Shorts
├── run_weekly_video_rss.py         # Weekly Video (scheduled)
├── run_weekly_video_rss_now.py     # Weekly Video (immediate)
├── run_breaking_news.py            # Breaking News detector
│
├── # n8n Workflows
├── n8n_daily_shorts_rss_morning_scheduled.json
├── n8n_daily_shorts_rss_scheduled.json
├── n8n_weekly_video_rss_scheduled.json
├── n8n_breaking_news_detector.json
│
├── # Email Templates
├── email_templates/
│   ├── success.html                # ✅ Green - job completed
│   ├── failure.html                # ❌ Red - error details
│   └── breaking.html               # 🔥 Orange - breaking alert
│
├── # Tracking Files
├── used_news_rss_daily.json        # Daily duplicates
├── used_news_rss_weekly.json       # Weekly duplicates
├── used_news_rss_breaking.json     # Breaking duplicates
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
5. Authorize:
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
# Daily Shorts
python news_dual.py --count 6 --shorts-only --use-rss

# Weekly Video
python news_dual.py --count 16 --video-only --by-category --use-rss

# Breaking News (check only)
python run_breaking_news.py --dry-run
```

### Immediate Upload

```bash
python run_daily_shorts_rss_now.py
python run_weekly_video_rss_now.py
```

### Automated (n8n)

```powershell
$env:N8N_USER_FOLDER = "D:\workspace\news\n8n_data"
npx n8n
```

Import workflows → Set timezone `Asia/Seoul`

## 📧 Email Notifications

### Setup Gmail SMTP

1. n8n → **Credentials** → **Add** → **SMTP**
2. Configure:
   - Host: `smtp.gmail.com`
   - Port: `465`
   - User: your Gmail
   - Password: [App Password](https://myaccount.google.com/apppasswords)
   - SSL/TLS: true
3. Update workflow JSONs:
   - `YOUR_EMAIL@gmail.com` → your email
   - `YOUR_SMTP_CREDENTIAL_ID` → credential ID

### Notification Types

| Icon | Type | Description |
|------|------|-------------|
| ✅ | Success | Job completed with output |
| ❌ | Failure | Error details + actions |
| 🔥 | Breaking | Breaking news generated |

## 📰 RSS Sources (38 feeds)

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

## 💰 Monthly Cost

| Item | Calculation | Cost |
|------|-------------|------|
| Daily Shorts | $0.50 × 2 × 22 days | ~$22 |
| Weekly Video | $1.50 × 4 weeks | ~$6 |
| Breaking | $0.50 × ~5/month | ~$2.50 |
| **Total** | | **~$30** |

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
