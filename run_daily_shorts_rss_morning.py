#!/usr/bin/env python3
"""
Daily Shorts Runner - Noon (RSS version)
=========================================
Generates and uploads daily news shorts for US audience.
Runs daily at 11:00 KST, publishes at 12:00 KST (US East 10PM / West 7PM previous day).

Usage:
    python run_daily_shorts_rss_morning.py
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
LOG_FILE = LOG_DIR / f"shorts_rss_morning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

KST = ZoneInfo("Asia/Seoul")


def log(msg):
    """Log to console and file"""
    # 콘솔 출력 (이모지 제거)
    safe_msg = msg.encode('ascii', errors='ignore').decode('ascii')
    print(safe_msg)
    # 파일에는 원본 저장
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


def get_publish_time() -> str:
    """KST 11시 예약 게시"""
    now = datetime.now(KST)
    publish_time = now.replace(hour=11, minute=0, second=0, microsecond=0)
    
    if now.hour >= 11:
        publish_time += timedelta(days=1)
    
    return publish_time.isoformat()


def run_shorts():
    log("=" * 60)
    log("[1/2] Generating Morning Shorts with RSS (6 news)...")
    log("=" * 60)
    
    # 오전(모닝)은 marin 목소리
    result = subprocess.run(
        [sys.executable, "news_dual.py", "--count", "6", "--shorts-only", "--use-rss", "--voice", "marin", "--output", "./output"],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        encoding='utf-8'
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
    log("[2/2] Uploading to YouTube (scheduled for US primetime)...")
    log("=" * 60)
    
    shorts = summary.get("shorts")
    if not shorts:
        log("[FAIL] No shorts in summary")
        return
    
    video_path = shorts.get("video")
    # 상대경로를 절대경로로 변환
    if video_path:
        video_path = Path(__file__).parent / video_path
    if not video_path or not video_path.exists():
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
        "--file", str(video_path),
        "--title", shorts["title"][:100],
        "--description", shorts["description"][:5000],
        "--privacyStatus", "private",
        "--publish-at", publish_time
    ]
    
    subtitles = shorts.get("subtitles", {})
    subtitle_files = [str(Path(__file__).parent / f) for f in subtitles.values() if (Path(__file__).parent / f).exists()]
    if subtitle_files:
        cmd.extend(["--subtitles", ",".join(subtitle_files)])
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        encoding='utf-8'
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
    log(f"Daily Shorts Runner - Noon (US Primetime)")
    log(f"Time: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    log(f"{'='*60}\n")
    
    try:
        summary = run_shorts()
        if summary:
            upload_shorts(summary)
            
            # 최종 JSON 요약 출력 (n8n 파싱용)
            shorts = summary.get("shorts", {})
            json_summary = {
                "status": "success",
                "title": shorts.get("title", ""),
                "description": shorts.get("description", ""),
                "video": shorts.get("video", ""),
                "api": "OpenAI GPT-4"
            }
            print("\n[JSON_SUMMARY]")
            print(json.dumps(json_summary, ensure_ascii=False))
            print("[/JSON_SUMMARY]")
        else:
            log("[FAIL] No shorts generated")
            sys.exit(1)
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
