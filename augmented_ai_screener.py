import yfinance as yf
import pandas as pd
import numpy as np
import requests, os
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]

def send_telegram(msg):
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": cid, "text": msg}, timeout=20)
        except Exception as e:
            print(f"Fail {e}")

def get_nifty_regime():
    df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    price = float(last['Close'])
    ema20 = float(last['EMA20'])
    ema50 = float(last['EMA50'])
    atr = float(last['ATR'])
    atr_pct = (atr / price) * 100
    sh = float(df['High'].tail(20).max())
    sl = float(df['Low'].tail(20).min())
    if price > ema20 and ema20 > ema50:
        regime = "TRENDING_BULL"
        reason = f"Bull: {price:.0f} > EMA20 {ema20:.0f} > EMA50, ATR {atr_pct:.1f}%"
    elif price < ema20:
        regime = "TRENDING_BEAR"
        reason = f"Bear: {price:.0f} < EMA20, ATR {atr_pct:.1f}%"
    else:
        regime = "RANGE"
        reason = f"Range: ATR {atr_pct:.1f}%"
    return regime, reason, sh, sl, price

def main():
    regime, reason, sh, sl, nifty_price = get_nifty_regime()
    print(f"Nifty {nifty_price} - {regime}")

    nifty50 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN","HDFCBANK"]
    symbols_ns = [s + ".NS" for s in nifty50]
    
    # BATCH DOWNLOAD - fixes 0 picks issue
    print(f"Downloading {len(symbols_ns)} stocks in batch...")
    data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker')
    
    trending = []
    breakout = []
    sniper = []

    for sym in nifty50:
        try:
            sym_ns = sym + ".NS"
            # Handle both multi-ticker formats
            if len(symbols_ns) > 1 and sym_ns in data.columns.get_level_values(0):
                df = data[sym_ns]
            else:
                df = data if len(nifty50)==1 else data.xs(sym_ns, axis=1, level=0, drop_level=False)
                # fallback: try direct
                if df.empty:
                    continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
            
            if len(df) < 30 or df['Close'].isna().all():
                continue

            df['EMA20'] = df['Close'].ewm(span=20).mean()
            df['EMA50'] = df['Close'].ewm(span=50).mean()
            df['High20'] = df['High'].rolling(20).max()
            df['Vol20'] = df['Volume'].rolling(20).mean()
            
            last = df.iloc[-1]
            price = float(last['Close'])
            ema20 = float(last['EMA20'])
            ema50 = float(last['EMA50'])
            high20 = float(last['High20'])
            vol20 = float(last['Vol20']) if not np.isnan(last['Vol20']) else 1
            vol_now = float(last['Volume'])
            vol_ratio = vol_now / vol20 if vol20>0 else 1

            # Simple momentum without RSI - more reliable
            is_up = price > ema20 and ema20 > ema50
            is_breakout = price >= high20 * 0.98 and price > ema20

            if is_up:
                trending.append({"sym": sym, "price": price, "vol": vol_ratio})
            if is_breakout:
                breakout.append({"sym": sym, "price": price, "vol": vol_ratio})
            if is_up and vol_ratio > 1.2:
                sniper.append({"sym": sym, "price": price, "vol": vol_ratio})

        except Exception as e:
            print(f"{sym} err {e}")
            continue

    trending = sorted(trending, key=lambda x: x['vol'], reverse=True)[:10]
    breakout = sorted(breakout, key=lambda x: x['vol'], reverse=True)[:7]
    sniper = sorted(sniper, key=lambda x: x['vol'], reverse=True)[:7]

    decision = "TRADE ALLOWED - Trend Day, Buy Dips" if "BULL" in regime else "NO TRADE - Wait"
    emoji = "✅" if "BULL" in regime else "🛑"

    msg = f"🤖 AUGMENTED AI BRAIN - {date.today()}\n"
    msg += f"--------------------------\n"
    msg += f"NIFTY: {nifty_price:.0f}\nRegime: {regime}\n{reason}\nHigh: {sh:.0f} Low: {sl:.0f}\n\n"
    msg += f"DECISION: {emoji} {decision}\n"
    msg += f"--------------------------\n"
    msg += f"📈 TRENDING ({len(trending)}):\n"
    for p in trending:
        msg += f"{p['sym']} {p['price']:.0f} Vol:{p['vol']:.1f}x\n"
    msg += f"\n🚀 BREAKOUT ({len(breakout)}):\n"
    for p in breakout:
        msg += f"{p['sym']} {p['price']:.0f} Vol:{p['vol']:.1f}x\n"
    msg += f"\n🎯 SNIPER ({len(sniper)}):\n"
    for p in sniper:
        msg += f"{p['sym']} {p['price']:.0f} Vol:{p['vol']:.1f}x\n"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
