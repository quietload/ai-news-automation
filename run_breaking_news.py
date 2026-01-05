#!/usr/bin/env python3
"""
Breaking News Detector & Shorts Generator
==========================================

RSS 피드 스캔하여 속보 감지 및 Shorts 자동 생성.

Trigger:
    - Breaking 키워드 포함 (breaking, dies, war, earthquake, etc.)
    - 8개 이상 소스에서 동일 뉴스 발견
    - GPT 검증 통과 (진짜 속보인지 최종 판단)

Flow:
    1. detect_breaking_news(min_sources=8) 호출
    2. GPT로 속보 여부 최종 검증
    3. 속보 발견 시 fetch_breaking_news_details() 로 상세 수집
    4. news_dual.py --breaking-news 로 Shorts 생성
    5. upload_video.py 로 YouTube 즉시 업로드

Limits:
    - 하루 최대 2개 속보 생성

Usage:
    python run_breaking_news.py              # 감지 & 생성 & 업로드
    python run_breaking_news.py --dry-run    # 감지만 (생성 안함)

Schedule:
    n8n에서 10분마다 실행
"""

import os
import subprocess
import sys
import json
import atexit
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from news_rss import detect_breaking_news, fetch_breaking_news_details

KST = ZoneInfo("Asia/Seoul")
LOG_FILE = Path(__file__).parent / "logs" / f"breaking_{datetime.now(KST).strftime('%Y%m%d')}.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# Lock file to prevent duplicate runs
LOCK_FILE = Path(__file__).parent / "breaking.lock"

# OpenAI API
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.openai.com/v1"


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(KST).strftime('%H:%M:%S')} {msg}\n")


