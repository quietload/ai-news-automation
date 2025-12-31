#!/usr/bin/python
"""
YouTube Video & Caption Upload Script
=====================================
Uploads video and multi-language subtitles to YouTube.
Supports scheduled publishing with thumbnail upload.

Usage:
    python upload_video.py --file video.mp4 --title "Title" --subtitles subs_en.srt,subs_ko.srt
"""

import httplib2
import http.client
import os
import random
import sys
import time
import json
import argparse

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser as oauth_argparser

# =============================================================================
# CONFIGURATION
# =============================================================================

httplib2.RETRIES = 1
MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secrets.json")
OAUTH_STORAGE_FILE = os.path.join(os.path.dirname(__file__), "upload_video.py-oauth2.json")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube"
]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Language code mapping for subtitles
LANGUAGE_NAMES = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish"
}

MISSING_CLIENT_SECRETS_MESSAGE = f"""
WARNING: OAuth 2.0 setup required.

{CLIENT_SECRETS_FILE} file is required.

1. Go to https://console.cloud.google.com/
2. Create or select a project
3. Enable YouTube Data API v3
4. Create OAuth client ID (Desktop app)
5. Download JSON as client_secrets.json
"""

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_authenticated_service(args):
    """Create authenticated YouTube service"""
    flow = flow_from_clientsecrets(
        CLIENT_SECRETS_FILE,
        scope=YOUTUBE_SCOPES,
        message=MISSING_CLIENT_SECRETS_MESSAGE
    )

    storage = Storage(OAUTH_STORAGE_FILE)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http())
    )


# =============================================================================
# VIDEO UPLOAD
# =============================================================================

def initialize_upload(youtube, options):
    """Start video upload - uploads as unlisted first if scheduled"""
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    # 예약 게시가 있으면 먼저 unlisted로 업로드 (썸네일 업로드를 위해)
    has_schedule = hasattr(options, 'publishAt') and options.publishAt
    
    if has_schedule:
        # 먼저 unlisted로 업로드
        status_dict = {"privacyStatus": "unlisted"}
        print(f"[INFO] Uploading as unlisted first (for thumbnail)")
    else:
        status_dict = {"privacyStatus": options.privacyStatus}

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category,
            defaultLanguage="en",
            defaultAudioLanguage="en"
        ),
        status=status_dict
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    result = resumable_upload(insert_request)
    
    # 예약 정보 저장 (나중에 설정하기 위해)
    if has_schedule and result.get("status") == "success":
        result["scheduled_publish_at"] = options.publishAt
    
    return result


