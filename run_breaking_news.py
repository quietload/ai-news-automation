#!/usr/bin/env python3
"""
Breaking News Detector & Shorts Generator
==========================================

RSS 피드 스캔하여 속보 감지 및 Shorts 자동 생성.

Trigger:
    - Breaking 키워드 포함 (breaking, dies, war, earthquake, etc.)
    - 5개 이상 소스에서 동일 뉴스 발견

Flow:
    1. detect_breaking_news(min_sources=5) 호출
    2. 속보 발견 시 fetch_breaking_news_details() 로 상세 수집
    3. news_dual.py --breaking-news 로 Shorts 생성
    4. YouTube 즉시 업로드

Usage:
    python run_breaking_news.py              # 감지 & 생성
    python run_breaking_news.py --dry-run    # 감지만 (생성 안함)

Schedule:
    n8n에서 10분마다 실행
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from news_rss import detect_breaking_news, fetch_breaking_news_details

KST = ZoneInfo("Asia/Seoul")
LOG_FILE = Path(__file__).parent / "logs" / f"breaking_{datetime.now(KST).strftime('%Y%m%d')}.log"
LOG_FILE.parent.mkdir(exist_ok=True)


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now(KST).strftime('%H:%M:%S')} {msg}\n")


def main():
    log(f"\n{'='*60}")
    log(f"Breaking News Detector")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    # Detect breaking news
    breaking = detect_breaking_news(min_sources=5)
    
    if not breaking:
        log("[INFO] No breaking news detected. Exiting.")
        return
    
    log(f"\n[BREAKING] Detected: {breaking['title']}")
    log(f"[BREAKING] Category: {breaking.get('category', 'Unknown')}")
    log(f"[BREAKING] Source: {breaking.get('source', 'Unknown')}")
    
    if dry_run:
        log("\n[DRY-RUN] Would generate Shorts video. Exiting.")
        return
    
    # Gather more details from multiple sources
    related = fetch_breaking_news_details(breaking)
    
    # Save breaking news to temp file for news_dual.py
    import json
    temp_file = Path(__file__).parent / "temp_breaking_news.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump({
            "main": breaking,
            "related": related
        }, f, ensure_ascii=False, indent=2)
    
    log(f"\n[INFO] Saved breaking news to {temp_file}")
    
    # Generate Shorts video
    log("\n[INFO] Generating Breaking News Shorts...")
    
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "news_dual.py"),
        "--count", "1",
        "--shorts-only",
        "--breaking-news", str(temp_file)
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        log("[OK] Breaking News Shorts generated successfully!")
    else:
        log(f"[ERROR] Generation failed with code {result.returncode}")
    
    # Cleanup temp file
    if temp_file.exists():
        temp_file.unlink()


if __name__ == "__main__":
    main()
