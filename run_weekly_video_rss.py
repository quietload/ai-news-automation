#!/usr/bin/env python3
"""
Weekly Video Runner (RSS version)
==================================
Generates and uploads weekly news video using RSS feeds (real-time, no delay).
Runs Saturday at 20:00 KST, publishes at 21:00 KST.

Usage:
    python run_weekly_video_rss.py
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
LOG_FILE = LOG_DIR / f"weekly_rss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def get_publish_time() -> str:
    """KST 일요일 낮 12시 예약 게시"""
    now = datetime.now(KST)
    publish_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # 다음 일요일 찾기
    days_until_sunday = (6 - now.weekday()) % 7 + 1
    if days_until_sunday == 7 and now.hour < 12:
        days_until_sunday = 0
    publish_time += timedelta(days=days_until_sunday)
    
    return publish_time.isoformat()


def run_video():
    log("=" * 60)
    log("[1/2] Generating Weekly Video with RSS (16 news)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "16", "--video-only", "--by-category", "--use-rss", "--output", "./output"],
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


def upload_video(summary: dict):
    log("=" * 60)
    log("[2/2] Uploading to YouTube (scheduled)...")
    log("=" * 60)
    
    video = summary.get("video")
    if not video:
        log("[FAIL] No video in summary")
        return
    
    video_path = video.get("video")
    if not video_path or not Path(video_path).exists():
        log(f"[FAIL] Video not found: {video_path}")
        return
    
    publish_time = get_publish_time()
    log(f"  Publish time: {publish_time}")
    
    cmd = [
        sys.executable, "upload_video.py",
        "--file", video_path,
        "--title", video["title"][:100],
        "--description", video["description"][:5000],
        "--privacyStatus", "private",
        "--publish-at", publish_time
    ]
    
    thumbnail = video.get("thumbnail")
    if thumbnail and Path(thumbnail).exists():
        cmd.extend(["--thumbnail", thumbnail])
    
    subtitles = video.get("subtitles", {})
    subtitle_files = [f for f in subtitles.values() if Path(f).exists()]
    if subtitle_files:
        cmd.extend(["--subtitles", ",".join(subtitle_files)])
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        log(f"[FAIL] Upload failed with code {result.returncode}")
        sys.exit(1)
    else:
        log("[OK] Upload scheduled successfully!")


def main():
    log(f"\n{'='*60}")
    log(f"Weekly Video Runner (RSS - Real-time)")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    try:
        summary = run_video()
        if summary:
            upload_video(summary)
        else:
            log("[FAIL] No video generated")
            sys.exit(1)
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