def resumable_upload(insert_request):
    """Upload with retry logic"""
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            print("Uploading video...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"[OK] Upload successful! Video ID: {video_id}")
                    print(f"[OK] URL: https://youtube.com/watch?v={video_id}")
                    return {
                        "video_id": video_id,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "status": "success"
                    }
                else:
                    print(f"Upload failed: {response}")
                    return {"status": "failed", "error": str(response)}
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"Retriable HTTP error {e.resp.status}: {e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"Retriable error: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                print("Max retries exceeded")
                return {"status": "failed", "error": "Max retries exceeded"}

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Retrying in {sleep_seconds:.1f}s...")
            time.sleep(sleep_seconds)

    return {"status": "failed", "error": "Unknown error"}


# =============================================================================
# THUMBNAIL UPLOAD
# =============================================================================

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Upload thumbnail to video"""
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        print(f"[WARN] Thumbnail file not found: {thumbnail_path}")
        return False
    
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/png")
        ).execute()
        print(f"[OK] Thumbnail uploaded")
        return True
    except HttpError as e:
        print(f"[FAIL] Thumbnail upload failed: {e}")
        return False


# =============================================================================
# SCHEDULE VIDEO (after thumbnail upload)
# =============================================================================

def schedule_video(youtube, video_id, publish_at):
    """Set video to private with scheduled publish time"""
    try:
        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {
                    "privacyStatus": "private",
                    "publishAt": publish_at
                }
            }
        ).execute()
        print(f"[OK] Scheduled publish: {publish_at}")
        return True
    except HttpError as e:
        print(f"[FAIL] Schedule failed: {e}")
        return False


# =============================================================================
# CAPTION UPLOAD
# =============================================================================

def upload_caption(youtube, video_id, caption_file, language_code):
    """Upload a single caption file to a video"""
    
    if not os.path.exists(caption_file):
        print(f"[WARN] Caption file not found: {caption_file}")
        return None
    
    language_name = LANGUAGE_NAMES.get(language_code, language_code)
    
    try:
        insert_result = youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": language_code,
                    "name": language_name,
                    "isDraft": False
                }
            },
            media_body=MediaFileUpload(caption_file, mimetype="application/octet-stream")
        ).execute()
        
        caption_id = insert_result.get("id")
        print(f"[OK] Caption uploaded: {language_name} ({language_code}) - ID: {caption_id}")
        return caption_id
        
    except HttpError as e:
        error_content = e.content.decode() if hasattr(e.content, 'decode') else str(e.content)
        print(f"[FAIL] Caption upload failed ({language_code}): {error_content}")
        return None


def upload_captions(youtube, video_id, subtitle_files):
    """Upload multiple caption files"""
    
    results = {}
    
    if isinstance(subtitle_files, str):
        files = [f.strip() for f in subtitle_files.split(",") if f.strip()]
        
        for filepath in files:
            filename = os.path.basename(filepath)
            lang_code = None
            
            for lang in LANGUAGE_NAMES.keys():
                if f"_{lang}." in filename or f"_{lang}_" in filename or filename.endswith(f"_{lang}.srt"):
                    lang_code = lang
                    break
            
            if lang_code is None:
                parts = filename.replace(".srt", "").split("_")
                for part in parts:
                    if part in LANGUAGE_NAMES:
                        lang_code = part
                        break
            
            if lang_code:
                caption_id = upload_caption(youtube, video_id, filepath, lang_code)
                if caption_id:
                    results[lang_code] = caption_id
            else:
                print(f"[WARN] Could not detect language for: {filename}")
    
    elif isinstance(subtitle_files, dict):
        for lang_code, filepath in subtitle_files.items():
            caption_id = upload_caption(youtube, video_id, filepath, lang_code)
            if caption_id:
                results[lang_code] = caption_id
    
    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="YouTube Video & Caption Upload",
        parents=[oauth_argparser],
        conflict_handler='resolve'
    )
    parser.add_argument("--file", required=True, help="Video file to upload")
    parser.add_argument("--title", default="Test Title", help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--category", default="25", help="Category ID (25=News)")
    parser.add_argument("--keywords", default="", help="Keywords (comma-separated)")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                        default="public", help="Privacy status")
    parser.add_argument("--publish-at", dest="publishAt", default=None,
                        help="Scheduled publish time (ISO 8601)")
    parser.add_argument("--thumbnail", default=None, help="Thumbnail image file")
    parser.add_argument("--subtitles", default=None,
                        help="Subtitle files (comma-separated)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        sys.exit(1)

    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(MISSING_CLIENT_SECRETS_MESSAGE)
        sys.exit(1)

    youtube = get_authenticated_service(args)
    
    try:
        # 1. Upload video (unlisted if scheduled)
        result = initialize_upload(youtube, args)
        
        if result.get("status") != "success":
            print(json.dumps(result))
            sys.exit(1)
        
        video_id = result["video_id"]
        
        # 2. Upload thumbnail (while unlisted)
        if args.thumbnail:
            upload_thumbnail(youtube, video_id, args.thumbnail)
        
        # 3. Upload captions
        if args.subtitles:
            print(f"\n[INFO] Uploading captions...")
            caption_results = upload_captions(youtube, video_id, args.subtitles)
            result["captions"] = caption_results
            if caption_results:
                print(f"[OK] {len(caption_results)} caption(s) uploaded")
        
        # 4. Set schedule (changes from unlisted to private with publishAt)
        if result.get("scheduled_publish_at"):
            schedule_video(youtube, video_id, result["scheduled_publish_at"])
        
        # JSON output
        print(json.dumps(result))
        
    except HttpError as e:
        print(f"HTTP error {e.resp.status}: {e.content}")
        sys.exit(1)
