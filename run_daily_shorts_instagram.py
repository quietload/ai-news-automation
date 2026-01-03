#!/usr/bin/env python3
"""
Daily Shorts Runner (YouTube + Instagram)
==========================================
Generates and uploads daily news shorts to YouTube and Instagram.

Usage:
    python run_daily_shorts_instagram.py
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
LOG_FILE = LOG_DIR / f"shorts_ig_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def run_shorts():
    log("=" * 60)
    log("[1/3] Generating Shorts (8 news, max 60 seconds)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "8", "--shorts-only", "--output", "./output"],
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


def upload_to_youtube(video_path: str, title: str, description: str, 
                      thumbnail: str = None, subtitles: dict = None) -> str:
    """Upload to YouTube (public immediately)"""
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
    
    if thumbnail and Path(thumbnail).exists():
        cmd.extend(["--thumbnail", thumbnail])
    
    if subtitles:
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
    
    if result.returncode != 0:
        log(f"[FAIL] YouTube upload failed")
        log(result.stderr if result.stderr else result.stdout)
        return None
    
    log("[OK] YouTube upload successful")
    return "success"


def upload_to_instagram(video_path: str, caption: str, video_url: str = None) -> str:
    """Upload to Instagram Reels"""
    
    # Check if Instagram is configured
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.environ.get("INSTAGRAM_ACCESS_TOKEN"):
        log("[SKIP] Instagram not configured (no INSTAGRAM_ACCESS_TOKEN)")
        return None
    
    if not video_url:
        log("[SKIP] Instagram requires public video URL")
        log("  Set PUBLIC_VIDEO_URL_BASE in .env or upload video to cloud storage")
        return None
    
    cmd = [
        sys.executable, "upload_instagram.py",
        "--video-url", video_url,
        "--caption", caption[:2200]
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    if result.returncode != 0:
        log(f"[FAIL] Instagram upload failed")
        log(result.stderr if result.stderr else result.stdout)
        return None
    
    log("[OK] Instagram upload successful")
    return "success"


def main():
    log(f"\n{'='*60}")
    log(f"Daily Shorts Runner (YouTube + Instagram)")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    try:
        # Generate shorts
        summary = run_shorts()
        if not summary:
            log("[FAIL] No shorts generated")
            return
        
        shorts = summary.get("shorts")
        if not shorts:
            log("[FAIL] No shorts in summary")
            return
        
        news_list = summary.get("news", [])
        
        # Upload to YouTube
        log("\n" + "=" * 60)
        log("[2/3] Uploading to YouTube...")
        log("=" * 60)
        
        upload_to_youtube(
            shorts["video"],
            shorts["title"],
            shorts["description"],
            shorts.get("thumbnail"),
            shorts.get("subtitles")
        )
        
        # Upload to Instagram
        log("\n" + "=" * 60)
        log("[3/3] Uploading to Instagram...")
        log("=" * 60)
        
        # Generate Instagram caption
        from upload_instagram import generate_instagram_caption
        ig_caption = generate_instagram_caption(news_list, is_weekly=False)
        
        # Instagram needs public URL - check if configured
        public_url_base = os.environ.get("PUBLIC_VIDEO_URL_BASE")
        if public_url_base:
            video_filename = Path(shorts["video"]).name
            video_url = f"{public_url_base}/{video_filename}"
            upload_to_instagram(shorts["video"], ig_caption, video_url)
        else:
            log("[SKIP] Instagram: Set PUBLIC_VIDEO_URL_BASE in .env")
        
        log(f"\n{'='*60}")
        log("[OK] Complete!")
        log(f"{'='*60}")
        
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())


if __name__ == "__main__":
    main()
