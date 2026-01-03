#!/usr/bin/env python3
"""
News Automation Pipeline v2.5
=============================

YouTube 뉴스 콘텐츠 자동 생성 파이프라인

Content Types:
    - Daily Shorts: 6개 뉴스, 세로형, ~2분, ~250 words (하루 2회)
    - Weekly Video: 16개 뉴스 (카테고리별 2개), 가로형, 제한 없음
    - Breaking News: 단일 뉴스 딥다이브, ~2분, ~250 words (온디맨드)

Tech Stack:
    - Text: GPT-5 mini (reasoning_effort: minimal)
    - Image: GPT Image 1.5
    - TTS: GPT-4o mini TTS (Marin voice)
    - News: 38 RSS feeds

Features:
    - 실시간 RSS 뉴스 수집
    - 로컬/유사 기사 필터링
    - AI 이미지 생성 (뉴스당 2-3장)
    - 다국어 자막 (EN, KO, JA, ZH, ES)
    - 오디오-이미지 동기화
    - 썸네일 자동 생성 (Weekly)
    - YouTube 예약 업로드
    - 중복 뉴스 방지

Usage:
    python news_dual.py --count 6 --shorts-only --use-rss      # Daily Shorts
    python news_dual.py --count 16 --video-only --by-category --use-rss  # Weekly
    python news_dual.py --breaking-news temp.json              # Breaking

Schedule:
    - 11:50 - 12:00 KST (Tue-Sat): US Primetime Shorts
    - 20:50 - 21:00 KST (Mon-Fri): Korea Primetime Shorts
    - 11:30 - 12:00 KST (Sun): Weekly Video
    - Every 10min: Breaking News Detection

GitHub: https://github.com/quietload/ai-news-automation
"""

import os
import sys
import io

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import time
import argparse
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

load_dotenv()

# API Keys
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.openai.com/v1"

# Image sizes for DALL-E
SHORTS_SIZE = "1024x1792"   # Vertical 9:16
VIDEO_SIZE = "1792x1024"    # Horizontal 16:9

# Subtitle languages
LANGUAGES = ["en", "ko", "ja", "zh", "es", "hi", "pt", "id", "fr", "ar", "ru"]
LANGUAGE_NAMES = {
    "en": "English", 
    "ko": "Korean", 
    "ja": "Japanese", 
    "zh": "Chinese", 
    "es": "Spanish",
    "hi": "Hindi",
    "pt": "Portuguese",
    "id": "Indonesian",
    "fr": "French",
    "ar": "Arabic",
    "ru": "Russian"
}

# Asset paths
ASSETS_DIR = Path(__file__).parent / "assets"
ENDING_SHORTS = ASSETS_DIR / "ending_shorts.png"
ENDING_VIDEO = ASSETS_DIR / "ending_video.png"

# Used news tracking (duplicate prevention) - Daily와 Weekly 분리
USED_NEWS_FILE_DAILY = Path(__file__).parent / "used_news_daily.json"
USED_NEWS_FILE_WEEKLY = Path(__file__).parent / "used_news_weekly.json"


def generate_opening_image(output_path: Path, orientation: str = "vertical") -> Path:
    """Generate opening image with GPT determining today's theme"""
    today = datetime.now()
    month = today.month
    day = today.day
    year = today.year
    date_text = f"{month}/{day}"
    
    # Ask GPT to determine today's theme
    theme_prompt = f"""Today is {year}/{month}/{day}.

What theme should today's image have? Consider:
- Global holidays (Christmas, Halloween, Valentine's Day, Thanksgiving, etc.)
- US holidays (Independence Day, Memorial Day, Labor Day, etc.)
- Seasonal events (spring bloom, summer beach, fall harvest, winter snow)
- Cultural events (Super Bowl week, Oscar season, etc.)
- If nothing special, use the current season

Reply with ONLY a short image theme description in English (one line, for image generation).
Example: "Thanksgiving harvest, autumn colors, pumpkins and warm tones"
Example: "Snowy winter scene, cozy warm lighting" """

    try:
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": theme_prompt}],
                "temperature": 0.3
            },
            timeout=30
        )
        if response.status_code == 200:
            theme_desc = response.json()["choices"][0]["message"]["content"].strip().strip('"')
        else:
            raise Exception("API error")
    except:
        # fallback to season
        if month in [12, 1, 2]:
            theme_desc = "snowy winter scene, soft snowflakes, cozy warm lighting"
        elif month in [3, 4, 5]:
            theme_desc = "cherry blossoms, fresh green leaves, bright spring morning"
        elif month in [6, 7, 8]:
            theme_desc = "bright sunny day, blue sky, refreshing summer vibes"
        else:
            theme_desc = "golden autumn leaves, warm orange tones, cozy fall atmosphere"
    
    print(f"    Opening theme: {theme_desc[:50]}...")
    
    if orientation == "vertical":
        size = SHORTS_SIZE
        format_desc = "vertical 9:16"
    else:
        size = VIDEO_SIZE
        format_desc = "horizontal 16:9"
    
    prompt = f"""Create a beautiful opening image for news broadcast.

MUST INCLUDE:
- Only the date "{date_text}" in large, stylish typography
- NO other text, NO other words, NO titles, NO logos

Theme: {theme_desc}

Style:
- Professional news broadcast aesthetic
- Modern, clean design
- {format_desc} format

The ONLY text allowed is "{date_text}" - nothing else."""

    response = requests.post(
        f"{OPENAI_API_BASE}/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-1.5", "prompt": prompt, "n": 1, "size": size, "quality": "high"},
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Opening image error: {response.text}")
    
    data = response.json()["data"][0]
    
    if "b64_json" in data:
        import base64
        img_data = base64.b64decode(data["b64_json"])
        with open(output_path, 'wb') as f:
            f.write(img_data)
    elif "url" in data:
        img_response = requests.get(data["url"], timeout=60)
        with open(output_path, 'wb') as f:
            f.write(img_response.content)
    
    return output_path

# 신뢰도 높은 글로벌 언론사 목록
TRUSTED_SOURCES = [
    # 영국
    "bbc", "reuters", "the guardian", "financial times", "the economist", "sky news",
    # 미국 (글로벌 커버리지)
    "cnn", "ap news", "associated press", "bloomberg", "cnbc", "npr", "washington post",
    "new york times", "wall street journal", "time", "newsweek", "usa today",
    # 호주/뉴질랜드
    "abc news", "sydney morning herald", "the australian",
    # 캐나다
    "cbc", "global news", "ctv news",
    # 아시아 (영어)
    "south china morning post", "the straits times", "channel news asia", "nikkei",
    # 중동/아프리카
    "al jazeera", "africa news",
    # 유럽
    "euronews", "dw", "france 24",
    # 통신사
    "afp", "agence france-presse",
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def load_used_news(news_type: str = "daily") -> set:
    """이미 사용한 뉴스 ID/제목 로드"""
    file_path = USED_NEWS_FILE_DAILY if news_type == "daily" else USED_NEWS_FILE_WEEKLY
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("used", []))
    return set()


