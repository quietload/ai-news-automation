#!/usr/bin/env python3
"""
RSS News Fetcher
================
Fetches real-time news from 38 global RSS feeds.
No delay, no API limits, completely free.

Features:
    - Local news filter: Skips region-specific articles (US cities, UK towns, etc.)
    - Similar article filter: Skips articles with 50%+ title similarity
    - Auto-fill: If a category is short, fills from other categories
    - Duplicate prevention: Tracks used articles per daily/weekly

Usage:
    from news_rss import fetch_rss_news, fetch_rss_news_by_category
    
    # Daily Shorts: 6 diverse news
    news = fetch_rss_news(count=6, news_type="daily")
    
    # Weekly Video: 16 news (2 per category)
    news = fetch_rss_news_by_category(count=16, news_type="weekly")

Log Examples:
    [OK] technology: Apple announces AI... (TechCrunch)
    [SKIP] Local: Florida governor signs...
    [SKIP] Similar: Apple reveals new AI...
    [FILL] business: Amazon reports Q4... (Bloomberg)
"""

import feedparser
import hashlib
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# =============================================================================
# RSS FEED SOURCES (Global, English, Trusted)
# =============================================================================

RSS_FEEDS = {
    "world": [
        # 한국 뉴스 (영어판) - 우선 순위
        ("Korea Herald", "http://www.koreaherald.com/rss/020000000000.xml"),
        ("Korea Times", "https://www.koreatimes.co.kr/www/rss/nation.xml"),
        ("Yonhap News", "https://en.yna.co.kr/RSS/news.xml"),
        ("Arirang News", "https://www.arirang.com/rss/news_all.xml"),
        # 글로벌 뉴스
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("DW", "https://rss.dw.com/rdf/rss-en-all"),
    ],
    "business": [
        ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
        ("Financial Times", "https://www.ft.com/rss/home"),
        ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ],
    "technology": [
        ("BBC Tech", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Wired", "https://www.wired.com/feed/rss"),
    ],
    "science": [
        ("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("Science Daily", "https://www.sciencedaily.com/rss/all.xml"),
        ("Nature", "https://www.nature.com/nature.rss"),
        ("New Scientist", "https://www.newscientist.com/feed/home/"),
        ("Space.com", "https://www.space.com/feeds/all"),
    ],
    "health": [
        ("BBC Health", "https://feeds.bbci.co.uk/news/health/rss.xml"),
        ("WebMD", "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"),
        ("Medical News Today", "https://www.medicalnewstoday.com/rss"),
        ("Health News", "https://www.news-medical.net/syndication.axd?format=rss"),
    ],
    "sports": [
        ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml"),
        ("ESPN", "https://www.espn.com/espn/rss/news"),
        ("Sky Sports", "https://www.skysports.com/rss/12040"),
        ("Sports Illustrated", "https://www.si.com/rss/si_topstories.rss"),
    ],
    "entertainment": [
        ("BBC Entertainment", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
        ("Variety", "https://variety.com/feed/"),
        ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/"),
        ("Entertainment Weekly", "https://ew.com/feed/"),
    ],
    "environment": [
        ("BBC Environment", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("Guardian Environment", "https://www.theguardian.com/environment/rss"),
        ("Climate News", "https://www.climatechangenews.com/feed/"),
        ("Mongabay", "https://news.mongabay.com/feed/"),
    ],
}

# Category display names
CATEGORY_NAMES = {
    "world": "World",
    "business": "Business", 
    "technology": "Technology",
    "science": "Science",
    "health": "Health",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "environment": "Environment",
}

# Used news tracking
USED_NEWS_FILE_RSS_DAILY = Path(__file__).parent / "used_news_rss_daily.json"
USED_NEWS_FILE_RSS_WEEKLY = Path(__file__).parent / "used_news_rss_weekly.json"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_news_id(title: str) -> str:
    """Generate unique ID from title"""
    return hashlib.md5(title.encode()).hexdigest()[:16]


# 지역/단체 한정 기사 필터링 키워드
LOCAL_KEYWORDS = [
    # 미국 지역
    "florida", "texas", "california", "new york city", "nyc", "los angeles", "chicago",
    "boston", "seattle", "denver", "atlanta", "miami", "phoenix", "detroit", "portland",
    # 영국 지역
    "london", "manchester", "birmingham", "liverpool", "scotland", "wales", "northern ireland",
    # 호주 지역
    "sydney", "melbourne", "brisbane", "perth", "adelaide",
    # 특정 단체/기관 (글로벌 아닌 것)
    "local council", "city council", "county", "municipality", "township",
    "school board", "school district", "high school", "elementary school",
    "local police", "sheriff", "state trooper",
    # 스포츠 로컬
    "minor league", "college football", "college basketball", "ncaa", "high school sports",
    # 기타 로컬 표현
    "residents say", "neighbors", "local community", "town hall", "local election",
    "state legislature", "governor signs", "mayor announces",
]


def is_local_news(title: str, description: str = "") -> bool:
    """Check if news is local/regional (not global interest)"""
    text = (title + " " + description).lower()
    for keyword in LOCAL_KEYWORDS:
        if keyword in text:
            return True
    return False


def is_similar_news(new_title: str, existing_titles: list, threshold: float = 0.5) -> bool:
    """Check if news title is too similar to existing ones"""
    new_words = set(new_title.lower().split())
    
    for existing in existing_titles:
        existing_words = set(existing.lower().split())
        
        # Jaccard similarity
        if not new_words or not existing_words:
            continue
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)
        similarity = intersection / union
        
        if similarity >= threshold:
            return True
    
    return False


def load_used_news(news_type: str = "daily") -> set:
    """Load used news IDs"""
    file_path = USED_NEWS_FILE_RSS_DAILY if news_type == "daily" else USED_NEWS_FILE_RSS_WEEKLY
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("used", []))
    return set()


def save_used_news(used: set, news_type: str = "daily", max_keep: int = 500):
    """Save used news IDs"""
    file_path = USED_NEWS_FILE_RSS_DAILY if news_type == "daily" else USED_NEWS_FILE_RSS_WEEKLY
    used_list = list(used)[-max_keep:]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({"used": used_list}, f)


def parse_feed(url: str, source_name: str, category: str) -> List[Dict]:
    """Parse a single RSS feed"""
    try:
        feed = feedparser.parse(url)
        news_items = []
        
        for entry in feed.entries[:10]:  # Max 10 per feed
            title = entry.get('title', '').strip()
            description = entry.get('summary', '') or entry.get('description', '')
            link = entry.get('link', '')
            
            # Clean description (remove HTML tags)
            if description:
                import re
                description = re.sub(r'<[^>]+>', '', description).strip()
                description = description[:500]  # Limit length
            
            if title and len(title) > 20:
                news_items.append({
                    "title": title,
                    "description": description,
                    "source": source_name,
                    "category": CATEGORY_NAMES.get(category, category),
                    "link": link,
                })
        
        return news_items
    except Exception as e:
        print(f"  [WARN] Failed to parse {source_name}: {e}")
        return []


# =============================================================================
# MAIN FETCH FUNCTIONS
# =============================================================================

def fetch_rss_news(count: int = 8, news_type: str = "daily") -> List[Dict]:
    """
    Fetch news from RSS feeds (for Daily Shorts)
    Returns diverse news from all categories
    Filters out: local news, similar articles
    """
    print(f"\n[RSS] Fetching {count} news articles...")
    
    used_news = load_used_news(news_type)
    all_news = []
    all_titles = []  # 유사도 체크용
    categories = list(RSS_FEEDS.keys())
    random.shuffle(categories)
    
    # Collect news from each category
    for category in categories:
        feeds = RSS_FEEDS[category]
        random.shuffle(feeds)
        
        for source_name, url in feeds:
            items = parse_feed(url, source_name, category)
            
            for item in items:
                news_id = get_news_id(item['title'])
                
                # 1. 이미 사용한 뉴스 스킵
                if news_id in used_news:
                    continue
                
                # 2. 지역/단체 한정 기사 스킵
                if is_local_news(item['title'], item.get('description', '')):
                    print(f"  [SKIP] Local: {item['title'][:40]}...")
                    continue
                
                # 3. 유사 기사 스킵
                if is_similar_news(item['title'], all_titles):
                    print(f"  [SKIP] Similar: {item['title'][:40]}...")
                    continue
                
                all_news.append(item)
                all_titles.append(item['title'])
                print(f"  [OK] {category}: {item['title'][:40]}... ({source_name})")
                break  # One per source
            
            if len([n for n in all_news if n['category'] == CATEGORY_NAMES.get(category)]) >= 2:
                break  # Max 2 per category for diversity
    
    # Select final news (카테고리당 1개씩)
    selected = []
    selected_titles = []
    for category in categories:
        cat_name = CATEGORY_NAMES.get(category)
        cat_news = [n for n in all_news if n['category'] == cat_name]
        if cat_news:
            selected.append(cat_news[0])
            selected_titles.append(cat_news[0]['title'])
            if len(selected) >= count:
                break
    
    # Fill remaining slots if needed (부족하면 다른 카테고리에서 추가)
    if len(selected) < count:
        print(f"  [INFO] Need {count - len(selected)} more articles...")
        for news in all_news:
            if news not in selected:
                if not is_similar_news(news['title'], selected_titles):
                    selected.append(news)
                    selected_titles.append(news['title'])
                    print(f"  [FILL] {news['category']}: {news['title'][:40]}...")
                if len(selected) >= count:
                    break
    
    # 순서 랜덤 섞기
    random.shuffle(selected)
    
    # Save used news
    for news in selected:
        used_news.add(get_news_id(news['title']))
    save_used_news(used_news, news_type)
    
    print(f"  [OK] Total: {len(selected)} articles selected")
    return selected[:count]


def fetch_rss_news_by_category(count: int = 16, news_type: str = "weekly") -> List[Dict]:
    """
    Fetch news by category (for Weekly Video)
    Returns balanced news across all categories
    Filters out: local news, similar articles
    If a category is short, fills from other categories
    """
    print(f"\n[RSS] Fetching {count} news articles by category...")
    
    used_news = load_used_news(news_type)
    all_news = []
    all_titles = []  # 전체 유사도 체크용
    categories = list(RSS_FEEDS.keys())
    per_category = (count + len(categories) - 1) // len(categories)  # Ceiling division
    
    # 1차: 카테고리별로 수집
    for category in categories:
        feeds = RSS_FEEDS[category]
        random.shuffle(feeds)
        category_news = []
        
        for source_name, url in feeds:
            if len(category_news) >= per_category:
                break
                
            items = parse_feed(url, source_name, category)
            
            for item in items:
                news_id = get_news_id(item['title'])
                
                # 1. 이미 사용한 뉴스 스킵
                if news_id in used_news:
                    continue
                
                # 2. 지역/단체 한정 기사 스킵
                if is_local_news(item['title'], item.get('description', '')):
                    print(f"  [SKIP] Local: {item['title'][:40]}...")
                    continue
                
                # 3. 유사 기사 스킵 (전체 기준)
                if is_similar_news(item['title'], all_titles):
                    print(f"  [SKIP] Similar: {item['title'][:40]}...")
                    continue
                
                category_news.append(item)
                all_titles.append(item['title'])
                print(f"  [OK] {category}: {item['title'][:40]}... ({source_name})")
                
                if len(category_news) >= per_category:
                    break
        
        all_news.extend(category_news)
    
    # 2차: 부족하면 다른 카테고리에서 추가 수집
    if len(all_news) < count:
        print(f"  [INFO] Need {count - len(all_news)} more articles, searching other categories...")
        random.shuffle(categories)
        
        for category in categories:
            if len(all_news) >= count:
                break
                
            feeds = RSS_FEEDS[category]
            random.shuffle(feeds)
            
            for source_name, url in feeds:
                if len(all_news) >= count:
                    break
                    
                items = parse_feed(url, source_name, category)
                
                for item in items:
                    news_id = get_news_id(item['title'])
                    
                    if news_id in used_news:
                        continue
                    if is_local_news(item['title'], item.get('description', '')):
                        continue
                    if is_similar_news(item['title'], all_titles):
                        continue
                    if item in all_news:
                        continue
                    
                    all_news.append(item)
                    all_titles.append(item['title'])
                    print(f"  [FILL] {category}: {item['title'][:40]}... ({source_name})")
                    
                    if len(all_news) >= count:
                        break
    
    # 순서 랜덤 섞기
    random.shuffle(all_news)
    
    # Save used news
    for news in all_news:
        used_news.add(get_news_id(news['title']))
    save_used_news(used_news, news_type)
    
    print(f"  [OK] Total: {len(all_news)} articles from {len(categories)} categories")
    return all_news[:count]


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing RSS News Fetcher")
    print("=" * 60)
    
    # Test daily fetch
    print("\n--- Daily Shorts (10 news) ---")
    daily_news = fetch_rss_news(count=10, news_type="daily")
    for i, news in enumerate(daily_news, 1):
        print(f"{i}. [{news['category']}] {news['title'][:50]}...")
    
    print("\n--- Weekly Video (20 news) ---")
    weekly_news = fetch_rss_news_by_category(count=20, news_type="weekly")
    for i, news in enumerate(weekly_news, 1):
        print(f"{i}. [{news['category']}] {news['title'][:50]}...")
