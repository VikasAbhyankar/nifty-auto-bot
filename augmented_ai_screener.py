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
            print(e)

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
    # Points for Nifty
    nifty_score = 0
    if price > ema20: nifty_score += 30
    if ema20 > ema50: nifty_score += 30
    if atr_pct > 1.0: nifty_score += 20
    if price > sh * 0.99: nifty_score += 20
    
    if nifty_score >= 80:
        regime = "TRENDING_BULL"
    elif nifty_score >= 50:
        regime = "MILD_BULL"
    else:
        regime = "RANGE"
    reason = f"Score {nifty_score}/100, {price:.0f} > EMA20 {ema20:.0f}, ATR {atr_pct:.1f}%"
    return regime, reason, sh, sl, price, nifty_score

def calc_points(df):
    """Calculate 0-100 points for a stock"""
    last = df.iloc[-1]
    price = float(last['Close'])
    ema20 = float(last['EMA20'])
    ema50 = float(last['EMA50'])
    high20 = float(last['High20'])
    vol20 = float(last['Vol20'])
    vol_now = float(last['Volume'])
    
    # RSI simple
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = float(100 - (100 / (1 + rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50
    
    points = 0
    # 1. Trend (40 points)
    if price > ema20: points += 20
    if ema20 > ema50: points += 20
    # 2. Volume (20 points)
    vol_ratio = vol_now / vol20 if vol20>0 else 1
    if vol_ratio > 2: points += 20
    elif vol_ratio > 1.5: points += 15
    elif vol_ratio > 1.2: points += 10
    # 3. Breakout (20 points)
    if price >= high20 * 0.995: points += 20
    elif price >= high20 * 0.98: points += 10
    # 4. Momentum RSI (20 points)
    if 60 <= rsi <= 75: points += 20
    elif 55 <= rsi <= 80: points += 10
    
    return points, rsi, vol_ratio, price

def main():
    regime, reason, sh, sl, nifty_price, nifty_points = get_nifty_regime()
    
    nifty50 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN"]
    symbols_ns = [s + ".NS" for s in nifty50]
    
    data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker')
    
    all_stocks = []
    for sym in nifty50:
        try:
            sym_ns = sym + ".NS"
            if sym_ns in data.columns.get_level_values(0):
                df = data[sym_ns]
            else:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
            if len(df) < 30 or df['Close'].isna().all():
                continue
            df['EMA20'] = df['Close'].ewm(span=20).mean()
            df['EMA50'] = df['Close'].ewm(span=50).mean()
            df['High20'] = df['High'].rolling(20).max()
            df['Vol20'] = df['Volume'].rolling(20).mean()
            
            points, rsi, vol_ratio, price = calc_points(df)
            if points >= 40: # Only keep good stocks
                all_stocks.append({"sym": sym, "price": price, "points": points, "rsi": rsi, "vol": vol_ratio})
        except:
            continue

    # Rank by points
    all_stocks = sorted(all_stocks, key=lambda x: x['points'], reverse=True)
    
    # Categories
    trending = [s for s in all_stocks if s['points'] >= 60][:10]
    breakout = [s for s in all_stocks if s['vol'] > 1.8][:7]
    sniper = [s for s in all_stocks if s['points'] >= 75][:7]

    emoji = "✅" if nifty_points >= 70 else "⚠️" if nifty_points >= 50 else "🛑"
    decision = "TRADE ALLOWED - Trend Day" if nifty_points >= 60 else "CAUTION - Choppy"

    msg = f"🤖 AUGMENTED AI BRAIN - {date.today()}\n"
    msg += f"--------------------------\n"
    msg += f"NIFTY: {nifty_price:.0f} | Score: {nifty_points}/100 {emoji}\n"
    msg += f"Regime: {regime}\n{reason}\nHigh:{sh:.0f} Low:{sl:.0f}\n\n"
    msg += f"DECISION: {decision}\n"
    msg += f"--------------------------\n"
    msg += f"🏆 RANKED TRENDING (Points):\n"
    for i, p in enumerate(trending, 1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} | {p['points']}pts RSI:{p['rsi']:.0f} V:{p['vol']:.1f}x\n"
    
    msg += f"\n🚀 BREAKOUT RANK:\n"
    for i, p in enumerate(breakout, 1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} | {p['points']}pts\n"
    
    msg += f"\n🎯 SNIPER (75+ Points):\n"
    for i, p in enumerate(sniper, 1):
        msg += f"{i}. {p['sym']} | {p['points']}pts | STRONG BUY\n"
    
    msg += f"\n--------------------------\n"
    msg += f"Index Score: NIFTY {nifty_points}/100"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
