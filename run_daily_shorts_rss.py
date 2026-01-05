#!/usr/bin/env python3
"""
Daily Shorts Runner - Evening (RSS version)
============================================
Generates and uploads daily news shorts for Korean audience.
Runs daily at 20:50 KST, publishes at 21:00 KST (Korea primetime).

Usage:
    python run_daily_shorts_rss.py
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
LOG_FILE = LOG_DIR / f"shorts_rss_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('utf-8', errors='replace').decode('utf-8'))
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def get_publish_time() -> str:
    """KST 오후 10시 예약 게시 (한국 프라임타임)"""
    now = datetime.now(KST)
    publish_time = now.replace(hour=22, minute=0, second=0, microsecond=0)
    
    if now.hour >= 22:
        publish_time += timedelta(days=1)
    
    return publish_time.isoformat()


def run_shorts():
    log("=" * 60)
    log("[1/2] Generating Shorts with RSS (6 news, max 60 seconds)...")
    log("=" * 60)
    
    # 오후(저녁)는 cedar 목소리
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "6", "--shorts-only", "--use-rss", "--voice", "cedar", "--output", "./output"],
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
        log(f"[FAIL] news_dual.py failed with code {result.returncode}")
        return None
    
    output_dir = Path(__file__).parent / "output"
    summaries = sorted(output_dir.glob("*_summary.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not summaries:
        log("[FAIL] No summary file found")
        return None
    
    with open(summaries[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def upload_shorts(summary: dict):
    log("=" * 60)
    log("[2/2] Uploading to YouTube (scheduled)...")
    log("=" * 60)
    
    shorts = summary.get("shorts")
    if not shorts:
        log("[FAIL] No shorts in summary")
        return
    
    video_path = shorts.get("video")
    if not video_path or not Path(video_path).exists():
        log(f"[FAIL] Video not found: {video_path}")
        return
    
    publish_time = get_publish_time()
    log(f"  Publish time: {publish_time}")
    
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
        "--privacyStatus", "private",
        "--publish-at", publish_time
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
        sys.exit(1)
    else:
        log("[OK] Upload scheduled successfully!")


def main():
    log(f"\n{'='*60}")
    log(f"Daily Shorts Runner (RSS - Real-time)")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    try:
        summary = run_shorts()
        if summary:
            upload_shorts(summary)
        else:
            log("[FAIL] No shorts generated")
            sys.exit(1)
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
