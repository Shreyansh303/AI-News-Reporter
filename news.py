import asyncio
import html
import json
import os
import re
from dotenv import load_dotenv
from typing import Optional, List, Dict

import httpx

# --- CONFIGURATION ---
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OUTPUT_FILE = "daily_news_context.json"

def clean_text(raw_text: Optional[str]) -> Optional[str]:
    """Cleans up the text and removes API junk like [Removed]"""
    if not raw_text or raw_text.strip().lower() == "[removed]":
        return None

    cleaned = html.unescape(raw_text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned if cleaned else None

async def fetch_news(client: httpx.AsyncClient, endpoint: str, params: dict, max_items: int) -> List[Dict[str, str]]:
    url = f"https://newsapi.org{endpoint}"
    params["apiKey"] = NEWS_API_KEY
    params["pageSize"] = 30 
    
    try:
        response = await client.get(url, params=params)
        data = response.json()
        
        # Catch and print explicit API errors
        if response.status_code != 200:
            print(f"❌ API ERROR on {endpoint}: {data.get('message', 'Unknown Error')}")
            return []
            
    except Exception as e:
        print(f"❌ HTTP/Connection Error: {e}")
        return []

    valid_payloads = []
    seen_titles = set()
    
    for article in data.get("articles", []):
        raw_title = article.get("title")
        raw_desc = article.get("description")
        raw_url = article.get("url")  # Extract the article URL
        
        cleaned_title = clean_text(raw_title)
        cleaned_desc = clean_text(raw_desc)
        
        # The title is our primary anchor.
        if cleaned_title and cleaned_title not in seen_titles:
            seen_titles.add(cleaned_title)
            
            # Package the title, description, and URL together
            valid_payloads.append({
                "title": cleaned_title,
                "description": cleaned_desc if cleaned_desc else "No additional description provided.",
                "url": raw_url if raw_url else "No link available."
            })
            
            if len(valid_payloads) >= max_items:
                break
                
    return valid_payloads

async def build_daily_news_context():
    if not NEWS_API_KEY:
        print("❌ ERROR: NEWS_API_KEY is missing!")
        return

    print("Fetching hardened news streams with Links... Please wait.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        
        # 1. INTERNATIONAL
        task_intl = fetch_news(
            client, 
            endpoint="/v2/top-headlines",
            params={"sources": "reuters,bbc-news,associated-press"},
            max_items=10
        )
        
        # 2. DOMESTIC (India Breaking News)
        task_dom = fetch_news(
            client,
            endpoint="/v2/everything",
            params={
                "q": "India", 
                "language": "en", 
                "sortBy": "publishedAt"
            },
            max_items=10 
        )
        
        # 3. USER INTEREST
        task_user = fetch_news(
            client,
            endpoint="/v2/everything",
            params={
                "q": 'marvel OR anime',
                "language": "en",
                "sortBy": "publishedAt"
            },
            max_items=15
        )
        
        intl_news, dom_news, user_news = await asyncio.gather(task_intl, task_dom, task_user)

    # Compile the final structured schema 
    final_output: Dict[str, List[Dict[str, str]]] = {
        "international_news": intl_news,
        "domestic_news": dom_news,
        "user_interest": user_news
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"✅ Success! Data saved to '{OUTPUT_FILE}'.")
    print(f"   - International: {len(intl_news)} items")
    print(f"   - Domestic:      {len(dom_news)} items")
    print(f"   - User Interest: {len(user_news)} items")

if __name__ == "__main__":
    asyncio.run(build_daily_news_context())