import yfinance as yf
import pandas as pd
import numpy as np
import requests, os
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]

MEMORY_FILE = "ai_memory.csv"

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_IDS:
        print("No Token/Chat ID")
        return
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=20)
            print(f"Telegram {cid}: {r.status_code} - {r.text[:150]}")
        except Exception as e:
            print(f"Fail {e}")

def get_nifty_regime():
    try:
        df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
        if len(df) < 30:
            return "UNKNOWN", "Data less", 0, 0, 0
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        last = df.iloc[-1]
        price = float(last['Close'])
        ema20 = float(last['EMA20'])
        ema50 = float(last['EMA50'])
        atr = float(last['ATR'])
        atr_pct = (atr / price) * 100
        
        swing_high = float(df['High'].tail(20).max())
        swing_low = float(df['Low'].tail(20).min())

        if price > ema20 and ema20 > ema50 and atr_pct > 1.0:
            regime = "TRENDING_BULL"
            reason = f"Bull: Price {price:.0f} > EMA20 {ema20:.0f} > EMA50, ATR {atr_pct:.1f}%"
        elif price < ema20 and atr_pct > 1.0:
            regime = "TRENDING_BEAR"
            reason = f"Bear: Price {price:.0f} < EMA20, ATR {atr_pct:.1f}%"
        elif atr_pct < 0.7:
            regime = "RANGE_LOW_VOL"
            reason = f"Low Vol Range: ATR {atr_pct:.1f}% - Avoid"
        else:
            regime = "RANGE"
            reason = f"Choppy: ATR {atr_pct:.1f}%"

        # Support/Resist from pivots (no NSE needed)
        return regime, reason, swing_high, swing_low, price
    except Exception as e:
        print(f"Regime err {e}")
        return "UNKNOWN", str(e), 25000, 24000, 25000

def scan_stock(symbol):
    try:
        # Add .NS for NSE
        sym = symbol if ".NS" in symbol else f"{symbol}.NS"
        df = yf.download(sym, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if len(df) < 50:
            return None
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['RSI'] = 100 - (100 / (1 + df['Close'].pct_change().rolling(14).mean().abs() / 0.01))
        # Simple RSI calc
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(last['Close'])
        ema20 = float(last['EMA20'])
        rsi = float(last['RSI'])
        vol_avg = df['Volume'].tail(20).mean()
        vol_now = float(last['Volume'])

        # Breakout condition
        high_20 = float(df['High'].tail(20).max())
        
        is_breakout = price >= high_20 * 0.99 and price > ema20 and vol_now > vol_avg * 1.2
        is_trending = price > ema20 and rsi > 55 and rsi < 78
        is_sniper = is_trending and rsi > 62 and vol_now > vol_avg * 1.5

        return {
            "symbol": symbol,
            "price": price,
            "rsi": rsi,
            "breakout": is_breakout,
            "trending": is_trending,
            "sniper": is_sniper,
            "vol_ratio": vol_now/vol_avg if vol_avg>0 else 1
        }
    except:
        return None

def main():
    regime, reason, swing_h, swing_l, nifty_price = get_nifty_regime()
    
    # NIFTY 50 list - fast scan (change to 500 if you want but takes 4 mins)
    nifty50 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LICI","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN"]
    # You can replace with full Nifty500 list from file nifty500_list.csv if you have

    picks_trending = []
    picks_breakout = []
    picks_sniper = []

    print(f"Scanning {len(nifty50)} stocks...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(scan_stock, s): s for s in nifty50}
        for f in as_completed(futures):
            res = f.result()
            if not res:
                continue
            if res['trending']:
                picks_trending.append(res)
            if res['breakout']:
                picks_breakout.append(res)
            if res['sniper']:
                picks_sniper.append(res)

    # Sort by RSI
    picks_trending = sorted(picks_trending, key=lambda x: x['rsi'], reverse=True)[:10]
    picks_breakout = sorted(picks_breakout, key=lambda x: x['vol_ratio'], reverse=True)[:7]
    picks_sniper = sorted(picks_sniper, key=lambda x: x['rsi'], reverse=True)[:7]

    # Decision
    if "BULL" in regime:
        decision = "TRADE ALLOWED - Trend Day, Buy Dips"
        emoji = "✅"
    elif "BEAR" in regime:
        decision = "TRADE ALLOWED - Bear Trend, Sell Rallies / Avoid Longs"
        emoji = "⚠️"
    else:
        decision = "NO TRADE - Range / Low Vol - Wait"
        emoji = "🛑"

    msg = f"""🤖 AUGMENTED AI BRAIN - {date.today()}

NIFTY: {nifty_price:.0f}
Regime: {regime}
{reason}
Swing High: {swing_h:.0f} | Low: {swing_l:.0f}

DECISION: {emoji} {decision}

📈 NIFTY50 TRENDING ({len(picks_trending)}):
"""
    for p in picks_trending:
        msg += f"{p['symbol']} {p['price']:.0f} RSI:{p['rsi']:.0f}\n"

    msg += f"\n🚀 BREAKOUT ({len(picks_breakout)}):\n"
    for p in picks_breakout:
        msg += f"{p['symbol']} {p['price']:.0f} Vol:{p['vol_ratio']:.1f}x\n"

    msg += f"\n🎯 SNIPER HIGH CONVICTION ({len(picks_sniper)}):\n"
    for p in picks_sniper:
        msg += f"{p['symbol']} {p['price']:.0f} RSI:{p['rsi']:.0f}\n"

    msg += "\n--------------------------\nAI Memory Updated - Learning daily"
    
    print(msg)
    send_telegram(msg)

    # Save memory
    try:
        df_mem = pd.DataFrame([{"date": str(date.today()), "nifty": nifty_price, "regime": regime, "trending_count": len(picks_trending), "breakout_count": len(picks_breakout)}])
        if os.path.exists(MEMORY_FILE):
            df_mem.to_csv(MEMORY_FILE, mode='a', header=False, index=False)
        else:
            df_mem.to_csv(MEMORY_FILE, index=False)
    except Exception as e:
        print(f"Memory save fail {e}")

if __name__ == "__main__":
    main()
