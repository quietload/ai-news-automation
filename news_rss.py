#!/usr/bin/env python3
"""
RSS News Fetcher & Breaking News Detector
==========================================

38개 글로벌 RSS 피드에서 실시간 뉴스 수집.
무료, 딜레이 없음, API 제한 없음.

Functions:
    fetch_rss_news(count, news_type)           # Daily Shorts용
    fetch_rss_news_by_category(count, news_type)  # Weekly Video용
    detect_breaking_news(min_sources)          # Breaking News 감지
    fetch_breaking_news_details(breaking_news) # Breaking 상세 수집

Filtering:
    - Local News: US/UK/AU 도시, local council, school board 스킵
    - Similar: 50%+ 제목 유사도 스킵 (Jaccard)
    - Auto-fill: 카테고리 부족 시 다른 카테고리에서 보충
    - Duplicates: daily/weekly/breaking 별도 추적

Breaking News:
    - Trigger: breaking keywords + 5개 이상 소스
    - Keywords: breaking, dies, war, earthquake, resigns, etc.
    - 키워드 기반 그룹핑: 동일 사건 다른 제목도 그룹핑
      (venezuela, ukraine, russia, china, iran, israel 등)
    - 40% 유사도 또는 동일 토픽 키워드로 그룹화
    - Daily limit: 최대 3개/일

Usage:
    from news_rss import fetch_rss_news, detect_breaking_news
    
    news = fetch_rss_news(count=6, news_type="daily")
    breaking = detect_breaking_news(min_sources=5)

Log:
    [OK] technology: Apple announces... (TechCrunch)
    [SKIP] Local: Florida governor...
    [SKIP] Similar: Apple reveals...
    [FILL] business: Amazon reports...
    [BREAKING] Found: Major earthquake...
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
USED_NEWS_FILE_RSS_BREAKING = Path(__file__).parent / "used_news_rss_breaking.json"

# Breaking news daily limit
MAX_BREAKING_PER_DAY = 3

# Breaking News 키워드
BREAKING_KEYWORDS = [
    # 속보 표현
    "breaking", "just in", "urgent", "developing", "alert",
    # 사망/사고
    "dies", "dead", "killed", "assassination", "assassinated",
    # 전쟁/공격
    "war", "invasion", "attack", "explosion", "bombing", "missile",
    # 자연재해
    "earthquake", "tsunami", "hurricane", "typhoon", "wildfire",
    # 경제/금융 충격
    "crash", "collapse", "bankruptcy", "default",
    # 정치 이벤트
    "resigns", "resigned", "impeached", "arrested", "indicted",
    # 역사적 사건
    "record", "historic", "first ever", "unprecedented",
]

# 주요 인물/기관 (이들 관련 뉴스는 가중치)
MAJOR_ENTITIES = [
    # 국가 정상
    "president", "prime minister", "xi jinping", "putin",
    # 빅테크
    "elon musk", "tim cook", "satya nadella", "sundar pichai", "mark zuckerberg",
    # 글로벌 기업
    "apple", "google", "microsoft", "amazon", "tesla", "nvidia", "samsung",
    # 국제기구
    "united nations", "un", "who", "nato", "federal reserve", "fed",
]

# 키워드 기반 그룹핑을 위한 주제 키워드 (같은 사건으로 묶을 키워드 조합)
TOPIC_KEYWORDS = {
    # 국가/지역명 + 관련 키워드들
    "venezuela": ["maduro", "caracas", "venezuelan"],
    "ukraine": ["kyiv", "kiev", "zelensky", "ukrainian"],
    "russia": ["moscow", "putin", "russian", "kremlin"],
    "china": ["beijing", "chinese", "xi jinping"],
    "iran": ["tehran", "iranian"],
    "israel": ["gaza", "hamas", "palestinian", "tel aviv", "israeli"],
    "north korea": ["pyongyang", "kim jong"],
    "taiwan": ["taipei", "taiwanese"],
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_news_id(title: str) -> str:
    """Generate unique ID from title"""
    return hashlib.md5(title.encode()).hexdigest()[:16]


def normalize_title(title: str) -> str:
    """Normalize title for comparison (lowercase, remove punctuation)"""
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    return ' '.join(title.split())


def titles_match(title1: str, title2: str, threshold: float = 0.5) -> bool:
    """Check if two titles are about the same news"""
    words1 = set(normalize_title(title1).split())
    words2 = set(normalize_title(title2).split())
    
    if not words1 or not words2:
        return False
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return (intersection / union) >= threshold


def is_breaking_news(title: str, description: str = "") -> bool:
    """Check if news contains breaking keywords"""
    text = (title + " " + description).lower()
    
    for keyword in BREAKING_KEYWORDS:
        if keyword in text:
            return True
    
    return False


def get_topic_key(title: str, description: str = "") -> str:
    """
    Extract topic key for keyword-based grouping.
    Returns topic key if found, empty string otherwise.
    """
    text = (title + " " + description).lower()
    
    for main_keyword, related_keywords in TOPIC_KEYWORDS.items():
        # 메인 키워드 또는 관련 키워드 중 하나라도 있으면
        all_keywords = [main_keyword] + related_keywords
        if any(kw in text for kw in all_keywords):
            # 브레이킹 키워드도 있는지 확인
            has_breaking = any(bk in text for bk in BREAKING_KEYWORDS)
            if has_breaking:
                return main_keyword
    
    return ""


def same_topic(title1: str, title2: str, desc1: str = "", desc2: str = "") -> bool:
    """
    Check if two articles are about the same topic.
    Uses both title similarity AND keyword-based matching.
    """
    # 1. 제목 유사도 체크 (기존 방식)
    if titles_match(title1, title2, threshold=0.4):
        return True
    
    # 2. 키워드 기반 체크 (새로운 방식)
    topic1 = get_topic_key(title1, desc1)
    topic2 = get_topic_key(title2, desc2)
    
    if topic1 and topic2 and topic1 == topic2:
        return True
    
    return False


def has_major_entity(title: str, description: str = "") -> bool:
    """Check if news involves major entities"""
    text = (title + " " + description).lower()
    
    for entity in MAJOR_ENTITIES:
        if entity in text:
            return True
    
    return False


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
    if news_type == "daily":
        file_path = USED_NEWS_FILE_RSS_DAILY
    elif news_type == "weekly":
        file_path = USED_NEWS_FILE_RSS_WEEKLY
    else:  # breaking
        file_path = USED_NEWS_FILE_RSS_BREAKING
    
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("used", []))
    return set()


def save_used_news(used: set, news_type: str = "daily", max_keep: int = 500):
    """Save used news IDs"""
    if news_type == "daily":
        file_path = USED_NEWS_FILE_RSS_DAILY
    elif news_type == "weekly":
        file_path = USED_NEWS_FILE_RSS_WEEKLY
    else:  # breaking
        file_path = USED_NEWS_FILE_RSS_BREAKING
    
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
# BREAKING NEWS DETECTION
# =============================================================================

def get_today_breaking_count() -> int:
    """Get how many breaking news were generated today"""
    if not USED_NEWS_FILE_RSS_BREAKING.exists():
        return 0
    
    with open(USED_NEWS_FILE_RSS_BREAKING, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    daily_counts = data.get('daily_counts', {})
    return daily_counts.get(today, 0)


def increment_today_breaking_count():
    """Increment today's breaking news count"""
    data = {}
    if USED_NEWS_FILE_RSS_BREAKING.exists():
        with open(USED_NEWS_FILE_RSS_BREAKING, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    daily_counts = data.get('daily_counts', {})
    
    # Clean old dates (keep only last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    daily_counts = {k: v for k, v in daily_counts.items() if k >= week_ago}
    
    daily_counts[today] = daily_counts.get(today, 0) + 1
    data['daily_counts'] = daily_counts
    
    with open(USED_NEWS_FILE_RSS_BREAKING, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def detect_breaking_news(min_sources: int = 5) -> Optional[Dict]:
    """
    Detect breaking news by scanning all RSS feeds.
    Returns breaking news if:
    1. Contains breaking keywords AND
    2. Found in 5+ different sources
    3. Daily limit not exceeded (max 3 per day)
    
    Returns None if no breaking news detected.
    """
    print(f"\n[BREAKING] Scanning for breaking news (min {min_sources} sources)...")
    
    # Check daily limit
    today_count = get_today_breaking_count()
    if today_count >= MAX_BREAKING_PER_DAY:
        print(f"  [LIMIT] Daily limit reached ({today_count}/{MAX_BREAKING_PER_DAY}). Skipping...")
        return None
    
    print(f"  [INFO] Today's breaking count: {today_count}/{MAX_BREAKING_PER_DAY}")
    
    # Load already reported breaking news
    used_breaking = load_used_news("breaking")
    
    # Collect all news from all feeds
    all_news = []
    for category, feeds in RSS_FEEDS.items():
        for source_name, url in feeds:
            items = parse_feed(url, source_name, category)
            all_news.extend(items)
    
    print(f"  [INFO] Scanned {len(all_news)} articles from all feeds")
    
    # Group similar news together
    news_groups = []  # List of (representative_news, count, sources)
    
    for news in all_news:
        title = news['title']
        desc = news.get('description', '')
        
        # Skip if not breaking keyword
        if not is_breaking_news(title, desc):
            continue
        
        # Skip if already reported
        news_id = get_news_id(title)
        if news_id in used_breaking:
            continue
        
        # Skip local news
        if is_local_news(title, desc):
            continue
        
        # Find matching group or create new one (using same_topic for better grouping)
        found_group = False
        for group in news_groups:
            if same_topic(title, group[0]['title'], desc, group[0].get('description', '')):
                group[1] += 1
                group[2].add(news.get('source', 'Unknown'))
                found_group = True
                break
        
        if not found_group:
            news_groups.append([news, 1, {news.get('source', 'Unknown')}])
    
    # Find news with 5+ sources
    for group in news_groups:
        news, count, sources = group
        if len(sources) >= min_sources:
            print(f"  [BREAKING] Found: {news['title'][:50]}...")
            print(f"  [BREAKING] Sources ({len(sources)}): {', '.join(list(sources)[:5])}...")
            
            # Mark as used
            used_breaking.add(get_news_id(news['title']))
            save_used_news(used_breaking, "breaking")
            
            # Increment daily count
            increment_today_breaking_count()
            
            return news
    
    print(f"  [INFO] No breaking news detected (found {len(news_groups)} candidates)")
    return None


def fetch_breaking_news_details(breaking_news: Dict) -> List[Dict]:
    """
    Fetch more details about breaking news from multiple sources.
    Returns list of related articles for comprehensive coverage.
    """
    print(f"\n[BREAKING] Gathering details for: {breaking_news['title'][:50]}...")
    
    related = [breaking_news]
    all_titles = [breaking_news['title']]
    
    # Scan all feeds for related news
    for category, feeds in RSS_FEEDS.items():
        for source_name, url in feeds:
            items = parse_feed(url, source_name, category)
            
            for item in items:
                if titles_match(item['title'], breaking_news['title'], threshold=0.3):
                    if not is_similar_news(item['title'], all_titles, threshold=0.7):
                        related.append(item)
                        all_titles.append(item['title'])
                        print(f"  [+] {source_name}: {item['title'][:40]}...")
                        
                        if len(related) >= 5:  # Max 5 sources
                            break
            
            if len(related) >= 5:
                break
        
        if len(related) >= 5:
            break
    
    print(f"  [OK] Gathered {len(related)} sources")
    return related


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
