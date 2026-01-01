#!/usr/bin/env python3
"""
Weekly Video Runner
===================
Generates and uploads weekly news video (13 news by category, ~3 minutes).
Runs Saturday at 17:00 KST, publishes at 18:00 KST.

Usage:
    python run_weekly_video.py
"""

import os
import sys
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Logging setup
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"weekly_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def get_publish_time() -> str:
    """KST 토요일 오후 6시 예약 게시"""
    now = datetime.now(KST)
    publish_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    # 다음 토요일 찾기
    days_until_saturday = (5 - now.weekday()) % 7  # 5 = 토요일
    if days_until_saturday == 0 and now.hour >= 18:
        days_until_saturday = 7
    
    publish_time += timedelta(days=days_until_saturday)
    
    return publish_time.isoformat()


def run_video():
    log("=" * 60)
    log("[1/2] Generating Weekly Video (8 categories x 2 = 16 news)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "16", "--video-only", "--by-category", "--output", "./output"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        log(f"[FAIL] news_dual.py failed with code {result.returncode}")
        return None
    
    output_dir = Path(__file__).parent / "output"
    summaries = sorted(output_dir.glob("*_summary.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not summaries:
        log("[FAIL] No summary file found")
        return None
    
    with open(summaries[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def upload_video(video_path: str, title: str, description: str, 
                 thumbnail: str = None, subtitles: dict = None, 
                 publish_at: str = None) -> str:
    """Upload video with thumbnail, captions, and schedule"""
    if not video_path or not Path(video_path).exists():
        log(f"[FAIL] Video not found: {video_path}")
        return None
    
    cmd = [
        sys.executable, "upload_video.py",
        "--file", video_path,
        "--title", title[:100],
        "--description", description[:5000],
        "--privacyStatus", "public"
    ]
    
    # 썸네일
    if thumbnail and Path(thumbnail).exists():
        cmd.extend(["--thumbnail", thumbnail])
        log(f"  [INFO] Thumbnail: {thumbnail}")
    
    # 자막 (쉼표로 구분된 파일 경로)
    if subtitles:
        srt_files = ",".join(subtitles.values())
        cmd.extend(["--subtitles", srt_files])
        log(f"  [INFO] Subtitles: {len(subtitles)} languages")
    
    # 예약 게시 설정
    if publish_at:
        cmd.extend(["--publish-at", publish_at])
        log(f"  [INFO] Scheduled: {publish_at}")
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"Upload STDERR: {result.stderr}")
    
    if result.returncode == 0:
        import re
        match = re.search(r'"video_id":\s*"([^"]+)"', result.stdout)
        if not match:
            match = re.search(r'"id":\s*"([^"]+)"', result.stdout)
        if match:
            return match.group(1)
    return None


def main():
    log("\n")
    log("*" * 60)
    log("*  WEEKLY VIDEO PIPELINE")
    log("*  Saturday - 13 Categories News")
    log("*" * 60)
    log(f"*  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"*  Log: {LOG_FILE}")
    log("*" * 60)
    
    # 예약 게시 시간 계산
    publish_at = get_publish_time()
    log(f"*  Scheduled Publish: {publish_at}")
    log("*" * 60)
    
    try:
        summary = run_video()
        if not summary or "video" not in summary:
            log("[FAIL] No video generated")
            sys.exit(1)
        
        video = summary["video"]
        
        log("\n" + "=" * 60)
        log("[2/2] Uploading Video to YouTube...")
        log("=" * 60)
        
        video_id = upload_video(
            video_path=video["video"],
            title=video["title"],
            description=video["description"],
            thumbnail=video.get("thumbnail"),
            subtitles=video.get("subtitles"),
            publish_at=publish_at
        )
        
        if video_id:
            log(f"[OK] Video uploaded! ID: {video_id}")
            log(f"[OK] URL: https://youtube.com/watch?v={video_id}")
        else:
            log("[FAIL] Video upload failed")
            sys.exit(1)
        
        log("\n" + "=" * 60)
        log("[OK] Weekly Video Complete!")
        log("=" * 60)
        
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