def save_used_news(used: set, news_type: str = "daily", max_keep: int = 200):
    """사용한 뉴스 저장 (최근 200개만 유지)"""
    file_path = USED_NEWS_FILE_DAILY if news_type == "daily" else USED_NEWS_FILE_WEEKLY
    used_list = list(used)[-max_keep:]  # 최근 200개만
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({"used": used_list}, f)


def get_news_id(news: dict) -> str:
    """뉴스 고유 ID 생성 (제목 기반 해시)"""
    import hashlib
    title = news.get("title", "")
    return hashlib.md5(title.encode()).hexdigest()[:16]


def fetch_global_news(count: int = 5) -> list:
    """Fetch global news from NewsData.io (wrapper for compatibility)"""
    return fetch_global_news_with_backup(count, backup_count=0)


# 8개 글로벌 카테고리 (지역성 카테고리 제외)
ALL_CATEGORIES = [
    "world",        # 세계 뉴스
    "business",     # 비즈니스/경제
    "technology",   # 기술
    "science",      # 과학
    "health",       # 건강
    "sports",       # 스포츠
    "entertainment",# 연예
    "environment",  # 환경
]

CATEGORY_NAMES = {
    "world": "World",
    "business": "Business",
    "technology": "Technology",
    "science": "Science",
    "health": "Health",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "environment": "Environment",
    "politics": "Politics",
    "crime": "Crime",
    "food": "Food",
    "lifestyle": "Lifestyle",
    "tourism": "Tourism"
}


