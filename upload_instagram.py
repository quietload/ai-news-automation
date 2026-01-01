#!/usr/bin/env python3
"""
Instagram Reels Upload Script
=============================
Uploads video reels to Instagram using Graph API.

Requirements:
- Instagram Business/Creator account
- Facebook Page linked to Instagram
- Meta Developer App with instagram_content_publish permission

Setup:
1. Create Meta App: https://developers.facebook.com/apps/
2. Add Instagram Graph API product
3. Get Access Token with permissions:
   - instagram_basic
   - instagram_content_publish
   - pages_read_engagement
4. Add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID to .env

Usage:
    python upload_instagram.py --file video.mp4 --caption "Your caption"
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID")
GRAPH_API_URL = "https://graph.facebook.com/v18.0"

# =============================================================================
# INSTAGRAM UPLOAD FUNCTIONS
# =============================================================================

def get_instagram_account_id(access_token: str) -> str:
    """Get Instagram Business Account ID from Facebook Page"""
    # First get Facebook Pages
    response = requests.get(
        f"{GRAPH_API_URL}/me/accounts",
        params={"access_token": access_token}
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to get Facebook pages: {response.text}")
    
    pages = response.json().get("data", [])
    if not pages:
        raise Exception("No Facebook pages found. Link a page to your Instagram account.")
    
    # Get Instagram account from first page
    page_id = pages[0]["id"]
    page_token = pages[0]["access_token"]
    
    response = requests.get(
        f"{GRAPH_API_URL}/{page_id}",
        params={
            "fields": "instagram_business_account",
            "access_token": page_token
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to get Instagram account: {response.text}")
    
    ig_account = response.json().get("instagram_business_account", {})
    if not ig_account:
        raise Exception("No Instagram Business account linked to Facebook page.")
    
    return ig_account["id"]


def upload_reel(video_url: str, caption: str, 
                cover_url: str = None,
                share_to_feed: bool = True) -> dict:
    """
    Upload a Reel to Instagram
    
    Note: Video must be hosted on a public URL (Instagram fetches it)
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        raise Exception("INSTAGRAM_ACCESS_TOKEN not set in .env")
    
    if not INSTAGRAM_ACCOUNT_ID:
        raise Exception("INSTAGRAM_ACCOUNT_ID not set in .env")
    
    print(f"[1/3] Creating media container...")
    
    # Step 1: Create media container
    container_params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": share_to_feed,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    
    if cover_url:
        container_params["cover_url"] = cover_url
    
    response = requests.post(
        f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/media",
        data=container_params
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create container: {response.text}")
    
    container_id = response.json().get("id")
    print(f"  [OK] Container ID: {container_id}")
    
    # Step 2: Wait for video processing
    print(f"[2/3] Waiting for video processing...")
    max_attempts = 30
    for attempt in range(max_attempts):
        response = requests.get(
            f"{GRAPH_API_URL}/{container_id}",
            params={
                "fields": "status_code,status",
                "access_token": INSTAGRAM_ACCESS_TOKEN
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to check status: {response.text}")
        
        status = response.json()
        status_code = status.get("status_code")
        
        if status_code == "FINISHED":
            print(f"  [OK] Video processed")
            break
        elif status_code == "ERROR":
            raise Exception(f"Video processing failed: {status}")
        else:
            print(f"  [WAIT] Status: {status_code} ({attempt+1}/{max_attempts})")
            time.sleep(10)
    else:
        raise Exception("Video processing timeout")
    
    # Step 3: Publish the reel
    print(f"[3/3] Publishing reel...")
    response = requests.post(
        f"{GRAPH_API_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to publish: {response.text}")
    
    media_id = response.json().get("id")
    print(f"  [OK] Published! Media ID: {media_id}")
    
    return {
        "media_id": media_id,
        "container_id": container_id,
        "status": "success"
    }


def upload_local_video(video_path: str, caption: str, 
                       public_url_base: str = None) -> dict:
    """
    Upload local video to Instagram
    
    Instagram requires video to be on a public URL.
    Options:
    1. Upload to your own server and provide public_url_base
    2. Use a service like Cloudinary, AWS S3, etc.
    3. Use ngrok for temporary public URL (development)
    """
    if not Path(video_path).exists():
        raise Exception(f"Video not found: {video_path}")
    
    if public_url_base:
        # Assume video is already uploaded to public URL
        filename = Path(video_path).name
        video_url = f"{public_url_base}/{filename}"
        return upload_reel(video_url, caption)
    else:
        print("[ERROR] Instagram requires video on public URL")
        print("Options:")
        print("  1. Upload video to cloud storage (S3, Cloudinary, etc.)")
        print("  2. Use --video-url with direct public URL")
        print("  3. Set PUBLIC_URL_BASE in .env for automatic URL construction")
        return {"status": "failed", "error": "No public URL provided"}


def generate_instagram_caption(news_list: list, is_weekly: bool = False) -> str:
    """Generate Instagram caption with hashtags"""
    if is_weekly:
        header = "📰 Weekly News Roundup"
    else:
        header = "📰 Today's Top News"
    
    # Instagram caption limit: 2200 characters
    # Keep it shorter with just headlines
    headlines = []
    for i, n in enumerate(news_list[:8]):  # Max 8 headlines
        headlines.append(f"{i+1}. {n['title'][:80]}")
    
    headlines_text = "\n".join(headlines)
    
    hashtags = "#news #worldnews #breakingnews #dailynews #globalnews #ainews #newsupdate #trending #currentevents #headlines"
    
    caption = f"""{header}

{headlines_text}

🤖 AI Generated News
📺 Full video on YouTube: AI News Daily

{hashtags}"""
    
    return caption[:2200]  # Instagram limit


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram Reels Upload")
    parser.add_argument("--file", help="Local video file path")
    parser.add_argument("--video-url", dest="video_url", help="Public video URL")
    parser.add_argument("--caption", default="", help="Caption text")
    parser.add_argument("--cover-url", dest="cover_url", help="Cover image URL")
    parser.add_argument("--get-account-id", dest="get_account_id", action="store_true",
                        help="Get Instagram Account ID from Facebook Page")
    
    args = parser.parse_args()
    
    if args.get_account_id:
        if not INSTAGRAM_ACCESS_TOKEN:
            print("Set INSTAGRAM_ACCESS_TOKEN in .env first")
            sys.exit(1)
        account_id = get_instagram_account_id(INSTAGRAM_ACCESS_TOKEN)
        print(f"Instagram Account ID: {account_id}")
        print(f"Add to .env: INSTAGRAM_ACCOUNT_ID={account_id}")
        sys.exit(0)
    
    if args.video_url:
        result = upload_reel(args.video_url, args.caption, args.cover_url)
    elif args.file:
        result = upload_local_video(args.file, args.caption)
    else:
        print("Provide --file or --video-url")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
