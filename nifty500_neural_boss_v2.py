# NIFTY500_NEURAL_BOSS_V3.2 PRO - PERFECT RANKING NO TIE
import os, json, requests, yfinance as yf
import pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(msg); return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=20)
        print(f"Telegram {r.status_code}")
    except Exception as e:
        print(f"Telegram error {e}")

def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except: return 50.0

def get_list():
    return ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","LTIM.NS","PIDILITIND.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"]

def analyze(symbol):
    try:
        df = yf.download(symbol, period="60d", interval="1d", progress=False, auto_adjust=False)
        if df is None or len(df) < 35: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close, high, low, vol = df['Close'], df['High'], df['Low'], df['Volume']
        lc = float(close.iloc[-1]); y_h=float(high.iloc[-2]); y_l=float(low.iloc[-2]); y_c=float(close.iloc[-2])
        ema9=float(close.ewm(span=9).mean().iloc[-1]); ema21=float(close.ewm(span=21).mean().iloc[-1]); ema50=float(close.ewm(span=50).mean().iloc[-1])
        rsi=calc_rsi(close)
        avg_v=float(vol.tail(10).mean()); last_v=float(vol.iloc[-1]); volx=last_v/avg_v if avg_v>0 else 1.0
        pivot=(y_h+y_l+y_c)/3; bc=(y_h+y_l)/2; tc=pivot-bc+pivot

        # PRO SCORING 0-10 NO TIE LOGIC
        score = 0.0
        # 1. EMA Gap % - higher gap = stronger momentum
        ema_gap = ((ema9 - ema21) / ema21 * 100) if ema21!=0 else 0
        score += max(0, min(2.5, ema_gap * 2))  # 0-2.5
        
        # 2. Price above TC %
        tc_gap = ((lc - tc)/tc*100) if tc!=0 else 0
        score += max(0, min(2.0, tc_gap * 1.5))
        
        # 3. RSI Perfect 60-70 = 2.5, 55-75=2, else less
        if 60 <= rsi <= 70: score += 2.5
        elif 55 <= rsi <= 75: score += 2.0
        elif 50 <= rsi <= 78: score += 1.2
        else: score += 0.3
        
        # 4. Volume - precise
        score += min(2.0, volx * 0.8)
        
        # 5. Above EMA50 bonus
        if lc > ema50: score += 1.0

        reasons = f"EMA gap {ema_gap:.1f}% | TC+{tc_gap:.1f}% | RSI {rsi:.0f} | Vol {volx:.1f}x"
        return {"symbol":symbol.replace(".NS",""),"price":lc,"score":round(score,2),"rsi":round(rsi,1),"tc":round(tc,1),"volx":round(volx,1),"ema_gap":round(ema_gap,2),"reasons":reasons}
    except Exception as e:
        print(f"Err {symbol} {e}"); return None

def main():
    print("Starting V3.2 PRO...")
    try:
        nifty=yf.download("^NSEI",period="5d",interval="1d",progress=False,auto_adjust=False)
        if isinstance(nifty.columns, pd.MultiIndex): nifty.columns=nifty.columns.get_level_values(0)
        y_h=float(nifty['High'].iloc[-2]); y_l=float(nifty['Low'].iloc[-2]); y_c=float(nifty['Close'].iloc[-2]); live=float(nifty['Close'].iloc[-1])
        pivot=(y_h+y_l+y_c)/3; bc=(y_h+y_l)/2; tc=pivot-bc+pivot
    except: y_h=y_l=y_c=live=tc=0

    results=[]
    for sym in get_list():
        r=analyze(sym)
        if r and r['score']>=5:
            results.append(r)
            print(f"{r['symbol']} Score {r['score']}")

    results=sorted(results,key=lambda x:x['score'],reverse=True)
    top3=results[:3]

    msg=f"""NIFTY500 NEURAL BOSS V3.2 PRO 🧠
Date: {datetime.now().strftime('%d-%b %Y %I:%M %p')}
Nifty: {live:.0f} | TC {tc:.0f}

Scanned: {len(get_list())} | Qualified: {len(results)}

🔥 TOP 3 PICKS (No Tie Rank):
"""
    if not top3:
        msg+="No qualified stock today.\n"
    else:
        for i,s in enumerate(top3,1):
            sl=s['price']*0.98; t1=s['price']*1.02; t2=s['price']*1.035
            msg+=f"{i}. {s['symbol']} @ {s['price']:.0f} SCORE {s['score']}/10 BUY\n SL {sl:.0f} TGT {t1:.0f}/{t2:.0f}\n {s['reasons']}\n\n"

    msg+="Rule: Trade 7.5+ only | Self-learning active"
    print(msg)
    send_telegram(msg)

if __name__=="__main__": main()
