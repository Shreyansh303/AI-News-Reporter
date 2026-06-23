import asyncio
import html
import json
import re
import urllib.parse
from typing import Optional, List, Dict

import httpx
import feedparser

# --- CONFIGURATION ---
OUTPUT_FILE = "daily_news_context_rss.json"

MAX_ITEMS_INTL = 10
MAX_ITEMS_DOM = 10
MAX_ITEMS_BIZ = 10
MAX_ITEMS_TECH = 10
MAX_ITEMS_SPORTS = 10  # New Sports Limit
MAX_ITEMS_USER = 15

# Broad industry terms targeting production news instead of listicles
ANIME_QUERY = '(anime OR manga OR "light novel" OR "animation studio") AND (unveils OR returns OR trailer OR announcement OR production OR "release date" OR serialization OR adaptation OR teaser)'

# Broad cinematic terms targeting breaking pop culture/entertainment events
HOLLYWOOD_QUERY = '("tv shows" OR movies OR cinema OR "streaming series") AND (leak OR trailer OR cast OR reveal OR clips OR premiere OR teaser OR announcement)'

ENCODED_ANIME = urllib.parse.quote(ANIME_QUERY)
ENCODED_HOLLYWOOD = urllib.parse.quote(HOLLYWOOD_QUERY)


def clean_google_html(raw_text: Optional[str]) -> str:
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text


async def fetch_rss_feed(client: httpx.AsyncClient, url: str, max_items: int) -> List[Dict[str, str]]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []

    valid_payloads = []
    seen_titles = set()
    
    for entry in feed.entries:
        raw_title = entry.get("title", "")
        raw_link = entry.get("link", "")
        raw_desc = entry.get("description", "")
        
        title = clean_google_html(raw_title)
        desc = clean_google_html(raw_desc)
        
        if desc.startswith(title):
            desc = desc[len(title):].strip()
            
        if title and title not in seen_titles:
            seen_titles.add(title)
            
            valid_payloads.append({
                "title": title,
                "description": desc if desc else "Context provided in title.",
                "url": raw_link
            })
            
            if len(valid_payloads) >= max_items:
                break
                
    return valid_payloads


async def build_daily_news_context():
    print("Fetching targeted streams (Including Sports)...")

    # 1. INTERNATIONAL: Global World News Section
    url_intl = "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"
    
    # 2. DOMESTIC: India Breaking News
    url_dom = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
    
    # 3. BUSINESS: Global Markets and Corporate News
    url_biz = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"
    
    # 4. TECHNOLOGY: Gadgets, Dev, and AI News
    url_tech = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
    
    # 5. SPORTS: Global Sports breaking news
    url_sports = "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en"
    
    # 6. USER INTERESTS (Split endpoints to protect anime data density)
    url_anime = f"https://news.google.com/rss/search?q={ENCODED_ANIME}&hl=en-US&gl=US&ceid=US:en"
    url_hollywood = f"https://news.google.com/rss/search?q={ENCODED_HOLLYWOOD}&hl=en-US&gl=US&ceid=US:en"

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # Fetching all 7 network requests concurrently
        task_intl = fetch_rss_feed(client, url_intl, MAX_ITEMS_INTL)
        task_dom = fetch_rss_feed(client, url_dom, MAX_ITEMS_DOM)
        task_biz = fetch_rss_feed(client, url_biz, MAX_ITEMS_BIZ)
        task_tech = fetch_rss_feed(client, url_tech, MAX_ITEMS_TECH)
        task_sports = fetch_rss_feed(client, url_sports, MAX_ITEMS_SPORTS)
        task_anime = fetch_rss_feed(client, url_anime, 15) 
        task_hollywood = fetch_rss_feed(client, url_hollywood, 15)
        
        intl_news, dom_news, biz_news, tech_news, sports_news, anime_news, hollywood_news = await asyncio.gather(
            task_intl, task_dom, task_biz, task_tech, task_sports, task_anime, task_hollywood
        )

    # Balanced Interleaving for User Interests
    user_interest_combined = []
    for anime_item, hollywood_item in zip(anime_news, hollywood_news):
        user_interest_combined.append(anime_item)
        user_interest_combined.append(hollywood_item)
    
    if len(anime_news) > len(hollywood_news):
        user_interest_combined.extend(anime_news[len(hollywood_news):])
    else:
        user_interest_combined.extend(hollywood_news[len(anime_news):])
        
    final_user_interest = user_interest_combined[:MAX_ITEMS_USER]

    # Structure final JSON schema
    final_output: Dict[str, List[Dict[str, str]]] = {
        "international_news": intl_news,
        "domestic_news": dom_news,
        "business_news": biz_news,
        "technology_news": tech_news,
        "sports_news": sports_news,
        "user_interest": final_user_interest
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"✅ Success! Data saved to '{OUTPUT_FILE}'.")
    print(f"   - International: {len(intl_news)} items")
    print(f"   - Domestic:      {len(dom_news)} items")
    print(f"   - Business:      {len(biz_news)} items")
    print(f"   - Technology:    {len(tech_news)} items")
    print(f"   - Sports:        {len(sports_news)} items")
    print(f"   - User Interest: {len(final_user_interest)} items")


if __name__ == "__main__":
    asyncio.run(build_daily_news_context())