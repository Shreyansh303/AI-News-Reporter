import json
import os
import asyncio
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from news_google import build_daily_news_context
from weather_api import get_weather_context
from stocks_api import get_market_data

# --- CONFIGURATION ---
INPUT_FILE = "daily_news_context_rss.json"
OUTPUT_FILE = "frontend_briefing.json"

OLLAMA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "weather_report": {"type": "string"},
        "market_overview": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "summary": {"type": "string"}
                },
                "required": ["id", "summary"]
            }
        }
    },
    "required": ["weather_report", "market_overview", "items"]
}

async def run_master_pipeline():
    # PHASE 1: CONCURRENTLY FETCH ALL DATA
    print("=== PHASE 1: FETCHING LIVE DATA SOURCES ===")
    
    # We use asyncio.to_thread to run synchronous external libraries (requests/yfinance) without blocking the async event loop
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

    # PHASE 2: GENERATE THE AI BRIEFING
    print("=== PHASE 2: GENERATING STRUCTURAL BRIEFING FROM NEW CONTEXT ===")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    sections = [
        "international_news", "domestic_news", "business_news", 
        "technology_news", "sports_news", "user_interest"
    ]

    url_mapping = {}
    context_lines = []
    
    # We add "weather" section to final_frontend_data so it renders on the UI
    final_frontend_data = {sec: [] for sec in sections}
    final_frontend_data["weather"] = []

    print("Packing all sections into a single context block...")
    for section in sections:
        articles = raw_data.get(section, [])
        # Slice to the top 3 articles to drastically reduce context window and speed up local execution
        for index, article in enumerate(articles[:3]):
            temp_id = f"{section}_{index}"
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

    print("🚀 Initializing local Llama 3.2:3b engine with Schema-Constrained Decoding...")
    
    # Passing the exact dictionary schema directly into format forces token-level precision
    llm = ChatOllama(
        model='llama3.2:3b',
        temperature=0.1,       # Low temperature ensures it stays highly factual and precise
        num_ctx=16384,         # Expanded buffer to give plenty of workspace
        num_predict=4096,      # Expanded production capacity so it never cuts off early
        format=OLLAMA_JSON_SCHEMA 
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are an elite, data-driven editor compiling a morning intelligence brief.\n"
         "Analyze the incoming context items and populate the JSON schema array completely. Do not skip or truncate any IDs.\n\n"
         "RULES:\n"
         "1. For each provided article ID, write a single comprehensive, high-density summary sentence.\n"
         "2. Capture exact names, figures, and tracking scores. Bold key tokens with markdown (**).\n"
         "3. Do NOT include introductory messages, text padding, or transitions. Do NOT include the name of the news publisher or source (e.g., 'according to NDTV', 'Reuters reports').\n"
         "4. Read the 'RAW WEATHER DATA' and generate an engaging, reporter-style weather_report.\n"
         "5. Read the 'RAW STOCK DATA' and generate a brief, conversational market_overview discussing the broader indices and how the specific watchlist stocks moved. Also include a very brief, general mention of the overall global market sentiment today.\n"
         "6. CRITICAL FORMATTING: You MUST explicitly bold (using **asterisks**) the names of ALL indices, ALL stock tickers/companies, and ALL numbers/percentages you mention in the market_overview."
        ),
        ("human", "Process these stories:\n\n{context}")
    ])

    chain = prompt | llm | StrOutputParser()

    print("🚀 Running batch extraction loop on local hardware...")
    
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            raw_response = await chain.ainvoke({"context": context_block})
            
            parsed_json = json.loads(raw_response.strip())
            
            weather_report = parsed_json.get("weather_report")
            if weather_report:
                final_frontend_data["weather"].append({
                    "summary": weather_report,
                    "url": "#"
                })
                
            market_overview = parsed_json.get("market_overview")
            if market_overview and raw_stock_data:
                final_frontend_data["finance"] = {
                    "overview": market_overview,
                    "stocks": raw_stock_data
                }
                
            items = parsed_json.get("items", [])

            print(f"Unpacking {len(items)} processed elements back into front-end arrays...")
            for item in items:
                story_id = item.get("id")
                summary_text = item.get("summary")
                
                if story_id and summary_text and story_id in url_mapping:
                    sec = url_mapping[story_id]["section"]
                    final_frontend_data[sec].append({
                        "summary": summary_text,
                        "url": url_mapping[story_id]["url"]
                    })
                    
            # If parsing succeeds without exceptions, break out of retry loop
            break

        except Exception as e:
            print(f"❌ LLM Parsing Error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            if attempt == MAX_RETRIES - 1:
                print("⚠️ Failed all retries. Generating safe fallback state.")
                final_frontend_data["user_interest"].append({
                    "summary": "Our AI reporter experienced technical difficulties compiling today's intelligence. Please try refreshing.",
                    "url": "#"
                })

    # Drop sections completely only if they generated 0 content items
    final_frontend_data = {k: v for k, v in final_frontend_data.items() if v}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_frontend_data, f, ensure_ascii=False, indent=2)

    print("\n====================================================")
    print(f"🏆 SUCCESS! Master execution complete.")
    print(f"   Frontend-ready data successfully built at '{OUTPUT_FILE}'")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_master_pipeline())