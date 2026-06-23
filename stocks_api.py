import yfinance as yf
import json
import os

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("finance", {})
    except Exception:
        return {}

def get_market_data():
    config = load_config()
    watchlist = config.get("watchlist", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"])
    indices = config.get("indices", {"^GSPC": "S&P 500", "^IXIC": "NASDAQ"})
    
    llm_context_lines = []
    llm_context_lines.append("MARKET INDICES:")
    
    raw_frontend_data = []
    
    # Process Indices for LLM context
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d").dropna()
            if len(hist) >= 1:
                current = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
                change_pct = ((current - prev) / prev) * 100
                llm_context_lines.append(f"{name}: {current:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            
    llm_context_lines.append("\nWATCHLIST STOCKS:")
    
    # Process Watchlist for both LLM and Frontend
    for symbol in watchlist:
        try:
            ticker = yf.Ticker(symbol)
            # Fetch history for price, volume, day range
            hist = ticker.history(period="5d").dropna()
            if len(hist) >= 1:
                current = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
                change_pct = ((current - prev) / prev) * 100
                volume = int(hist['Volume'].iloc[-1])
                day_high = float(hist['High'].iloc[-1])
                day_low = float(hist['Low'].iloc[-1])
                
                # Try to get 52 week data from info, fallback if missing
                info = ticker.info
                wk52_high = info.get('fiftyTwoWeekHigh', 'N/A')
                wk52_low = info.get('fiftyTwoWeekLow', 'N/A')
                
                llm_context_lines.append(
                    f"{symbol}: Price {current:.2f} ({change_pct:+.2f}%), "
                    f"Vol: {volume}, Day Range: {day_low:.2f}-{day_high:.2f}, "
                    f"52W Range: {wk52_low}-{wk52_high}"
                )
                
                raw_frontend_data.append({
                    "symbol": symbol,
                    "price": float(round(current, 2)),
                    "change_pct": float(round(change_pct, 2)),
                    "volume": int(volume),
                    "wk52_high": wk52_high if isinstance(wk52_high, str) else float(round(wk52_high, 2)),
                    "wk52_low": wk52_low if isinstance(wk52_low, str) else float(round(wk52_low, 2))
                })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            
    if not raw_frontend_data:
        return "Market data temporarily unavailable.", []
        
    return "\n".join(llm_context_lines), raw_frontend_data

if __name__ == "__main__":
    llm_text, raw_data = get_market_data()
    print("--- LLM CONTEXT ---")
    print(llm_text)
    print("\n--- FRONTEND JSON ---")
    print(raw_data)
