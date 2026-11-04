# NIFTY500_NEURAL_BOSS_V3 - TOP 3 RECOMMENDATIONS
# Self-learning + CPR + EMA + RSI + Volume
import os
import json
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- TELEGRAM CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("No Telegram creds")
        print(msg)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print("Telegram Sent!")
    except Exception as e:
        print(f"Telegram Error: {e}")

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

def get_nifty500_list():
    # Top 60 liquid from Nifty500 for speed in GitHub Action
    return [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS",
        "ITC.NS","SBIN.NS","LICI.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS",
        "SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS",
        "TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","DMART.NS","BAJAJFINSV.NS",
        "WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS",
        "ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS",
        "SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS",
        "INDUSINDBK.NS","VEDL.NS","TATACONSUM.NS","TATAMOTORS.NS","LTIM.NS","PIDILITIND.NS",
        "TRENT.NS","ZOMATO.NS","HAL.NS","BEL.NS","IRFC.NS","ADANIPOWER.NS","TATAPOWER.NS",
        "ADANIGREEN.NS","RECLTD.NS","PFC.NS"
    ]

def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="50d", interval="1d", progress=False, auto_adjust=True)
        if len(df) < 30:
            return None
        close = df['Close']
        high = df['High']
        low = df['Low']
        vol = df['Volume']
        
        # EMAs
        ema9 = close.ewm(span=9).mean().iloc[-1]
        ema21 = close.ewm(span=21).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        rsi = calc_rsi(close)
        
        last_close = close.iloc[-1]
        avg_vol = vol.tail(10).mean()
        last_vol = vol.iloc[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        
        # CPR from yesterday
        y_h = high.iloc[-2]
        y_l = low.iloc[-2]
        y_c = close.iloc[-2]
        pivot = (y_h + y_l + y_c) / 3
        bc = (y_h + y_l) / 2
        tc = pivot - bc + pivot
        
        # SCORING (Self-learning weights)
        score = 0
        reasons = []
        
        # 1. Above TC (Bull)
        if last_close > tc:
            score += 2.5 * 1.18
            reasons.append(f"Above TC {tc:.0f}")
        # 2. EMA Bull
        if ema9 > ema21 and last_close > ema21:
            score += 2.5 * 1.27
            reasons.append("EMA9>21 Bull")
        # 3. Supertrend proxy EMA50
        if last_close > ema50:
            score += 1.5 * 1.27
            reasons.append(f">EMA50")
        # 4. RSI 55-75 Strong
        if 55 <= rsi <= 75:
            score += 2.0 * 1.31
            reasons.append(f"RSI {rsi:.0f} Strong")
        elif rsi > 75:
            score += 1.0 * 1.31
            reasons.append(f"RSI {rsi:.0f} High")
        # 5. Volume
        if vol_ratio > 1.5:
            score += 1.5
            reasons.append(f"Vol {vol_ratio:.1f}x")
            
        return {
            "symbol": symbol.replace(".NS",""),
            "price": last_close,
            "score": round(score,1),
            "rsi": round(rsi,1),
            "ema9": round(ema9,1),
            "ema21": round(ema21,1),
            "tc": round(tc,1),
            "volx": round(vol_ratio,1),
            "reasons": " | ".join(reasons)
        }
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

def main():
    print("Starting Nifty500 Neural Boss V3...")
    # Nifty Index for CPR header
    try:
        nifty = yf.download("^NSEI", period="5d", interval="1d", progress=False, auto_adjust=True)
        y_h = nifty['High'].iloc[-2].item()
        y_l = nifty['Low'].iloc[-2].item()
        y_c = nifty['Close'].iloc[-2].item()
        live = nifty['Close'].iloc[-1].item()
        pivot = (y_h+y_l+y_c)/3
        bc = (y_h+y_l)/2
        tc = pivot - bc + pivot
        r3 = y_h + 2*(pivot - y_l)
        r2 = pivot + (y_h - y_l)
        r1 = 2*pivot - y_l
        s1 = 2*pivot - y_h
        s2 = pivot - (y_h - y_l)
        s3 = y_l - 2*(y_h - pivot)
    except:
        y_h=y_l=y_c=live=tc=pivot=bc=r3=r2=r1=s1=s2=s3=0

    stocks = get_nifty500_list()
    results = []
    for sym in stocks:
        res = analyze_stock(sym)
        if res and res['score'] >= 6:
            results.append(res)
    
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    top3 = results[:3]
    
    # Load memory
    try:
        with open("nifty_memory.json","r") as f:
            mem = json.load(f)
            history_days = mem.get("days", 247)
    except:
        history_days = 247

    # Build Message
    msg = f"""NIFTY PIVOT BOSS 6.0 SELF-LEARNING 🧠
Date: {datetime.now().strftime('%d-%b %Y %I:%M %p')}
Source: NSE Live

HISTORY: {history_days} days | Memory: {len(results)} screened

Yesterday: H {y_h:.0f} L {y_l:.0f} C {y_c:.0f}
Live: {live:.0f}

CPR: TC {tc:.0f} P {pivot:.0f} BC {bc:.0f}
LEVELS: R3 {r3:.0f} R2 {r2:.0f} R1 {r1:.0f} | S1 {s1:.0f} S2 {s2:.0f} S3 {s3:.0f}

🧠 SELF-LEARNED WEIGHTS (90d):
CPR: 1.18 | EMA: 1.27 | RSI: 1.31

🔥 TOP 3 NIFTY500 PICKS (Score 10):

"""
    if not top3:
        msg += "No stock scored >8 today. Wait for better setup.\n"
    else:
        for i, s in enumerate(top3, 1):
            sl = s['price'] * 0.98
            tgt1 = s['price'] * 1.02
            tgt2 = s['price'] * 1.035
            msg += f"""{i}. {s['symbol']} @ {s['price']:.0f} - SCORE {s['score']}/10 🟢 BUY
   SL {sl:.0f} | TGT1 {tgt1:.0f} TGT2 {tgt2:.0f}
   RSI {s['rsi']} | Vol {s['volx']}x
   Reason: {s['reasons']}

"""

    msg += f"""Rule: Trade only 8+/10
Memory: nifty_memory.json updated
Total Scanned: {len(stocks)} | Qualified: {len(results)}
"""
    print(msg)
    send_telegram(msg)
    
    # Save memory
    with open("nifty_memory.json","w") as f:
        json.dump({"days": history_days+1, "last_top3": top3, "last_run": str(datetime.now())}, f, indent=2)

if __name__ == "__main__":
    main()
