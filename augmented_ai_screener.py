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
        except: pass

def get_nifty_regime():
    df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    atr = float(last['ATR']); atr_pct = (atr / price) * 100
    sh = float(df['High'].tail(20).max()); sl = float(df['Low'].tail(20).min())
    nifty_score = 0
    if price > ema20: nifty_score += 30
    if ema20 > ema50: nifty_score += 30
    if atr_pct > 1.0: nifty_score += 20
    if price > sh * 0.99: nifty_score += 20
    regime = "TRENDING_BULL" if nifty_score >= 80 else "MILD_BULL" if nifty_score >= 50 else "RANGE"
    reason = f"Score {nifty_score}/100, {price:.0f} > EMA20 {ema20:.0f}, ATR {atr_pct:.1f}%"
    return regime, reason, sh, sl, price, nifty_score

def calc_points_and_levels(df):
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    high20 = float(last['High20']); vol20 = float(last['Vol20']); vol_now = float(last['Volume'])
    atr = float(last['ATR'])
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = float(100 - (100 / (1 + rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50
    
    points = 0
    if price > ema20: points += 20
    if ema20 > ema50: points += 20
    vol_ratio = vol_now / vol20 if vol20>0 else 1
    if vol_ratio > 2: points += 20
    elif vol_ratio > 1.5: points += 15
    elif vol_ratio > 1.2: points += 10
    if price >= high20 * 0.995: points += 20
    elif price >= high20 * 0.98: points += 10
    if 60 <= rsi <= 75: points += 20
    elif 55 <= rsi <= 80: points += 10

    # --- TARGET / SL LOGIC ---
    # Target 1 = Price + 1.5 * ATR (intraday/swing)
    # Target 2 = Price + 3 * ATR (positional)
    # SL = EMA20 or Price - 1 * ATR, whichever is higher
    target1 = price + (1.5 * atr)
    target2 = price + (3.0 * atr)
    sl_atr = price - (1.2 * atr)
    stop_loss = max(ema20, sl_atr) # Smart SL - below EMA20
    
    risk = price - stop_loss
    reward1 = target1 - price
    rr_ratio = reward1 / risk if risk > 0 else 0

    return points, rsi, vol_ratio, price, target1, target2, stop_loss, rr_ratio, atr

def main():
    regime, reason, sh, sl, nifty_price, nifty_points = get_nifty_regime()
    nifty50 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN"]
    symbols_ns = [s + ".NS" for s in nifty50]
    data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker')
    
    all_stocks = []
    for sym in nifty50:
        try:
            sym_ns = sym + ".NS"
            if sym_ns not in data.columns.get_level_values(0): continue
            df = data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df) < 30 or df['Close'].isna().all(): continue
            df['EMA20'] = df['Close'].ewm(span=20).mean()
            df['EMA50'] = df['Close'].ewm(span=50).mean()
            df['High20'] = df['High'].rolling(20).max()
            df['Vol20'] = df['Volume'].rolling(20).mean()
            df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
            
            points, rsi, vol_ratio, price, t1, t2, stop, rr, atr = calc_points_and_levels(df)
            if points >= 60:
                all_stocks.append({"sym": sym, "price": price, "points": points, "rsi": rsi, "vol": vol_ratio, "t1": t1, "t2": t2, "sl": stop, "rr": rr})
        except: continue

    all_stocks = sorted(all_stocks, key=lambda x: x['points'], reverse=True)
    trending = all_stocks[:10]

    emoji = "✅" if nifty_points >= 70 else "🛑"
    decision = "TRADE ALLOWED - Trend Day" if nifty_points >= 60 else "CAUTION"

    msg = f"🤖 AUGMENTED AI BRAIN - {date.today()}\n"
    msg += f"NIFTY: {nifty_price:.0f} Score:{nifty_points}/100 {emoji} {regime}\n{reason}\n\n"
    msg += f"DECISION: {decision}\n"
    msg += f"--------------------------\n"
    msg += f"🏆 TOP RANKED (Target/SL):\n"
    for i, p in enumerate(trending, 1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} ({p['points']}pts)\n"
        msg += f"   T1:{p['t1']:.0f} T2:{p['t2']:.0f} SL:{p['sl']:.0f} RR 1:{p['rr']:.1f}\n"
    
    msg += f"\n🎯 SNIPER 80+ pts:\n"
    for p in [s for s in all_stocks if s['points'] >= 80][:5]:
        msg += f"{p['sym']} Buy {p['price']:.0f} -> {p['t1']:.0f} SL {p['sl']:.0f}\n"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
