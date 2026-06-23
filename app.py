import json
import asyncio
import markdown
from fasthtml.common import *

# Import your master pipeline from main.py
from main1 import run_master_pipeline

#Run this in cmd before running main app.py script
#set OLLAMA_VULKAN=1 && set OLLAMA_IGPU_ENABLE=1 && ollama serve

# --- 1. APP CONFIGURATION & STYLING ---
# We inject Tailwind CSS via CDN and add a tiny CSS rule to hide the loading spinner until clicked
custom_css = Style("""
    .htmx-indicator { display: none; }
    .htmx-request .htmx-indicator { display: inline-flex; }
    .htmx-request.htmx-indicator { display: inline-flex; }
""")

app, rt = fast_app(
    pico=False,  # We turn off the default Pico.css to build a custom Tailwind UI
    hdrs=[Script(src="https://cdn.tailwindcss.com"), custom_css]
)

# --- 2. DATA LOADING & COMPONENT GENERATION ---
def load_news_data():
    """Reads the latest JSON payload from disk."""
    try:
        with open("frontend_briefing.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def NewsCard(article):
    """Creates a minimalist Tailwind card for a single news item."""
    # Convert Gemini's **bold** markdown into actual HTML <strong> tags
    html_summary = markdown.markdown(article.get('summary', ''))
    
    return Div(
        # NotStr() tells FastHTML to render the raw HTML rather than escaping the tags
        Div(NotStr(html_summary), cls="text-gray-800 text-base leading-relaxed mb-4"),
        A("Read Original Source →", href=article.get('url', '#'), target="_blank", 
          cls="text-blue-600 hover:text-blue-800 font-semibold text-sm transition-colors"),
        cls="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow flex flex-col justify-between"
    )

def SectionGrid(section_title, articles):
    """Creates a CSS Grid layout for a specific category."""
    if not articles:
        return None
    
    cards = [NewsCard(a) for a in articles]
    formatted_title = section_title.replace("_", " ").title()
    
    return Div(
        H2(formatted_title, cls="text-2xl font-extrabold text-gray-900 mb-6 border-b pb-2"),
        Div(*cards, cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"),
        cls="mb-14"
    )

def NewsFeed():
    """Builds the entire news feed by iterating through the JSON dictionary."""
    data = load_news_data()
    sections = [SectionGrid(title, articles) for title, articles in data.items()]
    
    # We wrap this in an ID so HTMX knows exactly what to swap out on refresh
    return Div(*sections, id="news-feed")

# --- 3. SERVER ROUTES ---
@rt('/')
def get():
    """The main dashboard page."""
    return Titled("News Briefing",
        Div(
            # Header Section
            Div(
                H1("Morning Intelligence", cls="text-4xl font-black text-gray-900 tracking-tight"),
                
                # HTMX Control Panel
                Div(
                    # The Loading Spinner (Hidden by default)
                    Div(
                        NotStr('<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>'),
                        "Running AI Pipeline...", 
                        id="spinner", 
                        cls="htmx-indicator items-center text-sm font-medium text-gray-500 mr-4"
                    ),
                    # The Refresh Button
                    Button(
                        "Refresh Feed", 
                        hx_get="/refresh",            
                        hx_target="#news-feed",       
                        hx_swap="outerHTML",          
                        hx_indicator="#spinner",      
                        cls="bg-black text-white px-5 py-2.5 rounded-lg font-medium hover:bg-gray-800 transition-colors shadow-sm cursor-pointer"
                    ),
                    cls="flex items-center mt-4 md:mt-0"
                ),
                cls="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 pb-6 border-b border-gray-200"
            ),
            
            # The actual news content
            NewsFeed(),
            
            # This class centers the Div and limits width, doing exactly what 'Container' did
            cls="max-w-7xl mx-auto px-4 py-12 font-sans bg-gray-50 min-h-screen"
        )
    )

@rt('/refresh')
async def get_refresh():
    """This route is hit in the background by HTMX when the button is clicked."""
    print("\n[HTMX Trigger] User requested a news refresh...")
    await run_master_pipeline()
    # Return JUST the updated NewsFeed component. HTMX handles injecting it into the screen.
    return NewsFeed()


# --- 4. STARTUP LIFECYCLE ---
if __name__ == '__main__':
    print("====================================================")
    print("🚀 STARTING FASTHTML SERVER...")
    print("Running initial boot sequence to fetch fresh news...")
    print("====================================================\n")
    
    # Run the master pipeline strictly BEFORE allowing the web server to start up
    asyncio.run(run_master_pipeline())
    
    # Once the data is fresh, boot the web UI
    serve()