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
    log("[1/2] Generating Weekly Video (13 categories)...")
    log("=" * 60)
    
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "13", "--video-only", "--by-category", "--output", "./output"],
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


def upload_video(video_path: str, title: str, description: str, publish_at: str = None) -> str:
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
    
    # 예약 게시 설정
    if publish_at:
        cmd.extend(["--publish-at", publish_at])
        log(f"  [OK] Scheduled publish at: {publish_at}")
    
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


def upload_thumbnail(video_id: str, thumbnail_path: str) -> bool:
    if not video_id or not thumbnail_path or not Path(thumbnail_path).exists():
        return False
    
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from oauth2client.file import Storage
        import httplib2
        
        storage = Storage(str(Path(__file__).parent / "upload_video.py-oauth2.json"))
        credentials = storage.get()
        
        if credentials and not credentials.invalid:
            youtube = build("youtube", "v3", http=credentials.authorize(httplib2.Http()))
            request = youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png")
            )
            request.execute()
            log(f"  [OK] Thumbnail uploaded")
            return True
    except Exception as e:
        log(f"  [WARN] Thumbnail failed: {e}")
    return False


def upload_captions(video_id: str, srt_dir: str, prefix: str) -> bool:
    result = subprocess.run(
        [sys.executable, "upload_captions.py",
         "--video-id", video_id,
         "--srt-dir", srt_dir,
         "--prefix", prefix],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(f"Caption STDERR: {result.stderr}")
    return result.returncode == 0


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
        ts = summary["timestamp"]
        
        log("\n" + "=" * 60)
        log("[2/2] Uploading Video to YouTube...")
        log("=" * 60)
        
        video_id = upload_video(video["video"], video["title"], video["description"], publish_at)
        
        if video_id:
            log(f"[OK] Video uploaded! ID: {video_id}")
            
            if video.get("thumbnail"):
                upload_thumbnail(video_id, video["thumbnail"])
            
            log("  Uploading captions...")
            upload_captions(video_id, "output", f"{ts}_video")
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
