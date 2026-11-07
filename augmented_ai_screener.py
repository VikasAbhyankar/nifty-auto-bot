import yfinance as yf
import pandas as pd
import numpy as np
import requests, os
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]

def send_telegram(msg):
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": cid, "text": msg}, timeout=20)
        except: pass

# --- AUGMENTED AI BRAIN (Regime + Points + Win%) ---
def get_nifty():
    df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    atr = float(last['ATR']); atr_pct = (atr/price*100)
    sh = float(df['High'].tail(20).max()); sl = float(df['Low'].tail(20).min())
    score = 0
    if price > ema20: score+=30
    if ema20 > ema50: score+=30
    if atr_pct > 1: score+=20
    if price > sh*0.99: score+=20
    regime = "TRENDING_BULL" if score>=80 else "MILD_BULL" if score>=50 else "RANGE"
    return regime, score, price, ema20, sh, sl, atr_pct

def calc_avwap(df):
    """SNIPER AVWAP LOGIC: AVWAP from last 20-day swing low"""
    try:
        # Find swing low in last 20 days
        low_idx = df['Low'].tail(20).idxmin()
        # AVWAP from that swing low
        df_slice = df.loc[low_idx:]
        df_slice['PV'] = df_slice['Close'] * df_slice['Volume']
        avwap = df_slice['PV'].cumsum().sum() / df_slice['Volume'].cumsum().sum() if df_slice['Volume'].sum()>0 else df_slice['Close'].mean()
        # Alternative simple AVWAP
        cum_pv = (df_slice['Close'] * df_slice['Volume']).cumsum()
        cum_v = df_slice['Volume'].cumsum()
        avwap_series = cum_pv / cum_v
        avwap_now = float(avwap_series.iloc[-1])
        return avwap_now
    except:
        return float(df['Close'].ewm(span=20).mean().iloc[-1])

def analyze_stock(df):
    """Combines NIFTY500 + SNIPER + AUGMENTED logic"""
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['High20'] = df['High'].rolling(20).max()
    df['Vol20'] = df['Volume'].rolling(20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    high20 = float(last['High20']); vol20 = float(last['Vol20']); vol_now = float(last['Volume'])
    atr = float(last['ATR'])
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = -delta.where(delta<0,0).rolling(14).mean()
    rs = gain/loss
    rsi = float(100 - (100/(1+rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50
    
    # AVWAP
    avwap = calc_avwap(df)
    
    # POINTS (Nifty500 logic)
    points = 0
    if price > ema20: points+=20
    if ema20 > ema50: points+=20
    vol_ratio = vol_now/vol20 if vol20>0 else 1
    if vol_ratio>2: points+=20
    elif vol_ratio>1.5: points+=15
    elif vol_ratio>1.2: points+=10
    if price>=high20*0.995: points+=20
    elif price>=high20*0.98: points+=10
    if 60<=rsi<=75: points+=20
    elif 55<=rsi<=80: points+=10

    # SNIPER LOGIC (AVWAP)
    is_sniper = price > avwap and price > ema20 and vol_ratio>1.2 and rsi>60

    # TARGETS
    t1 = price + 1.5*atr
    t2 = price + 3*atr
    sl = max(ema20, price - 1.2*atr)
    rr = (t1-price)/(price-sl) if (price-sl)>0 else 0

    # WIN% BACKTEST
    wins=0; total=0
    for i in range(20, len(df)-5):
        if df['Close'].iloc[i] > df['EMA20'].iloc[i] and df['EMA20'].iloc[i] > df['EMA50'].iloc[i]:
            total+=1
            if float(df['Close'].iloc[i+5]) > float(df['Close'].iloc[i]): wins+=1
    winp = int(wins/total*100) if total>0 else 50
    winp = min(95, max(45, winp + (points-60)//2))

    return {
        "price": price, "points": points, "rsi": rsi, "vol": vol_ratio,
        "t1": t1, "t2": t2, "sl": sl, "rr": rr, "win": winp,
        "avwap": avwap, "sniper": is_sniper,
        "trend": price>ema20 and ema20>ema50,
        "breakout": price>=high20*0.98
    }

def main():
    regime, nifty_score, nifty_price, nifty_ema20, sh, sl, atr_pct = get_nifty()
    
    # NIFTY 500 list - using Nifty 100 for speed (you can replace with full 500 CSV)
    # To use full 500, upload nifty500list.csv and we will auto-read
    nifty500 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN","HDFC","ICICIGI","ADANIGREEN","ADANIPOWER","ZOMATO","PAYTM","NYKAA","DMART","PIDILIT","HAVELLS","GODREJCP","DABUR","MARICO","BERGEPAINT","SAIL","NMDC","BEL","HAL","IRCTC","IRFC","PFC","RECLTD","VEDL","JINDALSTEL","TATAPOWER","ADANITRANS","POLYCAB","KEI","TRENT","ABFRL","INDIGO","BANKBARODA","PNB","CANBK","IDFCFIRSTB","FEDERALBNK","AUBANK","MUTHOOTFIN","PEL","BIOCON","LUPIN","ALKEM","AUROPHARMA","GLENMARK"]
    
    symbols_ns = [s + ".NS" for s in nifty500]
    data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker')
    
    nifty500_picks = []
    sniper_picks = []
    breakout_picks = []
    
    for sym in nifty500:
        try:
            sym_ns = sym + ".NS"
            if sym_ns not in data.columns.get_level_values(0): continue
            df = data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df)<30 or df['Close'].isna().all(): continue
            
            res = analyze_stock(df)
            if res['points']>=60:
                item = {"sym": sym, **res}
                if res['trend']: nifty500_picks.append(item)
                if res['breakout']: breakout_picks.append(item)
                if res['sniper']: sniper_picks.append(item)
        except: continue

    # Rank by Win% + Points
    nifty500_picks = sorted(nifty500_picks, key=lambda x: (x['win'], x['points']), reverse=True)[:10]
    breakout_picks = sorted(breakout_picks, key=lambda x: x['vol'], reverse=True)[:7]
    sniper_picks = sorted(sniper_picks, key=lambda x: (x['win'], x['points']), reverse=True)[:7]

    # SHORT CLEAN MESSAGE - No cut
    msg = f"🤖 MASTER BOT - {date.today()}\n"
    msg += f"NIFTY {nifty_price:.0f} Score:{nifty_score}/100 {regime} ATR:{atr_pct:.1f}%\n"
    msg += f"{'✅ TRADE' if nifty_score>=60 else '🛑 NO TRADE'}\n"
    msg += f"--------------------------\n"
    msg += f"📈 NIFTY500 TOP (Win/Points):\n"
    for i,p in enumerate(nifty500_picks,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} {p['win']}% {p['points']}pts\n   ->{p['t1']:.0f} SL:{p['sl']:.0f} RR:{p['rr']:.1f}\n"
    
    msg += f"\n🚀 BREAKOUT:\n"
    for i,p in enumerate(breakout_picks,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} Vol:{p['vol']:.1f}x {p['points']}pts\n"
    
    msg += f"\n🎯 SNIPER AVWAP (Price>AVWAP):\n"
    for i,p in enumerate(sniper_picks,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f}>{p['avwap']:.0f} Win:{p['win']}% T:{p['t1']:.0f}\n"
    
    msg += f"\nLogic: Nifty500=Trend | Sniper=AVWAP | Brain=Regime"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