def fetch_news_by_categories(categories: list = None, backup_per_category: int = 3) -> list:
    """카테고리별 Top 뉴스 가져오기 (백업 포함)"""
    if categories is None:
        categories = ALL_CATEGORIES
    
    print(f"\n[1/8] Fetching news from {len(categories)} categories (with {backup_per_category} backup each)...")
    
    if not NEWSDATA_API_KEY:
        raise Exception("NEWSDATA_API_KEY is not set! Please set the environment variable.")
    
    used_news = load_used_news("weekly")
    news_items = []
    
    for category in categories:
        try:
            response = requests.get(
                "https://newsdata.io/api/1/latest",
                params={
                    "apikey": NEWSDATA_API_KEY,
                    "language": "en",
                    "category": category,
                    "prioritydomain": "top",
                    "size": 10  # 무료 플랜 최대
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"  [FAIL] {category}: API error")
                continue
            
            data = response.json()
            if data.get("status") != "success":
                print(f"  [FAIL] {category}: No results")
                continue
            
            # 중복 아닌 뉴스들 저장 (나중에 정책 위반 시 사용)
            category_news = []
            for article in data.get("results", []):
                news = {
                    "title": article.get("title", ""),
                    "description": article.get("description", "") or article.get("content", ""),
                    "source": article.get("source_name", ""),
                    "category": CATEGORY_NAMES.get(category, category),
                    "link": article.get("link", ""),
                }
                
                news_id = get_news_id(news)
                if news_id in used_news:
                    continue
                
                # 제목/설명 품질 체크
                if len(news['title']) < 20 or not news['description']:
                    continue
                    
                # 신뢰도 체크 (마크 표시용)
                source_lower = news['source'].lower()
                news['is_trusted'] = any(trusted in source_lower for trusted in TRUSTED_SOURCES)
                
                category_news.append(news)
            
            if category_news:
                news_items.extend(category_news)  # 모든 백업 포함
                print(f"  [OK] {category}: {category_news[0]['title'][:40]}... (+{len(category_news)-1} backup)")
            else:
                print(f"  [SKIP] {category}: All news already used")
                
        except Exception as e:
            print(f"  [FAIL] {category}: {e}")
    
    print(f"  [OK] Total: {len(news_items)} articles (with backups)")
    return news_items


def generate_image_prompts(news: dict, count: int, orientation: str) -> list:
    """Generate DALL-E prompts"""
    orient_desc = "vertical portrait 9:16" if orientation == "vertical" else "horizontal landscape 16:9"
    
    response = requests.post(
        f"{OPENAI_API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-5-mini",
            "messages": [{
                "role": "system",
                "content": f"""Create {count} DALL-E prompts for news photo.
Format: {orient_desc}

MANDATORY STYLE: 
- Professional news photography, shot with DSLR camera
- Real-world scene, NOT illustration, NOT digital art, NOT 3D render
- Natural lighting, shallow depth of field, photojournalism style
- Show real objects, locations, or scenes (no abstract concepts)

RULES: 
- No human faces or identifiable people
- No text, logos, or watermarks
- Under 80 words each
- Start each prompt with "Professional news photograph of..."

Output one prompt per line, no numbering."""
            }, {
                "role": "user",
                "content": f"News: {news['title']}\n{news.get('description', '')[:200]}"
            }],
            "max_completion_tokens": 500,
            "reasoning_effort": "minimal"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        content = response.json()["choices"][0]["message"]["content"].strip()
        prompts = [p.strip() for p in content.split('\n') if p.strip()]
        return prompts[:count] if prompts else [f"Professional news photograph, {orient_desc}, photojournalism style: {news['title'][:50]}"] * count
    return [f"Professional news photograph, {orient_desc}, photojournalism style: {news['title'][:50]}"] * count


def generate_image(prompt: str, output_path: Path, size: str, retry_count: int = 0) -> Path:
    """Generate image with GPT Image 1.5"""
    # size 변환: DALL-E 형식 -> gpt-image-1.5 형식
    # gpt-image-1.5는 auto, 1024x1024, 1536x1024, 1024x1536 지원
    if size == "1024x1792":  # Shorts (세로)
        img_size = "1024x1536"
    elif size == "1792x1024":  # Video (가로)
        img_size = "1536x1024"
    else:
        img_size = "1024x1024"
    
    response = requests.post(
        f"{OPENAI_API_BASE}/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-1.5", "prompt": prompt, "n": 1, "size": img_size, "quality": "medium"},
        timeout=120
    )
    
    if response.status_code != 200:
        error_data = response.json().get("error", {})
        error_code = error_data.get("code", "")
        if error_code == "content_policy_violation":
            raise ContentPolicyError(f"Content policy violation: {prompt[:50]}...")
        raise Exception(f"Image Error: {response.text}")
    
    data = response.json()["data"][0]
    
    # url 또는 b64_json 형식 처리
    if "url" in data:
        img_response = requests.get(data["url"], timeout=60)
        with open(output_path, 'wb') as f:
            f.write(img_response.content)
    elif "b64_json" in data:
        import base64
        img_data = base64.b64decode(data["b64_json"])
        with open(output_path, 'wb') as f:
            f.write(img_data)
    else:
        raise Exception(f"Unknown response format: {data.keys()}")
    
    return output_path


class ContentPolicyError(Exception):
    """Content policy violation error"""
    pass


def fetch_global_news_with_backup(count: int, backup_count: int = 5) -> list:
    """Fetch news from multiple categories to ensure diversity (Daily Shorts용)"""
    print(f"\n[1/8] Fetching news (target: {count}, backup: {backup_count})...")
    
    if not NEWSDATA_API_KEY:
        raise Exception("NEWSDATA_API_KEY is not set! Please set the environment variable.")
    
    used_news = load_used_news("daily")
    news_items = []
    
    # 8개 글로벌 카테고리 (지역성 카테고리 제외)
    all_categories = [
        "world", "business", "technology", "science", 
        "health", "sports", "entertainment", "environment"
    ]
    
    # 랜덤 순서로 섞기 (다양성)
    import random
    random.shuffle(all_categories)
    
    for category in all_categories:
        if len(news_items) >= count + backup_count:
            break
            
        try:
            response = requests.get(
                "https://newsdata.io/api/1/latest",
                params={
                    "apikey": NEWSDATA_API_KEY,
                    "language": "en",
                    "category": category,
                    "prioritydomain": "top",
                    "size": 10  # 무료 플랜 최대
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"  [WARN] {category}: API error {response.status_code}")
                continue
            
            data = response.json()
            if data.get("status") != "success":
                continue
            
            for article in data.get("results", []):
                news = {
                    "title": article.get("title", ""),
                    "description": article.get("description", "") or article.get("content", ""),
                    "source": article.get("source_name", ""),
                    "category": CATEGORY_NAMES.get(category, category.title()),
                    "image_url": article.get("image_url", ""),
                    "link": article.get("link", ""),
                }
                
                news_id = get_news_id(news)
                
                # 중복 체크
                if news_id in used_news:
                    continue
                
                # 신뢰도 높은 언론사 우선 (없으면 아무거나)
                source_lower = news['source'].lower()
                is_trusted = any(trusted in source_lower for trusted in TRUSTED_SOURCES)
                
                # 제목/설명 품질 체크
                if len(news['title']) < 20 or not news['description']:
                    continue
                
                # 이미 같은 카테고리 뉴스가 있으면 스킵 (다양성)
                if any(n.get('category') == news['category'] for n in news_items):
                    continue
                
                news_items.append(news)
                trusted_mark = "★" if is_trusted else ""
                print(f"  [OK] {category}: {news['title'][:40]}... {trusted_mark}{news['source']}")
                break  # 카테고리당 1개만
                
        except Exception as e:
            print(f"  [WARN] {category}: {e}")
            continue
    
    if len(news_items) < count:
        raise Exception(f"Not enough news fetched: {len(news_items)} (need {count}). Try clearing used_news.json")
    
    print(f"  [OK] Total: {len(news_items)} articles from {len(news_items)} categories")
    return news_items
    
    # 선택된 카테고리 출력
    selected_categories = [n.get('category', 'Unknown') for n in news_items]
    print(f"  [OK] Fetched {len(news_items)} articles: {', '.join(selected_categories[:count])}")
    
    return news_items


def generate_narration_script(news_list: list, style: str = "short", is_saturday: bool = False) -> str:
    """Generate narration script - short for Shorts, long for Video"""
    news_text = "\n".join([f"{i+1}. {n['title']}: {n.get('description', '')[:150]}" 
                          for i, n in enumerate(news_list)])
    
    # 토요일이면 "See you Monday", 아니면 "Stay informed"
    outro = "See you Monday" if is_saturday else "Stay informed"
    
    if style == "short":
        system_prompt = f"""Write a news narration for YouTube Shorts.
TARGET: ~250 words total (under 2 minutes when spoken).

Style:
- Same charismatic news anchor personality as weekly videos
- Confident, professional, but personable
- Brief commentary or context where interesting

Structure:
- Engaging intro: "Here's today's top news"
- {len(news_list)} news stories: 2 sentences each with brief context
- Smooth transitions between stories
- Quick outro: "{outro}"

Output ONLY the narration. Stay under ~250 words."""
    elif style == "breaking":
        # Breaking News - 단일 뉴스 딥다이브 (2분 이내)
        system_prompt = f"""Write an URGENT breaking news narration for YouTube Shorts.
TARGET: ~250 words total (under 2 minutes when spoken).

Style:
- Urgent, authoritative breaking news anchor tone
- This is a SINGLE major story - give it depth and context
- Professional but convey the significance

Structure:
- Urgent intro: "Breaking news" or "This just in"
- What happened (2-3 sentences with details)
- Background context (1-2 sentences)
- Why it matters / impact (1-2 sentences)
- What's next / developing (1 sentence)
- Outro: "Stay tuned for updates"

Output ONLY the narration. Stay under ~250 words."""
    else:
        system_prompt = f"""Write an engaging news narration for a weekly YouTube video.

Style:
- Be a charismatic news anchor with personality
- Add your own commentary, observations, or light humor where appropriate
- Make it conversational and entertaining, not just dry facts
- Feel free to express opinions or make witty remarks about the news

Structure:
- Engaging intro: "Welcome to this week's global news roundup"
- Each news: 2-3 sentences with context + optional brief commentary
- Smooth, natural transitions between stories
- Conclusion ending with "{outro}"

Output ONLY the narration."""
    
    response = requests.post(
        f"{OPENAI_API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-5-mini",
            "messages": [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Create narration:\n\n{news_text}"}],
            "max_completion_tokens": 800 if style == "long" else 500,
            "reasoning_effort": "minimal"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    raise Exception(f"Script generation failed: {response.text}")


def generate_segmented_narration(news_list: list, style: str = "long", is_saturday: bool = False) -> list:
    """Generate narration segments per news for synced video - returns list of {text, news_index}"""
    
    outro = "See you Monday" if is_saturday else "Stay informed. See you next time."
    
    segments = []
    
    # 인트로
    if style == "long":
        intro = "Welcome to this week's global news roundup. Here are the top stories from around the world."
    else:
        intro = "Here's today's top news."
    segments.append({"text": intro, "type": "intro", "news_index": -1})
    
    # 각 뉴스별 나레이션
    for i, news in enumerate(news_list):
        news_text = f"{news['title']}: {news.get('description', '')[:150]}"
        
        if style == "long":
            system_prompt = """Write 2-3 sentences narration for this single news story.
- Include brief context
- Professional news anchor tone
- Under 50 words
Output ONLY the narration, no intro or outro."""
        else:
            system_prompt = """Write 1 sentence narration for this news.
- Just the key point
- 15-16 words
Output ONLY the narration."""
        
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-5-mini",
                "messages": [{"role": "system", "content": system_prompt},
                            {"role": "user", "content": news_text}],
                "max_completion_tokens": 100,
                "reasoning_effort": "minimal"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            narration = response.json()["choices"][0]["message"]["content"].strip()
        else:
            narration = news['title']
        
        segments.append({"text": narration, "type": "news", "news_index": i})
    
    # 아웃트로
    segments.append({"text": outro, "type": "outro", "news_index": -1})
    
    return segments


def generate_segmented_audio(segments: list, output_dir: Path, prefix: str, voice: str = "marin") -> list:
    """Generate TTS for each segment and return list with durations"""
    
    # 뉴스 앵커 스타일 instructions
    tts_instructions = "Speak in a clear, professional news anchor tone. Confident and authoritative, with natural pacing and slight emphasis on key words."
    
    result = []
    
    for i, seg in enumerate(segments):
        audio_path = output_dir / f"{prefix}_seg_{i:02d}.mp3"
        
        response = requests.post(
            f"{OPENAI_API_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini-tts",
                "input": seg["text"],
                "voice": voice,
                "instructions": tts_instructions,
                "response_format": "mp3"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS Error segment {i}: {response.text}")
        
        with open(audio_path, 'wb') as f:
            f.write(response.content)
        
        # Get duration
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(probe_result.stdout.strip()) if probe_result.stdout.strip() else 3.0
        
        result.append({
            **seg,
            "audio_path": audio_path,
            "duration": duration
        })
    
    return result


def merge_audio_segments(segments: list, output_path: Path) -> Path:
    """Merge audio segments into one file"""
    
    concat_file = output_path.parent / f"concat_audio_{output_path.stem}.txt"
    with open(concat_file, 'w') as f:
        for seg in segments:
            abs_path = str(seg["audio_path"].resolve()).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink()
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg merge error: {result.stderr[:500]}")
    
    # Clean up segment files
    for seg in segments:
        seg["audio_path"].unlink()
    
    return output_path


def generate_tts(text: str, output_path: Path, voice: str = "marin") -> Path:
    """Generate speech with OpenAI TTS - handles long text by chunking"""
    
    # 뉴스 앵커 스타일 instructions
    tts_instructions = "Speak in a clear, professional news anchor tone. Confident and authoritative, with natural pacing and slight emphasis on key words."
    
    # TTS limit is 4096 characters
    MAX_CHARS = 4000
    
    if len(text) <= MAX_CHARS:
        # Short text - single request
        response = requests.post(
            f"{OPENAI_API_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini-tts",
                "input": text,
                "voice": voice,
                "instructions": tts_instructions,
                "response_format": "mp3"
            },
            timeout=120
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS Error: {response.text}")
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return output_path
    
    # Long text - split into chunks and merge
    print(f"    [INFO] Text too long ({len(text)} chars), splitting...")
    
    # Split by sentences
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < MAX_CHARS:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Generate audio for each chunk
    temp_files = []
    for i, chunk in enumerate(chunks):
        temp_path = output_path.parent / f"temp_audio_{i}.mp3"
        
        response = requests.post(
            f"{OPENAI_API_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini-tts",
                "input": chunk,
                "voice": voice,
                "instructions": tts_instructions,
                "response_format": "mp3"
            },
            timeout=120
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS Error chunk {i}: {response.text}")
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        temp_files.append(temp_path)
    
    # Merge audio files with FFmpeg
    concat_file = output_path.parent / "concat_audio.txt"
    with open(concat_file, 'w') as f:
        for temp_path in temp_files:
            f.write(f"file '{str(temp_path.resolve()).replace(chr(92), '/')}'\n")
    
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
           "-c", "copy", str(output_path)]
    subprocess.run(cmd, capture_output=True)
    
    # Cleanup temp files
    concat_file.unlink()
    for temp_path in temp_files:
        temp_path.unlink()
    
    return output_path


def generate_subtitles(script: str, output_dir: Path, prefix: str, audio_path: Path = None) -> dict:
    """Generate SRT subtitles in multiple languages - 직접 타이밍 계산"""
    print(f"  Generating subtitles...")
    
    # 실제 오디오 길이 가져오기
    audio_duration = 60.0
    if audio_path and audio_path.exists():
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.stdout.strip():
            audio_duration = float(result.stdout.strip())
    
    # 스크립트 정리: 여러 줄바꿈을 공백으로 변환
    clean_script = ' '.join(script.strip().split())
    
    # 문장 단위로 분할 (마침표, 느낌표, 물음표 뒤에서)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', clean_script)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {}
    
    # 각 문장 길이 계산 (영어 기준 - TTS가 영어이므로)
    total_chars = sum(len(s) for s in sentences)
    
    # 타이밍 계산 (문자 수 비율로 분배)
    segments = []
    current_time = 0.0
    
    for sentence in sentences:
        char_ratio = len(sentence) / total_chars
        duration = char_ratio * audio_duration
        
        start_time = current_time
        end_time = current_time + duration
        
        segments.append({
            "start": format_srt_time(start_time),
            "end": format_srt_time(end_time),
            "text": sentence
        })
        
        current_time = end_time
    
    srt_files = {}
    num_segments = len(segments)
    
    # Generate for each language
    for lang in LANGUAGES:
        if lang == "en":
            texts = [seg['text'] for seg in segments]
        else:
            # Translate - 정확히 같은 줄 수 유지 강조
            original_texts = [seg['text'] for seg in segments]
            
            # 번역용 텍스트: 번호 붙여서 명확하게
            numbered_texts = [f"{i+1}. {text}" for i, text in enumerate(original_texts)]
            
            trans_response = requests.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-5-mini",
                    "messages": [{
                        "role": "system",
                        "content": f"""Translate to {LANGUAGE_NAMES[lang]} for video subtitles.

RULES:
- Translate each numbered line
- Keep the same numbering (1. 2. 3. ...)
- Output EXACTLY {num_segments} numbered lines
- Keep translations concise
- Do NOT merge or skip any line"""
                    }, {"role": "user", "content": "\n".join(numbered_texts)}],
                    "max_completion_tokens": 2000,
                    "reasoning_effort": "minimal"
                },
                timeout=60
            )
            
            if trans_response.status_code == 200:
                raw_content = trans_response.json()["choices"][0]["message"]["content"].strip()
                
                # 번호 제거하고 텍스트만 추출
                texts = []
                for line in raw_content.split('\n'):
                    line = line.strip()
                    if line:
                        # "1. 텍스트" 형식에서 번호 제거
                        match = re.match(r'^\d+\.\s*(.+)$', line)
                        if match:
                            texts.append(match.group(1))
                        else:
                            texts.append(line)
                
                # 줄 수 보정
                if len(texts) < num_segments:
                    texts.extend(original_texts[len(texts):])
                elif len(texts) > num_segments:
                    texts = texts[:num_segments]
            else:
                texts = [seg['text'] for seg in segments]
        
        srt_path = output_dir / f"{prefix}_subtitles_{lang}.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments):
                text = texts[i] if i < len(texts) else seg['text']
                f.write(f"{i+1}\n{seg['start']} --> {seg['end']}\n{text}\n\n")
        srt_files[lang] = srt_path
    
    print(f"    [OK] Subtitles: {', '.join(LANGUAGES)}")
    return srt_files


def generate_subtitles_from_segments(audio_segments: list, output_dir: Path, prefix: str) -> dict:
    """Generate SRT subtitles from audio segments with accurate timing"""
    print(f"  Generating subtitles from segments...")
    
    import re
    
    # 세그먼트별 시작/끝 시간 계산
    segments = []
    current_time = 0.0
    
    for seg in audio_segments:
        start_time = current_time
        end_time = current_time + seg["duration"]
        
        segments.append({
            "start": format_srt_time(start_time),
            "end": format_srt_time(end_time),
            "text": seg["text"]
        })
        
        current_time = end_time
    
    srt_files = {}
    num_segments = len(segments)
    
    for lang in LANGUAGES:
        if lang == "en":
            texts = [seg['text'] for seg in segments]
        else:
            # 번역
            original_texts = [seg['text'] for seg in segments]
            numbered_texts = [f"{i+1}. {text}" for i, text in enumerate(original_texts)]
            
            trans_response = requests.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-5-mini",
                    "messages": [{
                        "role": "system",
                        "content": f"""Translate to {LANGUAGE_NAMES[lang]} for video subtitles.
RULES:
- Translate each numbered line
- Keep the same numbering (1. 2. 3. ...)
- Output EXACTLY {num_segments} numbered lines
- Keep translations concise"""
                    }, {"role": "user", "content": "\n".join(numbered_texts)}],
                    "max_completion_tokens": 2000,
                    "reasoning_effort": "minimal"
                },
                timeout=60
            )
            
            if trans_response.status_code == 200:
                raw_content = trans_response.json()["choices"][0]["message"]["content"].strip()
                texts = []
                for line in raw_content.split('\n'):
                    line = line.strip()
                    if line:
                        match = re.match(r'^\d+\.\s*(.+)$', line)
                        if match:
                            texts.append(match.group(1))
                        else:
                            texts.append(line)
                
                if len(texts) < num_segments:
                    texts.extend(original_texts[len(texts):])
                elif len(texts) > num_segments:
                    texts = texts[:num_segments]
            else:
                texts = [seg['text'] for seg in segments]
        
        srt_path = output_dir / f"{prefix}_subtitles_{lang}.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments):
                text = texts[i] if i < len(texts) else seg['text']
                f.write(f"{i+1}\n{seg['start']} --> {seg['end']}\n{text}\n\n")
        srt_files[lang] = srt_path
    
    print(f"    [OK] Subtitles: {', '.join(LANGUAGES)}")
    return srt_files


