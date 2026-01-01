#!/usr/bin/env python3
"""
RSS News Fetcher
================
Fetches real-time news from major global news RSS feeds.
No delay, no API limits, completely free.

Usage:
    from news_rss import fetch_rss_news, fetch_rss_news_by_category
    
    # Get 10 news for Daily Shorts
    news = fetch_rss_news(count=10)
    
    # Get 20 news for Weekly Video (by category)
    news = fetch_rss_news_by_category(count=20)
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
    """
    print(f"\n[RSS] Fetching {count} news articles...")
    
    used_news = load_used_news(news_type)
    all_news = []
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
                if news_id not in used_news:
                    all_news.append(item)
                    print(f"  [OK] {category}: {item['title'][:40]}... ({source_name})")
                    break  # One per source
            
            if len([n for n in all_news if n['category'] == CATEGORY_NAMES.get(category)]) >= 2:
                break  # Max 2 per category for diversity
    
    # Select final news
    selected = []
    for category in categories:
        cat_name = CATEGORY_NAMES.get(category)
        cat_news = [n for n in all_news if n['category'] == cat_name]
        if cat_news:
            selected.append(cat_news[0])
            if len(selected) >= count:
                break
    
    # Fill remaining slots if needed
    while len(selected) < count and all_news:
        for news in all_news:
            if news not in selected:
                selected.append(news)
                if len(selected) >= count:
                    break
    
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
    """
    print(f"\n[RSS] Fetching {count} news articles by category...")
    
    used_news = load_used_news(news_type)
    all_news = []
    categories = list(RSS_FEEDS.keys())
    per_category = (count + len(categories) - 1) // len(categories)  # Ceiling division
    
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
                if news_id not in used_news and item not in category_news:
                    category_news.append(item)
                    print(f"  [OK] {category}: {item['title'][:40]}... ({source_name})")
                    if len(category_news) >= per_category:
                        break
        
        all_news.extend(category_news)
    
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
