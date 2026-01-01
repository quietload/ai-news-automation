#!/usr/bin/env python3
"""
Daily Shorts Runner
===================
Generates and uploads daily news shorts (8 news, ~60 seconds).
Runs Mon-Fri at 17:00 KST, publishes at 18:00 KST.

Usage:
    python run_daily_shorts.py
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
LOG_FILE = LOG_DIR / f"shorts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def get_publish_time() -> str:
    """KST 오후 9시 예약 게시"""
    now = datetime.now(KST)
    publish_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
    
    # 이미 6시가 지났으면 내일 6시
    if now >= publish_time:
        publish_time += timedelta(days=1)
    
    return publish_time.isoformat()


def run_shorts():
    log("=" * 60)
    log("[1/2] Generating Shorts (7 news, max 60 seconds)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "7", "--shorts-only", "--output", "./output"],
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
    log("*  DAILY SHORTS PIPELINE")
    log("*" * 60)
    log(f"*  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"*  Log: {LOG_FILE}")
    log("*" * 60)
    
    # 예약 게시 시간 계산
    publish_at = get_publish_time()
    log(f"*  Scheduled Publish: {publish_at}")
    log("*" * 60)
    
    try:
        summary = run_shorts()
        if not summary or "shorts" not in summary:
            log("[FAIL] No shorts generated")
            sys.exit(1)
        
        shorts = summary["shorts"]
        
        log("\n" + "=" * 60)
        log("[2/2] Uploading Shorts to YouTube...")
        log("=" * 60)
        
        video_id = upload_video(
            video_path=shorts["video"],
            title=shorts["title"],
            description=shorts["description"],
            thumbnail=shorts.get("thumbnail"),
            subtitles=shorts.get("subtitles"),
            publish_at=publish_at
        )
        
        if video_id:
            log(f"[OK] Shorts uploaded! ID: {video_id}")
            log(f"[OK] URL: https://youtube.com/watch?v={video_id}")
        else:
            log("[FAIL] Shorts upload failed")
            sys.exit(1)
        
        log("\n" + "=" * 60)
        log("[OK] Daily Shorts Complete!")
        log("=" * 60)
        
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
