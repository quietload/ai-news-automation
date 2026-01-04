#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'D:/workspace/news')

from news_rss import fetch_rss_news

print("Testing fetch_rss_news with dry_run=True...")
news = fetch_rss_news(count=6, news_type='daily', dry_run=True)
print(f"Got {len(news)} news")
