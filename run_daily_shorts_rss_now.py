#!/usr/bin/env python3
"""
Daily Shorts Runner - RSS Immediate
====================================
Generates and uploads shorts immediately using RSS feeds.

Usage:
    python run_daily_shorts_rss_now.py
"""

import os
import sys
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"shorts_rss_now_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def run_shorts():
    log("=" * 60)
    log("[1/2] Generating Shorts with RSS (10 news)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "10", "--shorts-only", "--use-rss", "--output", "./output"],
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


def upload_shorts(summary: dict):
    log("=" * 60)
    log("[2/2] Uploading to YouTube (public)...")
    log("=" * 60)
    
    shorts = summary.get("shorts")
    if not shorts:
        log("[FAIL] No shorts in summary")
        return
    
    video_path = shorts.get("video")
    if not video_path or not Path(video_path).exists():
        log(f"[FAIL] Video not found: {video_path}")
        return
    
    cmd = [
        sys.executable, "upload_video.py",
        "--file", video_path,
        "--title", shorts["title"][:100],
        "--description", shorts["description"][:5000],
        "--privacyStatus", "public"
    ]
    
    thumbnail = shorts.get("thumbnail")
    if thumbnail and Path(thumbnail).exists():
        cmd.extend(["--thumbnail", thumbnail])
    
    subtitles = shorts.get("subtitles", {})
    subtitle_files = [f for f in subtitles.values() if Path(f).exists()]
    if subtitle_files:
        cmd.extend(["--subtitles", ",".join(subtitle_files)])
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent, capture_output=True, text=True)
    
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        log(f"[FAIL] Upload failed")
    else:
        log("[OK] Upload complete!")


def main():
    log(f"\n{'='*60}")
    log(f"Daily Shorts (RSS) - Immediate Upload")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    try:
        summary = run_shorts()
        if summary:
            upload_shorts(summary)
        else:
            log("[FAIL] No shorts generated")
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())


if __name__ == "__main__":
    main()
