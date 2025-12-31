#!/usr/bin/python
"""
YouTube 동영상 업로드 스크립트
Google 공식 샘플 코드 기반
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

# 재시도 설정
httplib2.RETRIES = 1
MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# 설정
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secrets.json")
OAUTH_STORAGE_FILE = os.path.join(os.path.dirname(__file__), "upload_video.py-oauth2.json")

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_CAPTION_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = f"""
경고: OAuth 2.0 설정이 필요합니다.

{CLIENT_SECRETS_FILE} 파일이 필요합니다.

1. https://console.cloud.google.com/ 접속
2. 프로젝트 생성 또는 선택
3. YouTube Data API v3 활성화
4. 사용자 인증 정보 > OAuth 클라이언트 ID 생성
5. 애플리케이션 유형: 데스크톱 앱
6. JSON 다운로드 후 client_secrets.json으로 저장
"""

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(args):
    """OAuth 인증 서비스 생성"""
    flow = flow_from_clientsecrets(
        CLIENT_SECRETS_FILE,
        scope=[YOUTUBE_UPLOAD_SCOPE, YOUTUBE_CAPTION_SCOPE],
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


def initialize_upload(youtube, options):
    """동영상 업로드 시작"""
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    # 예약 게시 설정
    status_dict = dict(privacyStatus=options.privacyStatus)
    
    if hasattr(options, 'publishAt') and options.publishAt:
        # 예약 게시: private 상태로 업로드 후 지정 시간에 공개
        status_dict["privacyStatus"] = "private"
        status_dict["publishAt"] = options.publishAt
        print(f"[OK] 예약 게시 설정: {options.publishAt}")

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

    return resumable_upload(insert_request)


def resumable_upload(insert_request):
    """재시도 로직이 포함된 업로드"""
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            print("업로드 중...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"[OK] 업로드 성공! Video ID: {video_id}")
                    print(f"[OK] URL: https://youtube.com/watch?v={video_id}")
                    return {
                        "video_id": video_id,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "status": "success"
                    }
                else:
                    print(f"업로드 실패: {response}")
                    return {"status": "failed", "error": str(response)}
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"재시도 가능한 HTTP 에러 {e.resp.status}: {e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"재시도 가능한 에러: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                print("최대 재시도 횟수 초과")
                return {"status": "failed", "error": "Max retries exceeded"}

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"{sleep_seconds:.1f}초 후 재시도...")
            time.sleep(sleep_seconds)

    return {"status": "failed", "error": "Unknown error"}


if __name__ == '__main__':
    # OAuth argparser와 병합
    parser = argparse.ArgumentParser(
        description="YouTube 동영상 업로드",
        parents=[oauth_argparser],
        conflict_handler='resolve'
    )
    parser.add_argument("--file", required=True, help="업로드할 동영상 파일")
    parser.add_argument("--title", default="Test Title", help="동영상 제목")
    parser.add_argument("--description", default="", help="동영상 설명")
    parser.add_argument("--category", default="25", help="카테고리 ID (25=뉴스)")
    parser.add_argument("--keywords", default="", help="키워드 (쉼표 구분)")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                        default="public", help="공개 상태")
    parser.add_argument("--publish-at", dest="publishAt", default=None,
                        help="예약 게시 시간 (ISO 8601, 예: 2025-12-31T18:00:00+09:00)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"파일을 찾을 수 없습니다: {args.file}")
        sys.exit(1)

    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(MISSING_CLIENT_SECRETS_MESSAGE)
        sys.exit(1)

    youtube = get_authenticated_service(args)
    
    try:
        result = initialize_upload(youtube, args)
        # JSON 출력 (n8n에서 파싱용)
        print(json.dumps(result))
    except HttpError as e:
        print(f"HTTP 에러 {e.resp.status}: {e.content}")
        sys.exit(1)
