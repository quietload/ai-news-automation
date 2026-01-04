# 📰 AI News Automation Pipeline v2.7

Automatically generates and uploads YouTube news content using AI.

**GitHub**: https://github.com/quietload/ai-news-automation

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Script | GPT-5 mini (reasoning_effort: minimal) |
| Image | GPT Image 1.5 (오프닝 + 뉴스 + 엔딩) |
| TTS | GPT-4o mini TTS (3-voice rotation) |
| News | 38 RSS feeds |
| Automation | n8n |

## 🎙️ TTS Voice Rotation

3명의 AI 앵커가 번갈아 진행:
- **Marin** (Leader): 메인 앵커, 오프닝/클로징
- **Coral** (Friendly): 친근한 스타일
- **Nova** (Analyst): 분석적 스타일

## 🎬 Video Structure

```
┌─────────────────────────────────────┐
│  오프닝 이미지 (날짜 + 기념일/계절)    │  ← 3초
│  ※ 브레이킹: 뉴스 헤드라인 기반 테마   │
├─────────────────────────────────────┤
│  뉴스별 이미지들                      │  ← 오디오 길이에 맞춤
├─────────────────────────────────────┤
│  엔딩 이미지 (구독/좋아요)            │  ← 2초(Shorts) / 3초(Video)
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

## 🎯 Smart Opening Image

GPT가 오늘 날짜를 분석하여 테마 자동 결정:

**일반 Shorts/Video:**
- 기념일: Christmas, Halloween, Valentine's Day, etc.
- 계절: 봄 벚꽃, 여름 해변, 가을 단풍, 겨울 눈
- TOP 헤드라인 강조 (첫 번째 뉴스 제목)

**Breaking News:**
- GPT가 뉴스 헤드라인 분석
- 재난 → 긴급 빨간색
- 정치 → 공식적 분위기
- 경제 위기 → 시장 긴장감
- 유명인 사망 → 추모 분위기

## 🖼️ Image Generation (3-Stage Fallback)

1. **Normal**: 사실적 이미지 (얼굴 허용 - 알려진 인물일 때)
2. **No Face**: Policy 에러 시 → 뒷모습/실루엣 (얼굴 없음)
3. **Abstract**: 여전히 실패 시 → 추상적/상징적 이미지

## 🌍 Subtitles (5 Languages)

en, ko, ja, zh, es

## 📅 Schedule (n8n Luxon weekday: Mon=1...Sun=7)

| Time (KST) | Days | Content | Skip |
|------------|------|---------|------|
| 11:50 | Tue-Sat | Daily Shorts (US) | 일/월 (US 주말) |
| 20:50 | Mon-Fri | Daily Shorts (Korea) | 토/일 (KR 주말) |
| 11:30 | Sun | Weekly Video | - |
| Every 10min | 24/7 | Breaking News (max 1/day) | - |

## 🔥 Breaking News

**Trigger:** Breaking keywords + 5+ sources reporting same story

**Keywords:** breaking, dies, war, earthquake, crash, resigns, etc.

**Keyword-based Grouping:**
- 동일 사건이 다른 제목으로 보도되어도 그룹핑
- 국가/지역 키워드: venezuela, ukraine, russia, china, iran, israel 등
- 예: "US strikes Venezuela" + "Maduro captured" + "Caracas explosions" → 동일 사건

**Lock File:**
- `breaking.lock` 생성하여 중복 실행 방지
- 30분 이상 된 락은 자동 삭제

## 📁 Project Structure

```
news/
├── news_dual.py                    # 메인 생성기
│   ├── generate_opening_image()        # GPT 기반 오프닝 테마
│   ├── generate_breaking_opening_image()  # 속보용 긴박한 테마
│   ├── generate_segmented_audio()      # 세그먼트별 TTS
│   └── create_video()                  # 오프닝/엔딩 포함 영상
├── news_rss.py                     # RSS 수집 + 속보 감지
├── upload_video.py                 # YouTube 업로드
│
├── # Runner Scripts
├── run_daily_shorts_rss_morning.py
├── run_daily_shorts_rss.py
├── run_weekly_video_rss.py
├── run_breaking_news.py
│
├── # n8n Workflows
├── n8n_*.json
│
├── # Tracking
├── used_news_daily.json
├── used_news_weekly.json
│
├── assets/
│   ├── ending_shorts.png           # 세로 엔딩
│   └── ending_video.png            # 가로 엔딩
└── output/                         # 생성된 영상
```

## ⚙️ Setup

### 1. Install

```bash
pip install requests python-dotenv pillow feedparser openai google-auth google-auth-oauthlib google-api-python-client
```

### 2. FFmpeg

```bash
choco install ffmpeg  # Windows
```

### 3. API Keys (.env)

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

### 4. YouTube OAuth

1. Google Cloud Console → YouTube Data API v3
2. OAuth 2.0 credentials → `client_secrets.json`

### 5. Create Ending Images

```bash
python create_ending_images.py
```

## 🎮 Usage

```bash
# Daily Shorts
python news_dual.py --count 6 --shorts-only --use-rss

# Weekly Video
python news_dual.py --count 16 --video-only --by-category --use-rss

# Breaking News
python run_breaking_news.py
```

## 📧 Email Notifications

| Icon | Type | Content |
|------|------|---------|
| ✅ | Success | 로그 + YouTube Description |
| ❌ | Failure | 에러 로그 |
| 🔥 | Breaking | 속보 알림 |

**YouTube Description 포함**: 성공 메일에 업로드된 영상의 설명 전문 포함

## 📰 RSS Sources (38 feeds)

World, Business, Technology, Science, Health, Sports, Entertainment, Environment

## 💰 Monthly Cost

~$30 (Daily $22 + Weekly $6 + Breaking $2.50)

## 📄 License

MIT License