def format_srt_time(seconds: float) -> str:
    """초를 SRT 타임코드로 변환 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_synced_video(news_images: dict, audio_segments: list, audio_path: Path, output_path: Path, 
                        resolution: tuple, ending_image: Path = None, images_per_news: int = 3) -> Path:
    """Create video with images synced to audio segments
    
    news_images: {news_index: [img1, img2, img3], ...}
    audio_segments: [{news_index, duration, text, type}, ...]
    """
    
    width, height = resolution
    is_shorts = width < height
    ending_duration = 2.0 if is_shorts else 3.0
    
    # Build image sequence with proper durations
    concat_file = output_path.parent / f"concat_{output_path.stem}.txt"
    
    with open(concat_file, 'w') as f:
        for seg in audio_segments:
            news_idx = seg["news_index"]
            duration = seg["duration"]
            seg_type = seg["type"]
            
            if seg_type == "news" and news_idx in news_images:
                # 뉴스 세그먼트: 해당 뉴스의 이미지들을 균등 분배
                images = news_images[news_idx]
                duration_per_img = duration / len(images)
                
                for img in images:
                    abs_path = str(img.resolve()).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
                    f.write(f"duration {duration_per_img}\n")
            else:
                # 인트로/아웃트로: 첫 번째 또는 마지막 뉴스 이미지 사용
                if seg_type == "intro" and 0 in news_images:
                    img = news_images[0][0]  # 첫 뉴스 첫 이미지
                elif seg_type == "outro" and news_images:
                    last_idx = max(news_images.keys())
                    img = news_images[last_idx][-1]  # 마지막 뉴스 마지막 이미지
                else:
                    continue
                
                abs_path = str(img.resolve()).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
                f.write(f"duration {duration}\n")
        
        # 엔딩 이미지
        if ending_image and ending_image.exists():
            abs_path = str(ending_image.resolve()).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
            f.write(f"duration {ending_duration}\n")
            f.write(f"file '{abs_path}'\n")  # FFmpeg concat 요구사항
    
    # 총 길이 계산
    total_audio = sum(seg["duration"] for seg in audio_segments)
    total_duration = total_audio + ending_duration if (ending_image and ending_image.exists()) else total_audio
    
    print(f"    [DEBUG] Synced video: {len(audio_segments)} segments, {total_audio:.1f}s audio, {total_duration:.1f}s total")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-vf", f"scale={width}:{height},setsar=1:1",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(total_duration),
        "-pix_fmt", "yuv420p", "-r", "30",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink()
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr[:500]}")
    
    return output_path


def create_video(images: list, audio_path: Path, output_path: Path, resolution: tuple, ending_image: Path = None) -> Path:
    """Create video from images and audio"""
    
    # Get audio duration
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    audio_duration = float(result.stdout.strip()) if result.stdout.strip() else 60.0
    
    print(f"    [DEBUG] Audio duration: {audio_duration:.1f}s, Images: {len(images)}")
    
    # Build image list with opening and ending
    all_images = []
    
    # Shorts: 세로형, Video: 가로형
    is_shorts = resolution[0] < resolution[1]
    
    # Opening image (generated with date)
    opening_duration = 0
    if is_shorts:
        opening_path = output_path.parent / f"opening_{output_path.stem}.png"
        try:
            generate_opening_image(opening_path, "vertical")
            all_images.append(opening_path)
            opening_duration = 3.0  # 오프닝 3초
            print(f"    [OK] Opening image generated")
        except Exception as e:
            print(f"    [WARN] Opening image failed: {e}")
    
    # Content images
    all_images.extend(images)
    
    # Ending image
    ending_duration = 2.0 if is_shorts else 3.0
    
    if ending_image and ending_image.exists():
        all_images.append(ending_image)
        # 콘텐츠 이미지들은 오디오 길이에서 오프닝 시간을 뺀 만큼
        content_duration = audio_duration - opening_duration
        duration_per_image = content_duration / len(images) if images else 5.0
    else:
        duration_per_image = audio_duration / len(images) if images else 5.0
        ending_duration = 0
    
    print(f"    [DEBUG] Duration per image: {duration_per_image:.2f}s, Total images: {len(all_images)}")
    
    # Create concat file
    concat_file = output_path.parent / f"concat_{output_path.stem}.txt"
    with open(concat_file, 'w') as f:
        for i, img in enumerate(all_images):
            abs_path = str(img.resolve()).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
            
            # Opening image
            if opening_duration > 0 and i == 0:
                f.write(f"duration {opening_duration}\n")
            # Ending image (last)
            elif ending_image and ending_image.exists() and i == len(all_images) - 1:
                f.write(f"duration {ending_duration}\n")
            # Content images
            else:
                f.write(f"duration {duration_per_image}\n")
        abs_path = str(all_images[-1].resolve()).replace('\\', '/')
        f.write(f"file '{abs_path}'\n")
    
    width, height = resolution
    
    # 총 길이 계산 (오디오 + 오프닝(무음) + 엔딩(무음))
    total_duration = audio_duration + ending_duration
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-vf", f"scale={width}:{height},setsar=1:1",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(total_duration),
        "-pix_fmt", "yuv420p", "-r", "30",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink()
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr[:500]}")
    
    return output_path


def generate_description(news_list: list, is_weekly: bool = False) -> str:
    """Generate YouTube description with source links"""
    stories = []
    for i, n in enumerate(news_list):
        title = n['title']
        link = n.get('link', '')
        if link:
            stories.append(f"{i+1}. {title}\n{link}")
        else:
            stories.append(f"{i+1}. {title}")
    
    stories_text = "\n\n".join(stories)
    
    if is_weekly:
        header = "AI News Daily | Weekly Roundup (16 Stories)"
        stories_header = "This Week's Top Stories:"
    else:
        header = "AI News Daily | Today's Headlines (6 Stories)"
        stories_header = "Today's Stories:"
    
    subtitle_langs = "🌍 Subtitles: English, 한국어, 日本語, 中文, Español, हिन्दी, Português, Bahasa Indonesia, Français, العربية, Русский"
    
    description = f"{header}\n\n{subtitle_langs}\n\n{stories_header}\n\n{stories_text}\n\n---\nGenerated with AI\n\n#news #AI #globalNews #worldnews #breakingnews"
    return description


def generate_thumbnail(news_list: list, output_path: Path, style: str = "shorts") -> Path:
    """Generate eye-catching thumbnail: GPT Image background + Python text overlay"""
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    orientation = "vertical portrait" if style == "shorts" else "horizontal landscape"
    
    # 뉴스 제목들로 이미지 프롬프트 생성
    titles = [n['title'][:50] for n in news_list[:5]]
    titles_summary = ", ".join(titles)
    
    # 1. GPT에게 뉴스 내용 기반 이미지 프롬프트 요청
    prompt_response = requests.post(
        f"{OPENAI_API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-5-mini",
            "messages": [{
                "role": "system",
                "content": f"Create a DALL-E image prompt that combines these news topics into ONE dramatic scene. Format: {orientation}. RULES: Combine all topics into a single cohesive, dramatic scene. Photorealistic, cinematic quality, dramatic lighting. NO text, NO words, NO letters, NO numbers, NO faces. Show objects, symbols, or scenes representing the news. High contrast, vibrant colors, eye-catching. Under 100 words."
            }, {
                "role": "user",
                "content": f"News topics: {titles_summary}"
            }],
            "max_completion_tokens": 150,
            "reasoning_effort": "minimal"
        },
        timeout=30
    )
    
    if prompt_response.status_code == 200:
        prompt = prompt_response.json()["choices"][0]["message"]["content"].strip()
    else:
        prompt = f"Dramatic cinematic {orientation} scene, world news theme, professional photography, high contrast lighting"
    
    # size 변환: gpt-image-1.5 지원 형식
    
    # size 변환: gpt-image-1.5 지원 형식
    if style == "shorts":
        img_size = "1024x1536"
        pil_size = (1024, 1536)
    else:
        img_size = "1536x1024"
        pil_size = (1536, 1024)
    
    # 2. GPT Image로 배경 생성
    response = requests.post(
        f"{OPENAI_API_BASE}/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-image-1.5", "prompt": prompt, "n": 1, "size": img_size, "quality": "medium"},
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Thumbnail generation failed: {response.text}")
    
    data = response.json()["data"][0]
    
    # 이미지 로드
    if "url" in data:
        img_response = requests.get(data["url"], timeout=60)
        img = Image.open(io.BytesIO(img_response.content))
    elif "b64_json" in data:
        import base64
        img_data = base64.b64decode(data["b64_json"])
        img = Image.open(io.BytesIO(img_data))
    else:
        raise Exception("Unknown image format")
    
    # 3. 텍스트 오버레이 추가
    draw = ImageDraw.Draw(img)
    
    # 폰트 설정 (시스템 폰트 사용)
    try:
        # Windows
        font_large = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 72)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 48)
        font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except:
        # 기본 폰트
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
    
    width, height = pil_size
    
    # 카테고리들 추출
    categories = list(set([n.get('category', 'News') for n in news_list[:5]]))[:4]
    category_text = " • ".join(categories)
    
    if style == "shorts":
        # Shorts 세로형 레이아웃
        today = datetime.now().strftime("%b %d").upper()  # "DEC 31"
        year = datetime.now().strftime("%Y")  # "2025"
        
        # 상단: "TODAY'S"
        text1 = "TODAY'S"
        bbox1 = draw.textbbox((0, 0), text1, font=font_large)
        x1 = (width - (bbox1[2] - bbox1[0])) // 2
        draw.text((x1+3, 83), text1, font=font_large, fill="black")
        draw.text((x1, 80), text1, font=font_large, fill="#FF3333")
        
        # "NEWS"
        text2 = "NEWS"
        bbox2 = draw.textbbox((0, 0), text2, font=font_large)
        x2 = (width - (bbox2[2] - bbox2[0])) // 2
        draw.text((x2+3, 163), text2, font=font_large, fill="black")
        draw.text((x2, 160), text2, font=font_large, fill="white")
        
        # 중앙: 날짜 (크게)
        try:
            font_xlarge = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 96)
        except:
            font_xlarge = font_large
        
        bbox_date = draw.textbbox((0, 0), today, font=font_xlarge)
        x_date = (width - (bbox_date[2] - bbox_date[0])) // 2
        draw.text((x_date+4, height//2 - 50 + 4), today, font=font_xlarge, fill="black")
        draw.text((x_date, height//2 - 50), today, font=font_xlarge, fill="white")
        
        # 연도
        bbox_year = draw.textbbox((0, 0), year, font=font_medium)
        x_year = (width - (bbox_year[2] - bbox_year[0])) // 2
        draw.text((x_year+2, height//2 + 52), year, font=font_medium, fill="black")
        draw.text((x_year, height//2 + 50), year, font=font_medium, fill="#FFD700")
        
    else:
        # Video 가로형 레이아웃 - 심플하게
        today = datetime.now().strftime("%b %d").upper()
        year = datetime.now().strftime("%Y")
        
        # 큰 폰트 설정
        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 96)  # WEEKLY NEWS용
            font_date = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 84)   # 날짜용
        except:
            font_title = font_large
            font_date = font_large
        
        # 좌측 상단: "WEEKLY" (크게, 살짝 아래로)
        text1 = "WEEKLY"
        draw.text((53, 83), text1, font=font_title, fill="black")
        draw.text((50, 80), text1, font=font_title, fill="#FF3333")
        
        # 좌측 상단: "NEWS" (크게, 살짝 아래로)
        text2 = "NEWS"
        draw.text((53, 183), text2, font=font_title, fill="black")
        draw.text((50, 180), text2, font=font_title, fill="white")
        
        # 우측 하단: 날짜 (크게, 살짝 위로 + 왼쪽으로)
        bbox_date = draw.textbbox((0, 0), today, font=font_date)
        x_date = width - (bbox_date[2] - bbox_date[0]) - 80
        draw.text((x_date+3, height - 200 + 3), today, font=font_date, fill="black")
        draw.text((x_date, height - 200), today, font=font_date, fill="white")
        
        bbox_year = draw.textbbox((0, 0), year, font=font_medium)
        x_year = width - (bbox_year[2] - bbox_year[0]) - 80
        draw.text((x_year+2, height - 110 + 2), year, font=font_medium, fill="black")
        draw.text((x_year, height - 110), year, font=font_medium, fill="#FFD700")
    
    # 4. 저장 (JPEG로 압축 - YouTube 썸네일 2MB 제한)
    img = img.convert("RGB")
    jpg_path = Path(str(output_path).replace(".png", ".jpg"))
    img.save(jpg_path, "JPEG", quality=85)
    
    return jpg_path


def main():
    parser = argparse.ArgumentParser(description="News Shorts + Video Generator")
    parser.add_argument("--count", type=int, default=10, help="Number of news")
    parser.add_argument("--output", type=str, default="./output", help="Output directory")
    parser.add_argument("--shorts-only", action="store_true", help="Generate Shorts only")
    parser.add_argument("--video-only", action="store_true", help="Generate Video only")
    parser.add_argument("--by-category", action="store_true", help="Fetch 1 news per category (for weekly video)")
    parser.add_argument("--use-rss", action="store_true", help="Use RSS feeds instead of NewsData.io (real-time, no delay)")
    parser.add_argument("--breaking-news", type=str, help="Path to breaking news JSON file (single story, 60s deep dive)")
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    generate_shorts = not args.video_only
    generate_video = not args.shorts_only
    is_breaking = args.breaking_news is not None
    
    # 1. Fetch news
    if args.breaking_news:
        # Breaking News 모드 - 단일 뉴스 딥다이브
        print(f"\n[1/8] Loading breaking news from {args.breaking_news}...")
        with open(args.breaking_news, 'r', encoding='utf-8') as f:
            breaking_data = json.load(f)
        
        main_news = breaking_data['main']
        related = breaking_data.get('related', [])
        
        # 메인 뉴스 + 관련 소스 정보를 하나의 뉴스로 합침
        all_news = [{
            'title': main_news['title'],
            'description': main_news.get('description', ''),
            'category': main_news.get('category', 'Breaking'),
            'source': main_news.get('source', 'Multiple Sources'),
            'related_sources': [r.get('source', '') for r in related[:4]],
            'is_breaking': True
        }]
        
        print(f"  [OK] Breaking: {main_news['title'][:50]}...")
        print(f"  [OK] Related sources: {len(related)}")
        
        generate_video = False  # Breaking은 Shorts만
        
    elif args.use_rss:
        # RSS 피드 사용 (실시간, 딜레이 없음)
        from news_rss import fetch_rss_news, fetch_rss_news_by_category
        if args.by_category:
            all_news = fetch_rss_news_by_category(count=args.count, news_type="weekly")
        else:
            all_news = fetch_rss_news(count=args.count, news_type="daily")
    elif args.by_category:
        # NewsData.io 카테고리별 (주간 비디오용)
        all_news = fetch_news_by_categories(ALL_CATEGORIES)
    else:
        # NewsData.io 기존 방식 (일반)
        all_news = fetch_global_news_with_backup(args.count, backup_count=5)
    
    # 2. Generate images (skip policy violations, use backup news)
    shorts_images = []
    video_images = []
    used_news = []  # Successfully processed news
    skipped_news = []  # Policy violation news
    news_index = 0
    
    # Breaking News는 단일 뉴스에 더 많은 이미지 (4-5장)
    shorts_images_per_news = 5 if is_breaking else 2
    
    if generate_shorts:
        print(f"\n[2/8] Generating Shorts images (vertical, {shorts_images_per_news} per news)...")
        target_news_count = 1 if is_breaking else args.count
        
        while len(used_news) < target_news_count and news_index < len(all_news):
            news = all_news[news_index]
            news_index += 1
            
            print(f"  [{len(used_news)+1}/{target_news_count}] {news['title'][:35]}...")
            try:
                prompts = generate_image_prompts(news, count=shorts_images_per_news, orientation="vertical")
                news_images = []
                for j, prompt in enumerate(prompts, 1):
                    img_path = output_dir / f"{ts}_shorts_{len(used_news)+1}_{j}.png"
                    generate_image(prompt, img_path, SHORTS_SIZE)
                    news_images.append(img_path)
                    print(f"    [OK] Image {j}/{shorts_images_per_news}")
                
                shorts_images.extend(news_images)
                if news not in used_news:
                    used_news.append(news)
                    
            except ContentPolicyError as e:
                print(f"    [SKIP] Policy violation - trying next news...")
                skipped_news.append(news)
            except Exception as e:
                print(f"    [FAIL] {e}")
        
        if len(used_news) < args.count:
            print(f"  [WARN] Only {len(used_news)} news processed (policy violations: {len(skipped_news)})")
    
    # Use the same successfully processed news for video
    news_list = used_news[:args.count]
    
    if generate_video:
        print(f"\n[3/8] Generating Video images (horizontal, 3 per news)...")
        
        # video-only + by-category일 때는 카테고리별로 처리
        if args.video_only and args.by_category:
            video_used_news = []
            video_news_index = 0
            target_count = args.count
            max_per_category = (target_count + len(ALL_CATEGORIES) - 1) // len(ALL_CATEGORIES)  # 카테고리당 최대 개수
            
            while len(video_used_news) < target_count and video_news_index < len(all_news):
                news = all_news[video_news_index]
                video_news_index += 1
                
                # 카테고리당 max_per_category개까지만 허용
                category = news.get('category', 'News')
                category_count = sum(1 for n in video_used_news if n.get('category') == category)
                if category_count >= max_per_category:
                    continue
                
                print(f"  [{len(video_used_news)+1}/{target_count}] [{category}] {news['title'][:30]}...")
                try:
                    prompts = generate_image_prompts(news, count=3, orientation="horizontal")
                    for j, prompt in enumerate(prompts, 1):
                        img_path = output_dir / f"{ts}_video_{len(video_used_news)+1}_{j}.png"
                        generate_image(prompt, img_path, VIDEO_SIZE)
                        video_images.append(img_path)
                        print(f"    [OK] Image {j}/3")
                    
                    video_used_news.append(news)
                    
                except ContentPolicyError as e:
                    print(f"    [SKIP] Policy violation - trying next {category} news...")
                except Exception as e:
                    print(f"    [FAIL] {e}")
            
            news_list = video_used_news
        else:
            # 기존 방식
            for i, news in enumerate(news_list, 1):
                print(f"  [{i}/{len(news_list)}] {news['title'][:35]}...")
                try:
                    prompts = generate_image_prompts(news, count=3, orientation="horizontal")
                    for j, prompt in enumerate(prompts, 1):
                        img_path = output_dir / f"{ts}_video_{i}_{j}.png"
                        generate_image(prompt, img_path, VIDEO_SIZE)
                        video_images.append(img_path)
                        print(f"    [OK] Image {j}/3")
                except ContentPolicyError as e:
                    print(f"    [SKIP] Policy violation for video image")
                except Exception as e:
                    print(f"    [FAIL] {e}")
    
    results = {}
    
    # 3-5. Generate Shorts
    if generate_shorts and shorts_images:
        narration_style = "breaking" if is_breaking else "short"
        print(f"\n[4/8] Generating Shorts narration ({narration_style})...")
        shorts_script = generate_narration_script(news_list, style=narration_style)
        shorts_script_file = output_dir / f"{ts}_shorts_script.txt"
        with open(shorts_script_file, 'w', encoding='utf-8') as f:
            f.write(shorts_script)
        print(f"  [OK] Script: {len(shorts_script.split())} words")
        
        print(f"\n[5/8] Generating Shorts audio...")
        shorts_audio = output_dir / f"{ts}_shorts_audio.mp3"
        generate_tts(shorts_script, shorts_audio)
        print(f"  [OK] Audio saved")
        
        shorts_srt = generate_subtitles(shorts_script, output_dir, f"{ts}_shorts", shorts_audio)
        
        print(f"\n[6/8] Creating Shorts video...")
        shorts_video = output_dir / f"{ts}_Shorts.mp4"
        create_video(shorts_images, shorts_audio, shorts_video, (1080, 1920), ENDING_SHORTS)
        print(f"  [OK] Shorts: {shorts_video.name}")
        
        # Shorts는 썸네일 업로드 불가 (영상에서 프레임 선택 방식)
        
        results["shorts"] = {
            "video": str(shorts_video),
            "thumbnail": None,  # Shorts는 썸네일 없음
            "subtitles": {k: str(v) for k, v in shorts_srt.items()},
            "title": f"Today's Top News - {datetime.now().strftime('%b %d')} #shorts",
            "description": generate_description(news_list)
        }
    
    # 6-8. Generate Video (with synced audio)
    if generate_video and video_images:
        # 토요일인지 확인
        is_saturday = datetime.now().weekday() == 5
        
        print(f"\n[7/8] Generating Video narration (segmented for sync)...")
        
        # 뉴스별 이미지 매핑 생성 (3장씩)
        news_image_map = {}
        img_idx = 0
        for i in range(len(news_list)):
            news_image_map[i] = video_images[img_idx:img_idx+3]
            img_idx += 3
            if img_idx > len(video_images):
                break
        
        # 세그먼트별 나레이션 생성
        audio_segments = generate_segmented_narration(news_list, style="long", is_saturday=is_saturday)
        print(f"  [OK] Generated {len(audio_segments)} segments (intro + {len(news_list)} news + outro)")
        
        # 세그먼트별 TTS 생성
        print(f"  Generating segmented audio...")
        audio_segments = generate_segmented_audio(audio_segments, output_dir, f"{ts}_video")
        total_duration = sum(seg["duration"] for seg in audio_segments)
        print(f"  [OK] Total audio: {total_duration:.1f}s")
        
        # 오디오 병합
        video_audio = output_dir / f"{ts}_video_audio.mp3"
        merge_audio_segments(audio_segments, video_audio)
        print(f"  [OK] Audio merged")
        
        # 스크립트 저장 (자막용)
        video_script = " ".join([seg["text"] for seg in audio_segments])
        video_script_file = output_dir / f"{ts}_video_script.txt"
        with open(video_script_file, 'w', encoding='utf-8') as f:
            f.write(video_script)
        
        # 자막 생성 (세그먼트 기반)
        video_srt = generate_subtitles_from_segments(audio_segments, output_dir, f"{ts}_video")
        
        print(f"\n[8/8] Creating synced Video...")
        video_file = output_dir / f"{ts}_Video.mp4"
        create_synced_video(news_image_map, audio_segments, video_audio, video_file, (1920, 1080), ENDING_VIDEO)
        print(f"  [OK] Video: {video_file.name}")
        
        # Generate Video thumbnail
        print(f"  Generating Video thumbnail...")
        try:
            video_thumb = output_dir / f"{ts}_video_thumbnail.jpg"
            generate_thumbnail(news_list, video_thumb, style="video")
            print(f"  [OK] Thumbnail: {video_thumb.name}")
        except Exception as e:
            video_thumb = None
            print(f"  [WARN] Thumbnail failed: {e}")
        
        results["video"] = {
            "video": str(video_file),
            "thumbnail": str(video_thumb) if video_thumb else None,
            "subtitles": {k: str(v) for k, v in video_srt.items()},
            "title": f"Weekly News Roundup - {datetime.now().strftime('%b %d, %Y')}",
            "description": generate_description(news_list, is_weekly=True)
        }
    
    # Save summary
    summary = {
        "timestamp": ts,
        "news_count": len(news_list),
        "news": news_list,
        **results
    }
    
    summary_file = output_dir / f"{ts}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 사용한 뉴스 저장 (중복 방지) - RSS 사용 시 news_rss.py에서 저장하므로 스킵
    if not args.use_rss:
        news_type = "weekly" if args.by_category else "daily"
        used_news = load_used_news(news_type)
        for news in news_list:
            used_news.add(get_news_id(news))
        save_used_news(used_news, news_type)
    
    print(f"\n{'='*60}")
    print(f"[OK] Complete!")
    if "shorts" in results:
        print(f"[OK] Shorts: {results['shorts']['video']}")
    if "video" in results:
        print(f"[OK] Video: {results['video']['video']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
