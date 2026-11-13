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
def ema(series, period):
    try:
        return series.ewm(span=period, adjust=False).mean()
    except:
        return series
def rsi_func(series, period=14):
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        r = 100 - (100 / (1 + rs))
        return r.fillna(50)
    except:
        return pd.Series([50]*len(series), index=series.index)
def macd_func(series):
    try:
        e12 = ema(series, 12)
        e26 = ema(series, 26)
        macd = e12 - e26
        sig = ema(macd, 9)
        return macd - sig
    except:
        return pd.Series([0]*len(series), index=series.index)
def adx_func(high, low, close, period=14):
    try:
        tr = pd.concat([high-low, (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = up.where((up > down) & (up > 0), 0)
        minus_dm = down.where((down > up) & (down > 0), 0)
        plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.rolling(period).mean().fillna(20)
    except:
        return pd.Series([20]*len(close), index=close.index)
class IndiaEngine:
    def cost(self, price, qty, is_sell=False):
        try:
            turnover = float(price) * float(qty)
            broker = min(20, turnover * 0.0003)
            exchange = turnover * 0.0000325
            stt = turnover * 0.001 if is_sell else 0
            stamp = turnover * 0.00003
            gst = (broker + exchange) * 0.18
            return broker + exchange + stt + stamp + gst
        except:
            return 0
    def backtest(self, df, signal):
        try:
            cash = 100000.0
            pos = 0
            equity = []
            trades = 0
            wins = 0
            entry = 0
            closes = df["Close"].values
            sigs = signal.values
            for i in range(len(closes)):
                try:
                    price = float(closes[i])
                    if price <= 0 or np.isnan(price):
                        equity.append(cash)
                        continue
                    s = bool(sigs[i]) if i < len(sigs) else False
                    if s and pos == 0:
                        qty = int(cash * 0.9 / price)
                        if qty > 0:
                            cash = cash - price * qty - self.cost(price, qty, False)
                            pos = qty
                            entry = price
                    elif (not s) and pos > 0:
                        cash = cash + price * pos - self.cost(price, pos, True)
                        trades = trades + 1
                        if price > entry:
                            wins = wins + 1
                        pos = 0
                    if pos > 0:
                        equity.append(cash + pos * price)
                    else:
                        equity.append(cash)
                except:
                    equity.append(cash)
            if not equity:
                return {"return": 0, "win": 0, "trades": 0, "maxDD": 0, "sharpe": 0}
            ret = (equity[-1] - 100000) / 100000 * 100
            win = wins / trades * 100 if trades > 0 else 0
            peak = np.maximum.accumulate(equity)
            denom = np.where(peak == 0, 1, peak)
            max_dd = float(((np.array(equity) - peak) / denom).min() * 100)
            rets = pd.Series(equity).pct_change().dropna()
            sharpe = 0
            if len(rets) > 2 and rets.std() > 0:
                sharpe = float(rets.mean() / rets.std() * np.sqrt(252))
            if np.isnan(sharpe):
                sharpe = 0
            return {"return": float(ret), "win": float(win), "trades": trades, "maxDD": float(max_dd), "sharpe": float(sharpe)}
        except:
            return {"return": 0, "win": 0, "trades": 0, "maxDD": 0, "sharpe": 0}
def safe_download(sym, period="2y", interval="1d"):
    try:
        if yf is None:
            return None
        full = sym
        if not sym.startswith("^"):
            full = str(sym) + ".NS"
        df = yf.download(full, period=period, interval=interval, progress=False, auto_adjust=True, timeout=30)
        if df is None or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.get_level_values(0)
            except:
                pass
        df = df.copy()
        if "Close" not in df.columns:
            return None
        df = df.dropna(subset=["Close"])
        if len(df) < 50:
            return None
        return df
    except:
        print("Download fail " + str(sym))
        return None
def agent4_risk():
    try:
        if yf is None:
            return "UNKNOWN", "yfinance missing"
        df = None
        for ticker in ["^NSEI", "NIFTYBEES.NS", "^NSEBANK"]:
            try:
                tmp = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True, timeout=30)
                if tmp is not None and len(tmp) > 60:
                    if isinstance(tmp.columns, pd.MultiIndex):
                        try:
                            tmp.columns = tmp.columns.get_level_values(0)
                        except:
                            pass
                    tmp = tmp.dropna(subset=["Close"])
                    if len(tmp) > 60:
                        df = tmp
                        print("NIFTY OK using " + ticker + " rows " + str(len(tmp)))
                        break
            except:
                continue
        if df is None:
            return "UNKNOWN", "NIFTY data unavailable - Use 50 percent size"
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        last = df.iloc[-1]
        price = float(last["Close"])
        e20 = float(last["EMA20"])
        e50 = float(last["EMA50"])
        if e20 > e50:
            return "BULLISH", "NIFTY " + str(round(price, 0)) + " Bullish - 100 percent size"
        if e20 < e50:
            return "BEARISH", "NIFTY " + str(round(price, 0)) + " Bearish - NO BUY"
        return "SIDEWAYS", "NIFTY " + str(round(price, 0)) + " Sideways - 50 percent size"
    except Exception as e:
        print("Risk fail " + str(e))
        return "UNKNOWN", "Risk check failed - 50 percent size"
def send_telegram(msg):
    if not BOT_TOKEN or not requests or not CHAT_IDS:
        print("Telegram skipped")
        print(msg)
        return
    for cid in CHAT_IDS:
        try:
            url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
            r = requests.post(url, json={"chat_id": str(cid), "text": msg}, timeout=20)
            print("Telegram to " + str(cid) + ": " + str(r.status_code))
            time.sleep(1)
        except:
            print("Telegram fail " + str(cid))
def main():
    print("7 AGENTS START - FIXED NIFTY + FIXED STRATEGY")
    engine = IndiaEngine()
    m_status, m_detail = agent4_risk()
    print("Market: " + m_status + " - " + m_detail)
    results = []
    for sym in STOCKS:
        try:
            df = safe_download(sym, period="2y", interval="1d")
            if df is None:
                print(str(sym) + ": No data")
                continue
            try:
                df["EMA20"] = ema(df["Close"], 20)
                df["EMA50"] = ema(df["Close"], 50)
                df["EMA200"] = ema(df["Close"], 200)
                df["RSI"] = rsi_func(df["Close"], 14)
                df["MACD"] = macd_func(df["Close"])
                df["ADX"] = adx_func(df["High"], df["Low"], df["Close"], 14)
                df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean().fillna(0)
                vwap = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum().replace(0, np.nan)
                vwap = vwap.fillna(df["Close"])
                vwap_dist = (df["Close"] - vwap) / vwap.replace(0, np.nan) * 100
                vwap_dist = vwap_dist.fillna(0)
                vol_spike = df["Volume"] / df["Volume"].rolling(20).mean().replace(0, np.nan)
                vol_spike = vol_spike.fillna(1)
                mom_12_1 = df["Close"].pct_change(252) - df["Close"].pct_change(21)
                mom_12_1 = mom_12_1.fillna(0)
                mom20 = df["Close"].pct_change(20).fillna(0)
                ret5 = df["Close"].pct_change(5).fillna(0)
                hm = (df["EMA20"] > df["EMA50"]) & (df["RSI"] > 50) & (df["RSI"] < 78) & (df["MACD"] > 0)
                optimum = (df["Close"] > df["EMA200"]) & (df["EMA20"] > df["EMA50"]) & (df["RSI"] > 45) & (df["RSI"] < 70) & (df["MACD"] > 0) & (df["ADX"] > 15) & (ret5 > -0.03)
                hm_res = engine.backtest(df, hm)
                opt_res = engine.backtest(df, optimum)
               
