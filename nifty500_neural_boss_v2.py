# NIFTY500_NEURAL_BOSS_V3.1 - FIXED for yfinance 2026
import os, json, requests, yfinance as yf
import pandas as pd, numpy as np
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    print(f"DEBUG Token={bool(BOT_TOKEN)} Chat={CHAT_ID}")
    if not BOT_TOKEN or not CHAT_ID:
        print(msg); return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=20)
        print(f"Telegram status {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"Telegram error {e}\n{msg}")

def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except:
        return 50.0

def get_nifty500_list():
    # Fixed symbols - working in 2026
    return [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS",
        "ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS",
        "SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS",
        "ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS",
        "BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS",
        "JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS",
        "EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS",
        "TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS",
        "VEDL.NS","LTIM.NS","PIDILITIND.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS",
        "PFC.NS","TATAPOWER.NS","SBIN.NS"
    ]

def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="60d", interval="1d", progress=False, auto_adjust=False)
        if df is None or len(df) < 35:
            return None
        # Fix for new yfinance multi-column
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        vol = df['Volume']
        
        last_close = float(close.iloc[-1])
        if pd.isna(last_close):
            return None
            
        ema9 = float(close.ewm(span=9).mean().iloc[-1])
        ema21 = float(close.ewm(span=21).mean().iloc[-1])
        ema50 = float(close.ewm(span=50).mean().iloc[-1])
        rsi = calc_rsi(close)
        
        avg_vol = float(vol.tail(10).mean())
        last_vol = float(vol.iloc[-1])
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
        
        y_h = float(high.iloc[-2])
        y_l = float(low.iloc[-2])
        y_c = float(close.iloc[-2])
        pivot = (y_h + y_l + y_c) / 3
        bc = (y_h + y_l) / 2
        tc = pivot - bc + pivot
        
        score = 0
        reasons = []
        if last_close > tc:
            score += 2.5 * 1.18; reasons.append(f"Above TC {tc:.0f}")
        if ema9 > ema21 and last_close > ema21:
            score += 2.5 * 1.27; reasons.append("EMA9>21 Bull")
        if last_close > ema50:
            score += 1.5 * 1.27; reasons.append(">EMA50")
        if 55 <= rsi <= 78:
            score += 2.0 * 1.31; reasons.append(f"RSI {rsi:.0f}")
        if vol_ratio > 1.3:
            score += 1.5; reasons.append(f"Vol {vol_ratio:.1f}x")
            
        return {"symbol": symbol.replace(".NS",""), "price": last_close, "score": round(score,1),
                "rsi": round(rsi,1), "tc": round(tc,1), "volx": round(vol_ratio,1),
                "reasons": " | ".join(reasons)}
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

def main():
    print("Starting Nifty500 Neural Boss V3.1 Fixed...")
    try:
        nifty = yf.download("^NSEI", period="5d", interval="1d", progress=False, auto_adjust=False)
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)
        y_h = float(nifty['High'].iloc[-2]); y_l = float(nifty['Low'].iloc[-2])
        y_c = float(nifty['Close'].iloc[-2]); live = float(nifty['Close'].iloc[-1])
        pivot = (y_h+y_l+y_c)/3; bc = (y_h+y_l)/2; tc = pivot - bc + pivot
    except:
        y_h=y_l=y_c=live=tc=pivot=bc=0

    stocks = get_nifty500_list()
    results = []
    for sym in stocks:
        res = analyze_stock(sym)
        if res and res['score'] >= 6:
            results.append(res)
            print(f"OK {sym} Score {res['score']}")
    
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    top3 = results[:3]
    
    msg = f"""NIFTY500 NEURAL BOSS V3.1 🧠
Date: {datetime.now().strftime('%d-%b %Y %I:%M %p')}
Nifty Live: {live:.0f} | CPR TC {tc:.0f}

Total Scanned: {len(stocks)} | Qualified: {len(results)}

🔥 TOP 3 PICKS:
"""
    if not top3:
        msg += "No stock scored >6 today. Low momentum day.\n"
    else:
        for i, s in enumerate(top3, 1):
            sl = s['price'] * 0.98; tgt1 = s['price'] * 1.02; tgt2 = s['price'] * 1.035
            msg += f"{i}. {s['symbol']} @ {s['price']:.0f} SCORE {s['score']}/10 BUY\n SL {sl:.0f} TGT {tgt1:.0f}/{tgt2:.0f} | RSI {s['rsi']} Vol {s['volx']}x\n {s['reasons']}\n\n"

    msg += "Rule: Trade only 8+/10\nAuto-sent from GitHub"
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
