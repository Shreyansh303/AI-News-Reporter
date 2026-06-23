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

# --- CONFIGURATION ---
INPUT_FILE = "daily_news_context_rss.json"
OUTPUT_FILE = "frontend_briefing.json"

# Explicitly define the JSON Schema layout so Ollama can enforce it perfectly
OLLAMA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
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
    "required": ["items"]
}

async def run_master_pipeline():
    # PHASE 1: REFRESH RSS DATA
    print("=== PHASE 1: FETCHING LIVE RSS FEEDS FROM GOOGLE ===")
    await build_daily_news_context()
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
    final_frontend_data = {sec: [] for sec in sections}

    print("Packing all sections into a single context block...")
    for section in sections:
        articles = raw_data.get(section, [])
        for index, article in enumerate(articles):
            temp_id = f"{section}_{index}"
            url_mapping[temp_id] = {
                "url": article.get("url"),
                "section": section
            }
            desc = article.get("description", "")
            title = article.get("title", "")
            context_lines.append(f"ID: {temp_id}\nContext: {title} - {desc}\n")

    context_block = "\n".join(context_lines)

    print("🚀 Initializing local Llama 3.1 engine with Schema-Constrained Decoding...")
    
    # Passing the exact dictionary schema directly into format forces token-level precision
    llm = ChatOllama(
        model='llama3.1:8b',
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
         "3. Do NOT include introductory messages, text padding, or transitions."
        ),
        ("human", "Process these stories:\n\n{context}")
    ])

    chain = prompt | llm | StrOutputParser()

    print("🚀 Running batch extraction loop on local hardware...")
    try:
        raw_response = await chain.ainvoke({"context": context_block})
        
        parsed_json = json.loads(raw_response.strip())
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

        # Drop sections completely only if they generated 0 content items
        final_frontend_data = {k: v for k, v in final_frontend_data.items() if v}

    except Exception as e:
        print(f"❌ Error during batch generation: {e}")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_frontend_data, f, ensure_ascii=False, indent=2)

    print("\n====================================================")
    print(f"🏆 SUCCESS! Master execution complete.")
    print(f"   Frontend-ready data successfully built at '{OUTPUT_FILE}'")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_master_pipeline())