def cleanup_lock():
    """Remove lock file on exit"""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def verify_breaking_news_with_gpt(title: str, description: str, source_count: int) -> dict:
    """
    GPT로 속보 여부 최종 검증.
    Returns: {"is_breaking": bool, "reason": str}
    """
    log("\n[GPT] Verifying if this is truly breaking news...")
    
    prompt = f"""You are a news editor. Determine if this news is truly BREAKING NEWS worthy of immediate publication.

NEWS TITLE: {title}
DESCRIPTION: {description[:500] if description else 'N/A'}
SOURCES REPORTING: {source_count} different news outlets

BREAKING NEWS criteria (must meet ALL):
1. URGENCY: Just happened or developing RIGHT NOW (not analysis of past events)
2. GLOBAL IMPACT: Affects millions of people worldwide (not local/regional)
3. SIGNIFICANCE: Major event like death of world leader, war outbreak, major disaster, historic moment
4. NOT a reaction/opinion/analysis piece about a past event

NOT BREAKING NEWS:
- "Venezuelans divided after..." (reaction to past event)
- "What we know about..." (explainer article)
- "Analysis: Why X happened" (opinion piece)
- "X slams/criticizes Y" (political commentary)
- Local news affecting only one city/region
- Routine business news (quarterly earnings, etc.)
- Celebrity gossip or entertainment news

Respond in JSON format:
{{"is_breaking": true/false, "reason": "brief explanation"}}"""

    try:
        response = requests.post(
            f"{OPENAI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # Parse JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            result = json.loads(content)
            log(f"[GPT] Decision: {'✓ BREAKING' if result['is_breaking'] else '✗ NOT BREAKING'}")
            log(f"[GPT] Reason: {result['reason']}")
            return result
        else:
            log(f"[GPT] API error: {response.status_code}")
            # API 에러 시 보수적으로 통과시킴
            return {"is_breaking": True, "reason": "API error - defaulting to allow"}
            
    except Exception as e:
        log(f"[GPT] Error: {e}")
        # 에러 시 보수적으로 통과시킴
        return {"is_breaking": True, "reason": f"Error - defaulting to allow: {e}"}


def upload_shorts(summary: dict):
    """Upload generated Shorts to YouTube"""
    log("\n" + "=" * 60)
    log("[4/4] Uploading Breaking News to YouTube (public, immediate)...")
    log("=" * 60)
    
    shorts = summary.get("shorts")
    if not shorts:
        log("[FAIL] No shorts in summary")
        return False
    
    video_path = shorts.get("video")
    if not video_path or not Path(video_path).exists():
        log(f"[FAIL] Video not found: {video_path}")
        return False
    
    # Breaking news = 즉시 공개 (public)
    log("  Privacy: PUBLIC (immediate)")
    
    # YouTube 설명 출력 (메일에 포함용)
    log("\n" + "=" * 60)
    log("[YouTube Description]")
    log("=" * 60)
    log(shorts["description"])
    log("=" * 60 + "\n")
    
    cmd = [
        sys.executable, "upload_video.py",
        "--file", video_path,
        "--title", shorts["title"][:100],
        "--description", shorts["description"][:5000],
        "--privacyStatus", "public"  # Breaking news는 즉시 공개
    ]
    
    thumbnail = shorts.get("thumbnail")
    if thumbnail and Path(thumbnail).exists():
        cmd.extend(["--thumbnail", thumbnail])
    
    subtitles = shorts.get("subtitles", {})
    subtitle_files = [f for f in subtitles.values() if Path(f).exists()]
    if subtitle_files:
        cmd.extend(["--subtitles", ",".join(subtitle_files)])
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        log(f"[FAIL] Upload failed with code {result.returncode}")
        return False
    else:
        log("[OK] Breaking News uploaded successfully!")
        return True


def main():
    # Check if already running
    if LOCK_FILE.exists():
        # Check if lock is stale (older than 30 minutes)
        lock_age = datetime.now().timestamp() - LOCK_FILE.stat().st_mtime
        if lock_age < 1800:  # 30 minutes
            print(f"[SKIP] Breaking news generator already running (lock age: {lock_age/60:.1f}min)")
            return
        else:
            print(f"[WARN] Stale lock detected ({lock_age/60:.1f}min), removing...")
            LOCK_FILE.unlink()
    
    # Create lock file
    LOCK_FILE.touch()
    atexit.register(cleanup_lock)
    
    log(f"\n{'='*60}")
    log(f"Breaking News Detector")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    # [1/4] Detect breaking news (8+ sources required)
    log("[1/4] Scanning RSS feeds for breaking news...")
    breaking = detect_breaking_news(min_sources=8)
    
    if not breaking:
        log("[INFO] No breaking news detected. Exiting.")
        sys.exit(2)  # Exit code 2 = no breaking news (not an error, just nothing to do)
    
    log(f"\n[CANDIDATE] Detected: {breaking['title']}")
    log(f"[CANDIDATE] Category: {breaking.get('category', 'Unknown')}")
    log(f"[CANDIDATE] Source: {breaking.get('source', 'Unknown')}")
    log(f"[CANDIDATE] Sources count: {breaking.get('source_count', 'Unknown')}")
    
    # [2/4] GPT 검증
    log("\n[2/4] GPT verification...")
    verification = verify_breaking_news_with_gpt(
        title=breaking['title'],
        description=breaking.get('description', ''),
        source_count=breaking.get('source_count', 8)
    )
    
    if not verification.get('is_breaking', False):
        log(f"\n[SKIP] GPT rejected as not breaking news: {verification.get('reason', 'Unknown')}")
        sys.exit(2)  # Exit code 2 = no breaking news
    
    log("\n[VERIFIED] GPT confirmed this is breaking news!")
    
    if dry_run:
        log("\n[DRY-RUN] Would generate Shorts video. Exiting.")
        return
    
    # Gather more details from multiple sources
    log(f"\n[BREAKING] Gathering details for: {breaking['title'][:50]}...")
    related = fetch_breaking_news_details(breaking)
    log(f"  [OK] Gathered {len(related)} sources")
    
    # Save breaking news to temp file for news_dual.py
    temp_file = Path(__file__).parent / "temp_breaking_news.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump({
            "main": breaking,
            "related": related
        }, f, ensure_ascii=False, indent=2)
    
    log(f"\n[INFO] Saved breaking news to {temp_file}")
    
    # [3/4] Generate Shorts video
    log("\n" + "=" * 60)
    log("[3/4] Generating Breaking News Shorts...")
    log("=" * 60)
    
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "news_dual.py"),
        "--count", "1",
        "--shorts-only",
        "--breaking-news", str(temp_file),
        "--voice", "marin",  # Breaking news는 marin 보이스
        "--output", "./output"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=Path(__file__).parent)
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        log(f"[ERROR] Generation failed with code {result.returncode}")
        # Cleanup temp file
        if temp_file.exists():
            temp_file.unlink()
        sys.exit(1)
    
    log("[OK] Breaking News Shorts generated successfully!")
    
    # Find the generated summary file
    output_dir = Path(__file__).parent / "output"
    summaries = sorted(output_dir.glob("*_summary.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not summaries:
        log("[FAIL] No summary file found")
        if temp_file.exists():
            temp_file.unlink()
        sys.exit(1)
    
    with open(summaries[0], 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # [4/4] Upload to YouTube
    success = upload_shorts(summary)
    
    # Cleanup temp file
    if temp_file.exists():
        temp_file.unlink()
    
    if not success:
        sys.exit(1)
    
    # 최종 JSON 요약 출력 (n8n 파싱용)
    shorts = summary.get("shorts", {})
    json_summary = {
        "status": "success",
        "title": shorts.get("title", ""),
        "description": shorts.get("description", ""),
        "video": shorts.get("video", ""),
        "api": "OpenAI GPT-4",
        "type": "breaking_news"
    }
    print("\n[JSON_SUMMARY]")
    print(json.dumps(json_summary, ensure_ascii=False))
    print("[/JSON_SUMMARY]")


if __name__ == "__main__":
    main()
