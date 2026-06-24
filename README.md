# AI News Reporter

The AI News Reporter is a fully automated, AI-driven daily intelligence dashboard. Built with FastHTML, TailwindCSS, and LangChain, it aggregates disparate data streams—global news, local weather forecasts, and stock market indices—and synthesizes them into a highly readable, personalized morning briefing using Generative AI. 

## Project Architecture

### 1. Asynchronous Data Pipeline
At the core of the project is a high-performance Python backend utilizing `asyncio`. It **concurrently fetches** live stock market data via `yfinance`, weather telemetry from OpenWeatherMap, and global news feeds via Google RSS. By processing these network I/O requests **in parallel rather than sequentially**, the pipeline drastically reduces data retrieval latency.

### 2. Generative AI Orchestration
The project integrates **LangChain** to seamlessly orchestrate Large Language Models. It supports both **lightning-fast cloud execution** via Google Gemini and **100% offline, private execution** via Ollama (e.g., Llama 3). The pipeline feeds the aggregated raw data into the LLM with strict formatting prompts to synthesize concise summaries, extract critical entities, and generate conversational market intelligence.

To ensure maximum reliability, the LLM integration features **robust retry loops and fallback handlers**. These **self-healing mechanisms** automatically detect and correct malformed JSON outputs or AI hallucinations before they ever reach the frontend, preventing the web server from crashing.

### 3. Responsive Full-Stack Dashboard
The frontend is designed as a modern, server-side rendered web interface using **FastHTML**. It strips away complex JavaScript frameworks in favor of **pure Python component generation**. The interface is styled with **Tailwind CSS**, featuring a dynamic Light/Dark mode toggle with smooth CSS transitions. Using **HTMX**, the dashboard can trigger background pipeline executions and update its interface **in real-time without requiring a full page reload**.

### 4. Centralized Configuration
The architecture is built to be highly modular. By modifying a **single `config.json` file**, users can instantly change the localized weather coordinates, swap the tracked broad market indices, and update the specific stocks monitored in their personal watchlist, **without needing to touch the underlying Python code**.

## Tech Stack
- **Backend:** Python, FastHTML, AsyncIO
- **AI / LLM:** LangChain, Google Gemini, Ollama
- **Frontend:** Tailwind CSS, HTMX
- **Data Integration:** yfinance, OpenWeatherMap API, Google News RSS

## Getting Started

### 1. Clone and Navigate
Clone the repository and enter the project directory:
```bash
git clone https://github.com/yourusername/ai-news-reporter.git
cd ai-news-reporter
```

### 2. Set Up the Python Environment
It is highly recommended to use a virtual environment. Create and activate it:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

Install the required dependencies:
```bash
pip install python-fasthtml langchain-google-genai langchain-ollama yfinance python-dotenv markdown
```

### 3. API Keys (.env)
Create a `.env` file in the root directory and add your API credentials:
```env
GOOGLE_API_KEY="your_gemini_api_key_here"
WEATHER_API_KEY="your_openweathermap_api_key_here"
```

### 4. Custom Configuration
Open the `config.json` file to customize the dashboard. You can change the localized weather coordinates, tracked broad market indices, and your specific stock watchlist.

### 5. Launch the Server
Start the FastHTML web server by executing the main entry point:
```bash
python app.py
```
Navigate to `http://localhost:5001` in your web browser to view your daily intelligence brief!
