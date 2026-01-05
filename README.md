# 📰 AI News Automation Pipeline v2.8

Automatically generates and uploads YouTube news content using AI.

**GitHub**: https://github.com/quietload/ai-news-automation

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Script | GPT-5 mini (reasoning_effort: minimal) |
| Image | GPT Image 1.5 (오프닝 + 뉴스 + 엔딩) |
| TTS | GPT-4o mini TTS |
| News | 38 RSS feeds |
| Automation | n8n |

## 🎙️ TTS Voice Schedule

| Time | Voice | Style |
|------|-------|-------|
| Morning (12:00) | marin | 여성, 부드러운 |
| Evening (22:00) | cedar | 남성, 차분한 |
| Weekly | Alternating | 짝수주=marin, 홀수주=cedar |

## 🎬 Video Structure

```
┌─────────────────────────────────────┐
│  오프닝 이미지 (날짜 + 기념일/계절)    │  ← 3초
│  ※ 브레이킹: 뉴스 헤드라인 기반 테마   │
├─────────────────────────────────────┤
│  뉴스별 이미지들                      │  ← 오디오 길이에 맞춤
├─────────────────────────────────────┤
│  엔딩 이미지 (구독/좋아요)            │  ← 2초(Shorts) / 3초(Video)
│  ※ 워터마크 투명도 0.3               │
└─────────────────────────────────────┘
```

## 📊 Content Specs

| Spec | Daily Shorts | Weekly Video | Breaking Shorts |
|------|--------------|--------------|-----------------|
| News Count | 6 stories | 16 stories | 1 story (deep-dive) |
| Duration | ~2 minutes | No limit | ~2 minutes |
| Resolution | 1080x1920 | 1920x1080 | 1080x1920 |
| Images | 2 per news | 3 per news | 5 images |
| Opening | 기념일/계절 | - | 긴박한 속보 테마 |

## 📅 Schedule (n8n)

| Generate (KST) | Publish (KST) | Days | Content |
|----------------|---------------|------|---------|
| 11:45 | 12:00 | Tue-Sat | Daily Shorts (US primetime) |
| 21:45 | 22:00 | Mon-Fri | Daily Shorts (Korea primetime) |
| 11:30 | 12:00 | Sun | Weekly Video |
| Every 10min | Immediate | 24/7 | Breaking News (max 2/day) |

## 🔥 Breaking News

**Trigger:** Breaking keywords + 8+ sources reporting same story + GPT verification

**Exit Codes:**
- `0` = 성공 (뉴스 업로드됨) → 이메일 발송
- `1` = 에러 → 에러 이메일 발송
- `2` = 뉴스 없음 → 무시 (이메일 없음)

## 📁 Project Structure

```
news/
├── news_dual.py                    # 메인 생성기
├── news_rss.py                     # RSS 수집 + 속보 감지
├── upload_video.py                 # YouTube 업로드 (KST→UTC 변환)
│
├── run_daily_shorts_rss_morning.py # Morning (11:45 → 12:00)
├── run_daily_shorts_rss.py         # Evening (21:45 → 22:00)
├── run_weekly_video_rss.py         # Weekly (Sun 11:30)
├── run_breaking_news.py            # Breaking (Every 10min)
│
├── n8n_daily_shorts_rss_morning_scheduled.json  # Tue-Sat 11:45
├── n8n_daily_shorts_rss_scheduled.json          # Mon-Fri 21:45
├── n8n_weekly_video_rss_scheduled.json          # Sun 11:30
├── n8n_breaking_news_detector.json              # Every 10min
│
├── assets/
│   ├── ending_shorts.png           # 세로 엔딩 (워터마크 0.3)
│   └── ending_video.png            # 가로 엔딩 (워터마크 0.3)
└── output/                         # 생성된 영상
```

## ⚙️ Setup

```bash
# Install dependencies
pip install requests python-dotenv pillow feedparser openai google-auth google-auth-oauthlib google-api-python-client

# FFmpeg (Windows)
choco install ffmpeg

# API Keys (.env)
OPENAI_API_KEY=sk-xxxxxxxxxxxxx

# Create Ending Images
python create_ending_images.py
```

## 🎮 Usage

```bash
# Daily Shorts (Morning - female voice)
python news_dual.py --count 6 --shorts-only --use-rss --voice marin

# Daily Shorts (Evening - male voice)
python news_dual.py --count 6 --shorts-only --use-rss --voice cedar

# Weekly Video
python news_dual.py --count 16 --video-only --by-category --use-rss

# Breaking News
python run_breaking_news.py
```

## 📧 n8n Email Notifications

워크플로우 실행 결과를 이메일로 알림:
- **✅ Success:** 제목, YouTube 설명 포함
- **❌ Failure:** 에러 로그 포함
- **🔥 Breaking (뉴스 없음):** 이메일 발송 안 함 (exit code 2)

## 📰 RSS Sources (38 feeds)

World, Business, Technology, Science, Health, Sports, Entertainment, Environment

## 💰 Monthly Cost

~$30 (Daily $22 + Weekly $6 + Breaking $2.50)

## 📄 License

MIT License
