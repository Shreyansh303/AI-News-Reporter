import json
import asyncio
import markdown
from fasthtml.common import *

# Import your master pipeline from main.py
from main import run_master_pipeline

#Run this in cmd before running main app.py script
#set OLLAMA_VULKAN=1 && set OLLAMA_IGPU_ENABLE=1 && ollama serve

# --- 1. APP CONFIGURATION & STYLING ---
# We inject Tailwind CSS via CDN, Inter Google Font, and add a tiny CSS rule to hide the loading spinner until clicked
custom_css = Style("""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    body { font-family: 'Inter', sans-serif; background-color: #0a0a0a; color: #f5f5f5; }
    .htmx-indicator { display: none; }
    .htmx-request .htmx-indicator { display: inline-flex; }
    .htmx-request.htmx-indicator { display: inline-flex; }
    /* Micro-animations and sleek panels */
    .glass-panel {
        background: rgba(23, 23, 23, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(64, 64, 64, 0.3);
    }
    
    /* Make the markdown bold tags pop with crisp white in dark mode */
    strong { color: #ffffff; font-weight: 800; }
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
    """Creates a sleek dark mode horizontal row for a single news item."""
    html_summary = markdown.markdown(article.get('summary', ''))
    url = article.get('url', '#')
    
    # We wrap the summary text to target bold elements and color them
    elements = [Div(NotStr(html_summary), cls="text-neutral-300 text-lg leading-relaxed flex-grow")]
    
    if url != '#':
        elements.append(
            A("Read Source →", href=url, target="_blank", 
              cls="mt-4 md:mt-0 md:ml-6 flex-shrink-0 text-neutral-400 hover:text-white font-semibold text-sm transition-colors whitespace-nowrap px-4 py-2 rounded-lg bg-neutral-800/80 hover:bg-neutral-700 border border-neutral-700/50")
        )
    
    return Div(
        *elements,
        cls="glass-panel p-6 rounded-2xl hover:bg-neutral-800/60 hover:border-neutral-600/50 transition-all duration-300 flex flex-col md:flex-row items-start md:items-center transform hover:-translate-y-1 shadow-lg hover:shadow-2xl"
    )

def SectionGrid(section_title, articles):
    """Creates a vertical list stack layout for a specific category."""
    if not articles:
        return None
    
    cards = [NewsCard(a) for a in articles]
    formatted_title = section_title.replace("_", " ").title()
    
    title_cls = "text-3xl font-extrabold text-neutral-100 mb-6 border-b border-neutral-800/60 pb-3 tracking-tight"
        
    return Div(
        H2(formatted_title, cls=title_cls),
        Div(*cards, cls="flex flex-col space-y-4"),
        cls="mb-16"
    )

def FinanceSection(finance_data):
    """Builds a sleek dark layout for the market overview and stock grid."""
    if not finance_data:
        return None
        
    overview = markdown.markdown(finance_data.get('overview', ''))
    stocks = finance_data.get('stocks', [])
    
    stock_cards = []
    for s in stocks:
        sym = s.get('symbol')
        price = s.get('price')
        chg = s.get('change_pct', 0)
        vol = s.get('volume')
        hi = s.get('wk52_high')
        lo = s.get('wk52_low')
        
        # Kept the green/red strictly for the percentage indicators for readability
        color_cls = "text-green-400" if chg >= 0 else "text-red-400"
        bg_color_cls = "bg-green-900/30" if chg >= 0 else "bg-red-900/30"
        sign = "+" if chg >= 0 else ""
        
        stock_cards.append(Div(
            Div(
                Span(sym, cls="font-black text-neutral-100 text-xl tracking-tight"),
                Span(f"${price:.2f}", cls="font-bold text-neutral-300 text-lg"),
                cls="flex justify-between items-center mb-2"
            ),
            Div(
                Span(f"{sign}{chg:.2f}%", cls=f"font-bold {color_cls} {bg_color_cls} px-2.5 py-1 rounded-md text-sm border border-{color_cls.split('-')[1]}-800/50"),
                Span(f"Vol: {vol:,}", cls="text-xs text-neutral-500 font-medium"),
                cls="flex justify-between items-center mb-4"
            ),
            Div(
                Span("52W", cls="text-xs text-neutral-500 font-bold uppercase tracking-wider"),
                Span(f"${lo} - ${hi}", cls="text-xs font-medium text-neutral-400"),
                cls="flex justify-between items-center pt-3 border-t border-neutral-800/80"
            ),
            cls="glass-panel p-5 rounded-2xl hover:bg-neutral-800/60 hover:border-neutral-600/50 transition-all duration-300 transform hover:-translate-y-1 shadow-lg"
        ))
        
    return Div(
        H2("Market Intelligence", cls="text-3xl font-extrabold text-neutral-100 mb-6 border-b border-neutral-800/60 pb-3 tracking-tight"),
        Div(NotStr(overview), cls="text-neutral-300 text-lg leading-relaxed mb-8 p-6 rounded-2xl border border-neutral-700/40 bg-neutral-800/30 shadow-inner"),
        Div(*stock_cards, cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5"),
        cls="mb-16"
    )

def NewsFeed():
    """Builds the entire news feed enforcing strict ordering: Finance -> Weather -> Rest."""
    data = load_news_data()
    sections = []
    
    # 1. Render Finance First
    if "finance" in data:
        sections.append(FinanceSection(data["finance"]))
        
    # 2. Render Weather Second
    if "weather" in data:
        sections.append(SectionGrid("weather", data["weather"]))
        
    # 3. Render everything else
    for title, articles in data.items():
        if title in ["finance", "weather"]:
            continue
        sections.append(SectionGrid(title, articles))
        
    # We wrap this in an ID so HTMX knows exactly what to swap out on refresh
    return Div(*sections, id="news-feed")

# --- 3. SERVER ROUTES ---
@rt('/')
def get():
    """The main dashboard page."""
    return Titled("",
        Div(
            # Header Section
            Div(
                H1("Hi Shreyansh!", Br(), "Here's your Morning brief", cls="pb-2 text-5xl md:text-6xl font-black text-white tracking-tight leading-tight mb-4 md:mb-0"),
                
                # HTMX Control Panel
                Div(
                    # The Loading Spinner (Hidden by default)
                    Div(
                        NotStr('<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-neutral-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>'),
                        "Compiling Intelligence...", 
                        id="spinner", 
                        cls="htmx-indicator items-center text-sm font-medium text-neutral-400 mr-4"
                    ),
                    # The Refresh Button
                    Button(
                        "Refresh Feed", 
                        hx_get="/refresh",            
                        hx_target="#news-feed",       
                        hx_swap="outerHTML",          
                        hx_indicator="#spinner",      
                        cls="bg-neutral-800 text-white px-6 py-3 rounded-xl font-bold hover:bg-neutral-700 transition-colors shadow-lg hover:shadow-neutral-700/25 cursor-pointer whitespace-nowrap border border-neutral-600"
                    ),
                    cls="flex flex-col md:flex-row justify-end items-center mt-6 md:mt-0 w-full md:w-auto"
                ),
                cls="flex flex-col md:flex-row justify-between items-start md:items-end mb-16 pb-8 border-b border-neutral-800/80"
            ),
            
            # The actual news content
            NewsFeed(),
            
            # Root Container
            cls="max-w-7xl mx-auto px-4 sm:px-6 py-12 min-h-screen"
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