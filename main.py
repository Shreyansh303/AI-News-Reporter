import json
import os
import asyncio
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from news_google import build_daily_news_context
from weather_api import get_weather_context
from stocks_api import get_market_data



# --- CONFIGURATION ---
INPUT_FILE = "daily_news_context_rss.json"
OUTPUT_FILE = "frontend_briefing.json"

# 1. DEFINE THE STRUCTURE GEMINI MUST RETURN
class ArticleSummary(BaseModel):
    id: str = Field(description="The exact temporary ID passed in the context.")
    summary: str = Field(description="The hyper-dense, detailed summary with bolded entities.")

class MasterBriefing(BaseModel):
    weather_report: str = Field(description="The engaging and informative weather briefing generated from the provided weather data.")
    market_overview: str = Field(description="A brief, engaging conversational overview of the broader stock market trends and specific watchlist movements based on the provided RAW STOCK DATA.")
    items: List[ArticleSummary]


async def run_master_pipeline():
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("❌ GOOGLE_API_KEY not found! Check your .env file.")

    # -----------------------------------------------------------------
    # PHASE 1: CONCURRENTLY FETCH ALL DATA
    # -----------------------------------------------------------------
    print("=== PHASE 1: FETCHING LIVE DATA SOURCES ===")
    
    weather_task = asyncio.to_thread(get_weather_context)
    stocks_task = asyncio.to_thread(get_market_data)
    news_task = build_daily_news_context()
    
    print("Simultaneously gathering RSS Feeds, Weather, and Stocks...")
    _, weather_data, (llm_market_text, raw_stock_data) = await asyncio.gather(
        news_task,
        weather_task,
        stocks_task
    )
    print("====================================================\n")

    # -----------------------------------------------------------------
    # PHASE 2: GENERATE THE AI BRIEFING (SINGLE BATCH)
    # -----------------------------------------------------------------
    print("=== PHASE 2: GENERATING STRUCTURAL BRIEFING FROM NEW CONTEXT ===")
    
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading newly generated JSON: {e}")
        return

    sections = [
        "international_news", "domestic_news", "business_news", 
        "technology_news", "sports_news", "user_interest"
    ]

    # Initialize the mapping dictionaries
    url_mapping = {}
    context_lines = []
    
    # We add "weather" section to final_frontend_data so it renders on the UI
    final_frontend_data = {sec: [] for sec in sections}
    final_frontend_data["weather"] = []

    print("Packing all 6 sections into a single context block...")

    # Build ONE massive context block containing all articles from all sections
    for section in sections:
        articles = raw_data.get(section, [])
        for index, article in enumerate(articles):
            temp_id = f"{section}_{index}"
            
            # Store both the URL and the Section so we can unpack it later
            url_mapping[temp_id] = {
                "url": article.get("url"),
                "section": section
            }
            
            desc = article.get("description", "")
            title = article.get("title", "")
            context_lines.append(f"ID: {temp_id}\nContext: {title} - {desc}\n")

    # We inject the data we fetched concurrently in Phase 1
    context_lines.append(f"\nRAW WEATHER DATA:\n{weather_data}")
    context_lines.append(f"\nRAW STOCK DATA:\n{llm_market_text}")

    context_block = "\n".join(context_lines)

    #Setup Gemini
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    
    
    structured_llm = llm.with_structured_output(MasterBriefing)

    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are an elite, data-driven editor compiling a morning intelligence brief.\n"
         "RULES:\n"
         "1. For each provided article ID, write a comprehensive, high-density summary.\n"
         "2. Every summary must be hyper-dense, capturing specific scores, player names, company names, and numbers from the context.\n"
         "3. Bold all key names, teams, and numbers for instant scanning.\n"
         "4. Do NOT use conversational transitions.\n"
         "5. Read the 'RAW WEATHER DATA' and generate an engaging, reporter-style weather briefing.\n"
         "6. Read the 'RAW STOCK DATA' and generate a brief, conversational market overview discussing the broader indices and how the specific watchlist stocks moved. Do not list out all the numbers mechanically; tell the story of the market day.\n"
         "7. CRITICAL FORMATTING: You MUST explicitly bold (using **asterisks**) the names of ALL indices, ALL stock tickers/companies, and ALL numbers/percentages you mention in the market overview."
        ),
        ("human", "Process these stories:\n\n{context}")
    ])

    chain = prompt | structured_llm

    print("🚀 Sending ONE unified batch request to Gemini API (Bypassing Rate Limits)...")

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            # One single API call processes everything!
            result = await chain.ainvoke({"context": context_block})
            
            # Extract the new weather section
            if result.weather_report:
                final_frontend_data["weather"].append({
                    "summary": result.weather_report,
                    "url": "#"
                })
                
            # Extract the new finance section
            if result.market_overview and raw_stock_data:
                final_frontend_data["finance"] = {
                    "overview": result.market_overview,
                    "stocks": raw_stock_data
                }
                
            # Unpack the single massive list back into the correct sections
            for item in result.items:
                if item.id in url_mapping:
                    sec = url_mapping[item.id]["section"]
                    final_frontend_data[sec].append({
                        "summary": item.summary,
                        "url": url_mapping[item.id]["url"]
                    })
                    
            # If parsing succeeds, break out of retry loop
            break

        except Exception as e:
            print(f"❌ LLM Error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt == MAX_RETRIES - 1:
                print("⚠️ Failed all retries. Generating safe fallback state.")
                final_frontend_data["user_interest"].append({
                    "summary": "Our AI reporter experienced technical difficulties compiling today's intelligence via Gemini. Please try refreshing.",
                    "url": "#"
                })

    # Remove any empty sections if a feed failed
    final_frontend_data = {k: v for k, v in final_frontend_data.items() if v}

    # Save final frontend-optimized configuration
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_frontend_data, f, ensure_ascii=False, indent=2)

    print("\n====================================================")
    print(f"🏆 SUCCESS! Master execution complete.")
    print(f"   Frontend-ready data successfully built at '{OUTPUT_FILE}'")
    print("====================================================")


if __name__ == "__main__":
    asyncio.run(run_master_pipeline())