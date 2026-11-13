import os
import sys
import time
import traceback
import pandas as pd
import numpy as np
NL = chr(10)
try:
    import yfinance as yf
except:
    yf = None
try:
    import requests
except:
    requests = None
try:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
except:
    IST = None
from datetime import datetime

def now_str():
    try:
        if IST:
            return datetime.now(IST).strftime("%d-%m %H:%M IST")
        return datetime.now().strftime("%d-%m %H:%M")
    except:
        return "Now"

BOT_TOKEN = os.getenv("TELEGRAM_FNO_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "") or os.getenv("BOT_TOKEN", "")
CHAT_FROM_ENV = os.getenv("TELEGRAM_FNO_CHAT_ID", "") or os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("CHAT_ID", "")
CHAT_IDS = []
for cid in ["5239892901", "7507879668", CHAT_FROM_ENV]:
    if cid and str(cid).strip() and str(cid).strip() not in CHAT_IDS:
        CHAT_IDS.append(str(cid).strip())

STOCKS = ["BAJFINANCE","SHRIRAMFIN","HDFCLIFE","SBILIFE","BAJAJFINSV","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","TITAN","ITC","LT","TATAPOWER","TATASTEEL","AXISBANK","KOTAKBANK","MARUTI","SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","HINDUNILVR","ASIANPAINT","NESTLEIND","BRITANNIA","DABUR","COLPAL","GODREJCP","MARICO","ULTRACEMCO","GRASIM","HINDALCO","JSWSTEEL","JINDALSTEL","NTPC","ONGC","IOC","BPCL","HINDPETRO","GAIL","COALINDIA","POWERGRID","ADANIPORTS","ADANIENT","BEL","HAL","BHEL"]

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def rsi_func(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    rs = g / l.replace(0, np.nan)
    r = 100 - (100 / (1 + rs))
    return r.fillna(50)

def macd_hist(s):
    return ema(s, 12) - ema(s, 26) - ema(ema(s, 12) - ema(s, 26), 9)

def adx_func(h, l, c, p=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(p).mean()
    up = h - h.shift(1)
    dn = l.shift(1) - l
    pdm = up.where((up > dn) & (up > 0), 0)
    mdm = dn.where((dn > up) & (dn > 0), 0)
    pdi = 100 * pdm.rolling(p).mean() / atr.replace(0, np.nan)
    mdi = 100 * mdm.rolling(p).mean() / atr.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.rolling(p).mean().fillna(20)

def clean_df(df):
    if df is None:
        return None
    if len(df) < 50:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.copy()
    if "Close" not in df.columns:
        return None
    df = df.dropna(subset=["Close"])
    if len(df) < 50:
        return None
    return df

def cost_calc(price, qty, is_sell):
    turnover = float(price) * float(qty)
    broker = min(20, turnover * 0.0003)
    exch = turnover * 0.0000325
    stt = turnover * 0.001 if is_sell else 0
    stamp = turnover * 0.00003
    gst = (broker + exch) * 0.18
    return broker + exch + stt + stamp + gst

def backtest(df, sig):
    cash = 100000.0
    pos = 0
    equity = []
    trades = 0
    wins = 0
    entry = 0
    closes = df["Close"].values
    sigs = sig.values
    for i in range(len(closes)):
        price = float(closes[i])
        if price <= 0 or np.isnan(price):
            equity.append(cash)
            continue
        s = bool(sigs[i]) if i < len(sigs) else False
        if s and pos == 0:
            qty = int(cash * 0.9 / price)
            if qty > 0:
                cash = cash - price * qty - cost_calc(price, qty, False)
                pos = qty
                entry = price
        elif (not s) and pos > 0:
            cash = cash + price * pos - cost_calc(price, pos, True)
            trades = trades + 1
            if price > entry:
                wins = wins + 1
            pos = 0
        if pos > 0:
            equity.append(cash + pos * price)
        else:
            equity.append(cash)
    if not equity:
        return {"return": 0, "win": 0, "trades": 0, "sharpe": 0}
    ret = (equity[-1] - 100000) / 100000 * 100
    win = wins / trades * 100 if trades > 0 else 0
    rets = pd.Series(equity).pct_change().dropna()
    sharpe = 0
    if len(rets) > 2 and rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(252))
    if np.isnan(sharpe):
        sharpe = 0
    return {"return": float(ret), "win": float(win), "trades": trades, "sharpe": float(sharpe)}

def safe_download(sym):
    if yf is None:
        return None
    full = sym
    if not sym.startswith("^"):
        full = str(sym) + ".NS"
    try:
        df = yf.download(full, period="2y", interval="1d", progress=False, auto_adjust=True, timeout=30)
    except:
        print("Download fail " + str(sym))
        return None
    return clean_df(df)

def agent4_risk():
    if yf is None:
        return "UNKNOWN", "yfinance missing - Use 50 percent size"
    df = None
    used = "NONE"
    try:
        t1 = yf.download("^NSEI", period="6mo", interval="1d", progress=False, auto_adjust=True, timeout=30)
        if t1 is not None and len(t1) > 60:
            df = t1
            used = "^NSEI"
    except:
        df = None
    if df is None:
        try:
            t2 = yf.download("NIFTYBEES.NS", period="6mo", interval="1d", progress=False, auto_adjust=True, timeout=30)
            if t2 is not None and len(t2) > 60:
                df = t2
                used = "NIFTYBEES"
        except:
            df = None
    if df is None:
        try:
            t3 = yf.download("^NSEBANK", period="6mo", interval="1d", progress=False, auto_adjust=True, timeout=30)
            if t3 is not None and len(t3) > 60:
                df = t3
                used = "NSEBANK"
        except:
            df = None
    if df is None:
        return "UNKNOWN", "NIFTY data unavailable - Use 50 percent size"
    df = clean_df(df)
    if df is None:
        if used == "^NSEI":
            return "UNKNOWN", "NIFTY data short - Use 50 percent size"
        return "UNKNOWN", "NIFTY data unavailable - Use 50 percent size"
    if len(df) < 60:
        df2 = None
        try:
            df2 = yf.download("^NSEI", period="1y", interval="1d", progress=False, auto_adjust=True, timeout=30)
        except:
            df2 = None
        df
