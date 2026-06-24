import json
import asyncio
import markdown
from fasthtml.common import *

# Import your master pipeline from main.py
from main import run_master_pipeline

# --- 1. APP CONFIGURATION & STYLING ---
tailwind_script = Script(src="https://cdn.tailwindcss.com")
tailwind_config = Script("""
    tailwind.config = {
      darkMode: 'class',
    }
""")

custom_css = Style("""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* Enable smooth scrolling across the entire page */
    html { scroll-behavior: smooth; }
    body { font-family: 'Inter', sans-serif; }
    
    .htmx-indicator { display: none; }
    .htmx-request .htmx-indicator { display: inline-flex; }
    .htmx-request.htmx-indicator { display: inline-flex; }
    
    /* Make the markdown bold tags pop depending on the theme */
    strong { font-weight: 800; color: #171717; transition: color 0.3s ease; }
    .dark strong { color: #ffffff; }
""")

app, rt = fast_app(
    pico=False,
    htmlkw={'class': 'dark'},
    hdrs=[tailwind_script, tailwind_config, custom_css]
)

# --- 2. DATA LOADING & COMPONENT GENERATION ---
def load_news_data():
    try:
        with open("frontend_briefing.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def Sidebar(sections):
    """Generates the slide-out navigation menu with dynamic section links."""
    links = [
        Li(A(title, href=f"#{anchor}", onclick="document.getElementById('sidebar').classList.add('translate-x-full')", cls="block text-neutral-600 dark:text-neutral-400 hover:text-black dark:hover:text-white font-semibold transition-colors text-lg"))
        for title, anchor in sections
    ]
    
    return Div(
        # The Sidebar Drawer
        Div(
            Div(
                H2("Navigation", cls="text-2xl font-black text-neutral-900 dark:text-white tracking-tight"),
                Button("✕", onclick="document.getElementById('sidebar').classList.add('translate-x-full')", cls="text-neutral-500 hover:text-black dark:hover:text-white text-xl font-bold transition-colors"),
                cls="flex justify-between items-center mb-8 pb-4 border-b border-neutral-200 dark:border-neutral-800"
            ),
            Ul(*links, cls="space-y-4"),
            id="sidebar",
            cls="fixed inset-y-0 right-0 transform translate-x-full transition-transform duration-300 ease-in-out z-50 w-72 bg-white/95 dark:bg-[#0a0a0a]/95 backdrop-blur-xl border-l border-neutral-200 dark:border-neutral-800 shadow-2xl p-8 overflow-y-auto"
        ),
        
        # The Toggle Button
        Button(
            "☰",
            onclick="document.getElementById('sidebar').classList.remove('translate-x-full')",
            cls="fixed top-6 right-6 lg:top-8 lg:right-8 bg-neutral-900 dark:bg-neutral-800 text-white px-5 py-3 rounded-xl shadow-2xl z-40 hover:bg-neutral-800 dark:hover:bg-neutral-700 transition-all border border-neutral-700 dark:border-neutral-600 text-lg font-bold"
        )
    )

def NewsCard(article):
    html_summary = markdown.markdown(article.get('summary', ''))
    url = article.get('url', '#')
    
    elements = [Div(NotStr(html_summary), cls="text-neutral-700 dark:text-neutral-300 text-lg leading-relaxed flex-grow transition-colors")]
    
    if url != '#':
        elements.append(
            A("Read Source →", href=url, target="_blank", 
              cls="mt-4 md:mt-0 md:ml-6 flex-shrink-0 text-neutral-600 dark:text-neutral-400 hover:text-black dark:hover:text-white font-semibold text-sm transition-colors whitespace-nowrap px-4 py-2 rounded-lg bg-neutral-100/80 dark:bg-neutral-800/80 hover:bg-neutral-200 dark:hover:bg-neutral-700 border border-neutral-200/50 dark:border-neutral-700/50 shadow-sm")
        )
    
    return Div(
        *elements,
        cls="bg-white/60 dark:bg-[#171717]/40 backdrop-blur-xl border border-neutral-200/60 dark:border-[#404040]/50 p-6 rounded-2xl hover:bg-white/80 dark:hover:bg-neutral-800/60 hover:border-neutral-300 dark:hover:border-neutral-600/50 transition-all duration-300 flex flex-col md:flex-row items-start md:items-center transform hover:-translate-y-1 shadow-lg hover:shadow-2xl"
    )

def SectionGrid(section_title, articles):
    if not articles:
        return None
    
    cards = [NewsCard(a) for a in articles]
    
    title_mapping = {
        "user_interest": "Curated Intelligence",
        "domestic_news": "National Affairs",
        "international_news": "Global Affairs",
        "business_news": "Business & Economy",
        "technology_news": "Technology & Innovation",
        "sports_news": "Sports & Athletics"
    }
    
    formatted_title = title_mapping.get(section_title, section_title.replace("_", " ").title())
    anchor_id = formatted_title.lower().replace(" ", "-").replace("&", "and")
    
    title_cls = "text-3xl font-extrabold text-neutral-900 dark:text-neutral-100 mb-6 border-b border-neutral-200 dark:border-neutral-800/60 pb-3 tracking-tight transition-colors"
        
    return Div(
        H2(formatted_title, cls=title_cls),
        Div(*cards, cls="flex flex-col space-y-4"),
        id=anchor_id,
        cls="mb-16 scroll-mt-12"
    )

def FinanceSection(finance_data):
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
        
        color_cls = "text-green-700 dark:text-green-400" if chg >= 0 else "text-red-700 dark:text-red-400"
        bg_color_cls = "bg-green-100 dark:bg-green-900/30 border-green-200 dark:border-green-800/50" if chg >= 0 else "bg-red-100 dark:bg-red-900/30 border-red-200 dark:border-red-800/50"
        sign = "+" if chg >= 0 else ""
        
        stock_cards.append(Div(
            Div(
                Span(sym, cls="font-black text-neutral-900 dark:text-neutral-100 text-xl tracking-tight transition-colors truncate mr-2"),
                Span(f"₹{price:.2f}", cls="font-bold text-neutral-700 dark:text-neutral-300 text-lg transition-colors flex-shrink-0"),
                cls="flex justify-between items-center mb-2"
            ),
            Div(
                Span(f"{sign}{chg:.2f}%", cls=f"font-bold {color_cls} {bg_color_cls} px-2.5 py-1 rounded-md text-sm border"),
                Span(f"Vol: {vol:,}", cls="text-xs text-neutral-500 dark:text-neutral-400 font-medium"),
                cls="flex justify-between items-center mb-4"
            ),
            Div(
                Span("52W", cls="text-xs text-neutral-400 dark:text-neutral-500 font-bold uppercase tracking-wider flex-shrink-0 mr-2"),
                Span(f"₹{lo} - ₹{hi}", cls="text-xs font-medium text-neutral-500 dark:text-neutral-400 truncate"),
                cls="flex justify-between items-center pt-3 border-t border-neutral-200 dark:border-neutral-800/80 transition-colors"
            ),
            cls="bg-white/60 dark:bg-[#171717]/40 backdrop-blur-xl border border-neutral-200/60 dark:border-[#404040]/50 p-5 rounded-2xl hover:bg-white/80 dark:hover:bg-neutral-800/60 transition-all duration-300 transform hover:-translate-y-1 shadow-lg"
        ))
        
    return Div(
        H2("Market Intelligence", cls="text-3xl font-extrabold text-neutral-900 dark:text-neutral-100 mb-6 border-b border-neutral-200 dark:border-neutral-800/60 pb-3 tracking-tight transition-colors"),
        Div(NotStr(overview), cls="text-neutral-700 dark:text-neutral-300 text-lg leading-relaxed mb-8 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-700/40 bg-neutral-100/50 dark:bg-neutral-800/30 shadow-inner transition-colors"),
        Div(*stock_cards, cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5"),
        id="market-intelligence",
        cls="mb-16 scroll-mt-12"
    )

def NewsFeed():
    data = load_news_data()
    sections = []
    nav_links = []
    
    if "finance" in data:
        nav_links.append(("Market Intelligence", "market-intelligence"))
        sections.append(FinanceSection(data["finance"]))
        
    if "weather" in data:
        nav_links.append(("Weather", "weather"))
        sections.append(SectionGrid("weather", data["weather"]))
        
    title_mapping = {
        "user_interest": "Curated Intelligence",
        "domestic_news": "National Affairs",
        "international_news": "Global Affairs",
        "business_news": "Business & Economy",
        "technology_news": "Technology & Innovation",
        "sports_news": "Sports & Athletics"
    }
    
    for title, articles in data.items():
        if title in ["finance", "weather"]:
            continue
            
        formatted_title = title_mapping.get(title, title.replace("_", " ").title())
        anchor_id = formatted_title.lower().replace(" ", "-").replace("&", "and")
        nav_links.append((formatted_title, anchor_id))
        
        sections.append(SectionGrid(title, articles))
        
    return Div(
        Sidebar(nav_links),
        Div(*sections), 
        id="news-feed"
    )

# --- 3. SERVER ROUTES ---
@rt('/')
def get():
    return Titled("",
        Div(
            # Header Section
            Div(
                H1("Hi Shreyansh!", Br(), "Here's your Morning brief", cls="pb-2 text-5xl md:text-6xl font-black text-neutral-900 dark:text-white tracking-tight leading-tight mb-4 md:mb-0 transition-colors"),
                
                # Control Panel (Buttons + Spinner)
                Div(
                    # Loading Spinner
                    Div(
                        NotStr('<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-neutral-500 dark:text-neutral-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>'),
                        "Compiling...", 
                        id="spinner", 
                        cls="htmx-indicator items-center text-sm font-medium text-neutral-500 dark:text-neutral-400 mr-4 transition-colors"
                    ),
                    # Theme Toggle Button
                    Button(
                        "Toggle Theme",
                        onclick="document.documentElement.classList.toggle('dark')",
                        cls="mr-3 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 px-4 py-3 rounded-xl font-bold hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors shadow-sm border border-neutral-200 dark:border-neutral-700 cursor-pointer whitespace-nowrap"
                    ),
                    # Refresh Button
                    Button(
                        "Refresh Feed", 
                        hx_get="/refresh",            
                        hx_target="#news-feed",       
                        hx_swap="outerHTML",          
                        hx_indicator="#spinner",      
                        cls="bg-neutral-900 dark:bg-neutral-800 text-white px-6 py-3 rounded-xl font-bold hover:bg-neutral-800 dark:hover:bg-neutral-700 transition-colors shadow-lg hover:shadow-neutral-500/25 dark:hover:shadow-neutral-700/25 cursor-pointer whitespace-nowrap border border-neutral-700 dark:border-neutral-600"
                    ),
                    cls="flex flex-col md:flex-row justify-end items-center mt-6 md:mt-0 w-full md:w-auto"
                ),
                cls="flex flex-col md:flex-row justify-between items-start md:items-end mb-16 pb-8 border-b border-neutral-200 dark:border-neutral-800/80 transition-colors"
            ),
            
            # The actual news content (includes Sidebar)
            NewsFeed(),
            
            cls="max-w-7xl mx-auto px-4 sm:px-6 py-12"
        ),
        cls="bg-[#fafafa] dark:bg-[#0a0a0a] min-h-screen text-neutral-900 dark:text-[#f5f5f5] transition-colors duration-300"
    )

@rt('/refresh')
async def get_refresh():
    print("\n[HTMX Trigger] User requested a news refresh...")
    await run_master_pipeline()
    return NewsFeed()

# --- 4. STARTUP LIFECYCLE ---
if __name__ == '__main__':
    print("====================================================")
    print("🚀 STARTING FASTHTML SERVER...")
    print("====================================================\n")
    
    asyncio.run(run_master_pipeline())
    serve()