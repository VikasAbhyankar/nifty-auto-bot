# BALA FRESH + PROXY V1.2 - FINAL - START 9:30 AM
# Strategy 1A: FRESH CROSS - Monthly Strong + Weekly Pullback + 15m EMA200>EMA400 Fresh
# Strategy 1B: RET-200 - 15m Price near EMA200 (0.3%) + EMA200>EMA400 + HILEGA - BSE @3850 case
# Strategy 2: PROXY AVWP - Chartink PROXY AVWP 20112026 - Daily Breakout + Vol + RSI
# HM Filter: RSI(9) + EMA(3) on RSI + WMA(21) on RSI + 50 Filter - HILEGA only, MILEGA = SKIP
# Schedule: 9:30 AM FULL + Every 15 min QUICK (Fresh + Ret only) | PAPER ONLY
import os, sys, time, math, traceback, csv, argparse
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor

try:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "") or os.getenv("TELEGRAM_FNO_BOT_TOKEN", "")
CHAT_FROM_ENV = os.getenv("TELEGRAM_CHAT_ID", "") or os.getenv("TELEGRAM_FNO_CHAT_ID", "")
UPSTOX_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
UPSTOX_ENABLED = bool(UPSTOX_TOKEN)
UPSTOX_BASE = "https://api.upstox.com/v3"

CHAT_IDS = []
_raw_ids = []
if CHAT_FROM_ENV:
    for x in str(CHAT_FROM_ENV).split(","):
        x = x.strip()
        if x and x not in _raw_ids:
            _raw_ids.append(x)
for fid in ["5239892901", "9000971028"]:
    if fid not in _raw_ids:
        _raw_ids.append(fid)
CHAT_IDS = _raw_ids
print(f"BALA V1.2 Targets: {CHAT_IDS} | Upstox: {UPSTOX_ENABLED}")

PAPER_FILE = "paper_trades_fresh_cross.csv"
PAPER_QTY = 100

_NIFTY500_RAW = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","TATAMOTORS","ETERNAL","CDSL","PNB","KALYANKJIL","TITAN","ITC","LT","AXISBANK","KOTAKBANK","BAJFINANCE","HINDUNILVR","MARUTI","TATASTEEL","JSWSTEEL","ULTRACEMCO","ADANIENT","ADANIPORTS","POWERGRID","NTPC","ONGC","COALINDIA","BPCL","IOC","HDFCLIFE","SBILIFE","ICICIPRULI","BAJAJFINSV","M&M","EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","APOLLOHOSP","DIVISLAB","SUNPHARMA","CIPLA","DRREDDY","GRASIM","HINDALCO","VEDL","TATAPOWER","ADANIGREEN","ADANIPOWER","IRFC","RVNL","HAL","BEL","BDL","MAZAGON","COCHINSHIP","BHEL","NHPC","SJVN","PFC","RECLTD","HUDCO","NBCC","IRCON","RAILTEL","TITAGARH","JUPITERWAGONS","GENSOL","SUZLON","IREDA","TATATECH","TATAELXSI","KPITTECH","PERSISTENT","COFORGE","LTIM","MPHASIS","TECHM","WIPRO","HCLTECH","ZOMATO","PAYTM","NYKAA","POLICYBZR","DELHIVERY","DMART","TRENT","VBL","NESTLEIND","BRITANNIA","DABUR","MARICO","GODREJCP","COLPAL","TATACONSUM","HATSUN","PAGEIND","RELAXO","CAMPUS","BATAINDIA","METROBRANDS","KAYNES","DIXON","AMBER","PGEL","SYRMA","CROMPTON","HAVELLS","POLYCAB","KEI","FINOLEX","SUPREMEIND","ASTRAL","APLAPOLLO","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDCOPPER","MOIL","GMDCLTD","MANGLMCEM","RAMCOCEM","SHREECEM","ACC","AMBUJACEM","DALMIABHA","JKCEMENT","STAR","ORIENTCEM","HEIDELBERG","PRISMJOHN","SAGAR","INDIACEM","CERA","KAJARIA","SOMANY","HSIL","RAJESHEXPO","THANGAMAYIL","KALYAN","PNBGILTS","PNBHOUSING","CANFIN","LICHSGFIN","GICHSGFIN","REPCOHOME","AAVAS","HOMEFIRST","APTUS","MANAPPURAM","MUTHOOTFIN","IIFL","CHOLAFIN","SHRIRAMFIN","MAHABANK","CENTRALBK","UCOBANK","BANKOFMAHA","INDIANB","IOB","PSB","J&KBANK","KARURVYSYA","FEDERALBNK","RBLBANK","IDFCFIRSTB","YESBANK","BANDHANBNK","CSBBANK","DCBBANK","CUB","TMB","KARNATAKA","SOUTHBANK","INDUSINDBK","AUBANK","EQUITASBNK","UJJIVANSFB","CAPITALSFB","ESAFSFB","JANA","SURYO","SPANDANA","CREDITACC","ARMAN","FIVE-STAR","SATIN","UJJIVAN","MFIN","MASFIN","PAISALO","CAPRIGLOBAL","PIRAMAL","JMFINANCIL","MOTILALOFS","ANGELONE","BSE","MCX","CDSL","NSDL","CAMS","KFINTECH","ANANDRATHI","NUVAMA","360ONE","IIFLSEC","GEOJIT","SMC","SHAREINDIA","EMKAY","MONARCH","PRUDENT","DPABHUSHAN","MANINFRA","OBEROIRLTY","PRESTIGE","BRIGADE","SOBHA","GODREJPROP","DLF","PHOENIXLTD","MACPOWER","ASHIANA","SUNTERRA","SHRIRAMPROP","PURAVANKARA","ARVIND","VARDHMAN","TRIDENT","WELSPUNLIV","INDOCOUNT","GOKEX","RAYMOND","KPRMILL","PAGE","WELCORP","JINDALSAW","RATNAMANI","MAHSEAMLES","APL","JTLIND","MANAKSIA","JINDALPOLY","HIMATSEIDE","BANSWRAS","RSWM","DONEAR","ALOKINDS","FILATEX","VTL","SUTLEJTEX","NITINSPIN","GHCL","GHCLTEXTIL","VARDHMANACR","INDORAMA","JBF","GARDENREACH","GRSE","PARADEEP","FACT","RCF","GSFC","GNFC","DEEPAKFERT","ZUARI","MANGCHE","CHAMBLFERT","NFL","KRIBHCO","COROMANDEL","UPL","PIIND","SUMICHEM","ATUL","AARTIIND","DEEPAKNTR","FINEORG","ALKYLAMINE","BALAMINES","VINATIORGA","CLEAN","ROSSARI","NEOGEN","ANURAS","GOPAL","LAXMI","TATACHEM","DCMSHRIRAM","TATAGU","IGL","MGL","GUJGASLTD","PETRONET","GAIL","OIL","MRPL","CHENNPETRO","NRL","BALMERLAWRIE","GULFOILLUB","CASTROLIND","SAVITA","APARINDS","TIDEWATER","PANAMAPET","GANDHARTU","MORGANITE","CARBORUNIV","GRINDWELL","WENDT","MMTC","STCINDIA","KIOCL","FERRO","IMFA","SHAKTI","JSL","JINDALSTEL"]
NIFTY500 = list(dict.fromkeys(_NIFTY500_RAW))

def safe_float(x, default=0.0):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except Exception:
        return default

def flatten_df(df):
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    new_cols = []
    for c in df.columns:
        lc = str(c).lower()
        if lc in ["open", "high", "low", "close", "volume"]:
            new_cols.append(str(c).capitalize())
        else:
            new_cols.append(str(c))
    df.columns = new_cols
    cols = {}
    for c in df.columns:
        lc = str(c).lower()
        if lc == "open":
            cols[c] = "Open"
        elif lc == "high":
            cols[c] = "High"
        elif lc == "low":
            cols[c] = "Low"
        elif lc == "close":
            cols[c] = "Close"
        elif lc == "volume":
            cols[c] = "Volume"
    df = df.rename(columns=cols)
    return df

def calc_rsi(series, period=14):
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss.replace(0, 1e-9))
        return 100 - (100 / (1 + rs))
    except Exception:
        return pd.Series([50] * len(series), index=series.index)

def calc_atr(df, n=14):
    try:
        h = df["High"]
        l = df["Low"]
        c = df["Close"]
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / n, adjust=False).mean()
    except Exception:
        return pd.Series([0] * len(df), index=df.index)

def upstox_headers():
    return {"Authorization": f"Bearer {UPSTOX_TOKEN}", "Accept": "application/json"}

def to_upstox_key(symbol):
    if symbol == "^NSEI":
        return "NSE_INDEX|Nifty 50"
    if symbol == "^NSEBANK":
        return "NSE_INDEX|Nifty Bank"
    base = symbol.replace(".NS", "").replace("-", "_").upper()
    return f"NSE_EQ|{base}"

def upstox_live_price(instrument_key):
    if not UPSTOX_ENABLED:
        return None
    try:
        r = requests.get(f"{UPSTOX_BASE}/market-quote/quotes", headers=upstox_headers(), params={"instrument_key": instrument_key}, timeout=10)
        if r.status_code != 200:
            return None
        d = r.json().get("data", {}).get(instrument_key, {})
        lp = d.get("last_price") or d.get("ltp")
        return float(lp) if lp else None
    except Exception:
        return None

def upstox_candles_to_df(candles):
    if not candles:
        return None
    try:
        if len(candles[0]) > 5:
            cols = ["ts", "Open", "High", "Low", "Close", "Volume", "OI"]
        else:
            cols = ["ts", "Open", "High", "Low", "Close", "Volume"]
        df = pd.DataFrame(candles, columns=cols)
        df = df[["ts", "Open", "High", "Low", "Close", "Volume"]]
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts").sort_index()
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        print(f"Upstox df convert err {e}")
        return None

def get_upstox_candles(symbol, interval="day", days_back=365):
    if not UPSTOX_ENABLED:
        return None
    try:
        ikey = to_upstox_key(symbol)
        now = datetime.now(IST)
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if interval in ["30minute", "1hour", "15minute"]:
            url = f"{UPSTOX_BASE}/market-candle/intraday/{ikey}/{interval}"
            r = requests.get(url, headers=upstox_headers(), timeout=20)
        else:
            url = f"{UPSTOX_BASE}/market-candle/historical/{ikey}/{interval}/{to_date}/{from_date}"
            r = requests.get(url, headers=upstox_headers(), timeout=25)
        if r.status_code != 200:
            return None
        candles = r.json().get("data", {}).get("candles", [])
        return upstox_candles_to_df(candles)
    except Exception as e:
        print(f"Upstox candle err {symbol} {e}")
        return None

def get_data_safe(symbol, period="1y", interval="1d"):
    upstox_interval = "day"
    days_back = 365
    if interval == "1d":
        upstox_interval = "day"
        days_back = 365
    elif interval == "1wk":
        upstox_interval = "week"
        days_back = 730
    elif interval == "1mo":
        upstox_interval = "month"
        days_back = 1825
    elif interval == "1h":
        upstox_interval = "1hour"
        days_back = 30
    if UPSTOX_ENABLED:
        df = get_upstox_candles(symbol, upstox_interval, days_back)
        if df is not None and len(df) >= 50:
            try:
                live = upstox_live_price(to_upstox_key(symbol))
                if live and live > 0:
                    df.loc[df.index[-1], "Close"] = live
            except Exception:
                pass
            return flatten_df(df)
    try:
        ticker = symbol if symbol.startswith("^") else symbol + ".NS"
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False, timeout=25)
        df = flatten_df(df)
        if df is None or len(df) < 50:
            return None
        return df
    except Exception:
        return None

def get_15m_df(symbol):
    try:
        ticker = symbol + ".NS"
        df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True, timeout=25)
        df = flatten_df(df)
        if df is None or len(df) < 50:
            return None
        return df
    except Exception:
        return None

# ===== HM FILTER - HILEGA / MILEGA =====
def check_hm_15m(df_15):
    try:
        if df_15 is None or len(df_15) < 30:
            return {"signal": "NO_DATA", "rsi9": 0, "ema3": 0, "wma21": 0}
        rsi9_series = calc_rsi(df_15["Close"], 9)
        rsi9 = safe_float(rsi9_series.iloc[-1])
        rsi9_prev = safe_float(rsi9_series.iloc[-2])
        ema3_series = rsi9_series.ewm(span=3, adjust=False).mean()
        ema3 = safe_float(ema3_series.iloc[-1])
        ema3_prev = safe_float(ema3_series.iloc[-2])
        wma21_series = rsi9_series.rolling(21).apply(lambda x: np.dot(x, np.arange(1, 22)) / np.arange(1, 22).sum(), raw=True)
        wma21 = safe_float(wma21_series.iloc[-1])
        wma21_prev = safe_float(wma21_series.iloc[-2])
        # HILEGA = RSI9 crosses above EMA3 AND above WMA21 AND RSI9 > 50
        # Cross ya already above - dono ko HILEGA maanenge, kyunki 15 min me cross miss ho sakta hai
        hilega = (rsi9 > ema3 and rsi9 > wma21 and rsi9 > 50) and (rsi9_prev <= ema3_prev or rsi9_prev <= wma21_prev or True)
        # Strict cross check: agar abhi upar hai aur pehle neeche tha toh fresh HILEGA, agar pehle se upar hai toh HILEGA HOLD
        if rsi9 > ema3 and rsi9 > wma21 and rsi9 > 50:
            if rsi9_prev <= ema3_prev or rsi9_prev <= wma21_prev:
                sig = "HILEGA"
            else:
                sig = "HILEGA_HOLD"
        elif rsi9 < ema3 and rsi9 < wma21 and rsi9 < 50:
            sig = "MILEGA"
        else:
            sig = "NEUTRAL"
        return {"signal": sig, "rsi9": round(rsi9, 1), "ema3": round(ema3, 1), "wma21": round(wma21, 1), "rsi9_prev": round(rsi9_prev, 1)}
    except Exception as e:
        print(f"HM err {e}")
        return {"signal": "NO_DATA", "rsi9": 0, "ema3": 0, "wma21": 0}

# ===== STRATEGY 1A - FRESH CROSS =====
def check_fresh_cross_strategy(symbol, df_15=None):
    try:
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        if mo is None or len(mo) < 21:
            return None
        mo_close = mo["Close"]
        mo_ema8 = safe_float(mo_close.ewm(span=8, adjust=False).mean().iloc[-1])
        mo_ema20 = safe_float(mo_close.ewm(span=20, adjust=False).mean().iloc[-1])
        mo_rsi = safe_float(calc_rsi(mo_close, 14).iloc[-1])
        if not (mo_ema8 > mo_ema20 and mo_rsi > 60):
            return None
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk) < 22:
            return None
        wk_close = safe_float(wk["Close"].iloc[-1])
        wk_open = safe_float(wk["Open"].iloc[-1])
        wk_prev_close = safe_float(wk["Close"].iloc[-2])
        wk_ema20 = safe_float(wk["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        if not (wk_close > wk_ema20):
            return None
        if not (wk_close <= wk_ema20 * 1.03):
            return None
        if not (wk_close > wk_open):
            return None
        if not (wk_close > wk_prev_close):
            return None
        if df_15 is None:
            df_15 = get_15m_df(symbol)
        if df_15 is None or len(df_15) < 405:
            return None
        e200 = df_15["Close"].ewm(span=200, adjust=False).mean()
        e400 = df_15["Close"].ewm(span=400, adjust=False).mean()
        e200_now = safe_float(e200.iloc[-1])
        e400_now = safe_float(e400.iloc[-1])
        e200_prev = safe_float(e200.iloc[-2])
        e400_prev = safe_float(e400.iloc[-2])
        if not (e200_now > e400_now and e200_prev <= e400_prev):
            return None
        # HM Filter - MILEGA = SKIP
        hm = check_hm_15m(df_15)
        if hm["signal"] == "MILEGA":
            print(f"  Fresh Cross {symbol} SKIP - HM MILEGA RSI9 {hm['rsi9']}")
            return None
        df_d = get_data_safe(symbol, period="6mo", interval="1d")
        if df_d is None or len(df_d) < 30:
            return None
        cmp_ = safe_float(df_d["Close"].iloc[-1])
        atr = safe_float(calc_atr(df_d).iloc[-1])
        entry_low = round(cmp_ * 0.998, 2)
        entry_high = round(cmp_, 2)
        sl_by_ema = round(wk_ema20 * 0.996, 2)
        sl_by_pct = round(cmp_ * 0.992, 2)
        sl = round(min(sl_by_ema, sl_by_pct), 2)
        if sl % 1 == 0:
            sl -= 0.30
        risk = entry_high - sl
        if risk <= 0:
            risk = round(cmp_ * 0.008, 2)
            sl = round(cmp_ - risk, 2)
        t1 = round(entry_high + risk * 1.5, 2)
        t2 = round(entry_high + risk * 2.5, 2)
        sl_pct = round(risk / entry_high * 100, 2)
        score = 80
        if mo_rsi > 65:
            score += 10
        if mo_rsi > 70:
            score += 5
        dist_w = abs(wk_close - wk_ema20) / wk_ema20 * 100
        if dist_w <= 1.0:
            score += 5
        if hm["signal"] == "HILEGA":
            score += 5
        prob = min(95, score)
        win = min(92, 70 + (score - 80) * 1.0)
        return {"symbol": symbol, "strategy": "FRESH CROSS", "tag": "FRESH CROSS", "emoji": "🔥", "cmp": round(cmp_, 2), "entry_low": entry_low, "entry_high": entry_high, "sl": sl, "t1": t1, "t2": t2, "sl_pct": sl_pct, "risk": round(risk, 2), "score": score, "prob": prob, "win": win, "monthly_ema8": round(mo_ema8, 2), "monthly_ema20": round(mo_ema20, 2), "monthly_rsi": round(mo_rsi, 1), "weekly_close": round(wk_close, 2), "weekly_ema20": round(wk_ema20, 2), "weekly_open": round(wk_open, 2), "weekly_prev_close": round(wk_prev_close, 2), "dist_weekly_pct": round(dist_w, 2), "e200_now": round(e200_now, 2), "e400_now": round(e400_now, 2), "e200_prev": round(e200_prev, 2), "e400_prev": round(e400_prev, 2), "atr": round(atr, 2), "hm": hm}
    except Exception as e:
        print(f"Fresh Cross {symbol} err {e}")
        return None

# ===== STRATEGY 1B - RET-200 - NEW - BSE @3850 CASE =====
def check_ret200_strategy(symbol, df_15=None):
    try:
        # Monthly + Weekly - same as Fresh Cross - trend strong hona chahiye
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        if mo is None or len(mo) < 21:
            return None
        mo_close = mo["Close"]
        mo_ema8 = safe_float(mo_close.ewm(span=8, adjust=False).mean().iloc[-1])
        mo_ema20 = safe_float(mo_close.ewm(span=20, adjust=False).mean().iloc[-1])
        mo_rsi = safe_float(calc_rsi(mo_close, 14).iloc[-1])
        if not (mo_ema8 > mo_ema20 and mo_rsi > 60):
            return None
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk) < 22:
            return None
        wk_close = safe_float(wk["Close"].iloc[-1])
        wk_open = safe_float(wk["Open"].iloc[-1])
        wk_prev_close = safe_float(wk["Close"].iloc[-2])
        wk_ema20 = safe_float(wk["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        if not (wk_close > wk_ema20):
            return None
        if not (wk_close <= wk_ema20 * 1.03):
            return None
        if not (wk_close > wk_open):
            return None
        if not (wk_close > wk_prev_close):
            return None
        if df_15 is None:
            df_15 = get_15m_df(symbol)
        if df_15 is None or len(df_15) < 405:
            return None
        # 15m EMA200 / EMA400
        e200_series = df_15["Close"].ewm(span=200, adjust=False).mean()
        e400_series = df_15["Close"].ewm(span=400, adjust=False).mean()
        e200_now = safe_float(e200_series.iloc[-1])
        e400_now = safe_float(e400_series.iloc[-1])
        cmp_15 = safe_float(df_15["Close"].iloc[-1])
        low_15 = safe_float(df_15["Low"].iloc[-1])
        open_15 = safe_float(df_15["Open"].iloc[-1])
        # Rule 1: EMA200 > EMA400 - trend up, fresh cross zaroori nahi
        if not (e200_now > e400_now):
            return None
        # Rule 2: Price EMA200 ke paas hai - 0.3% ke andar, aur EMA200 ke upar hold kar raha hai
        # BSE case: CMP 3865, EMA200 3850, distance 0.39% - thoda loose rakha 0.5% tak
        if not (cmp_15 >= e200_now):
            return None
        dist_pct = (cmp_15 - e200_now) / e200_now * 100 if e200_now > 0 else 99
        if not (dist_pct <= 0.5):
            return None
        # Rule 3: Last candle green - retracement khatam
        if not (cmp_15 > open_15):
            return None
        # Rule 4: HM - HILEGA mandatory for RET-200, MILEGA = SKIP
        hm = check_hm_15m(df_15)
        if hm["signal"] not in ["HILEGA", "HILEGA_HOLD"]:
            print(f"  RET-200 {symbol} SKIP - HM {hm['signal']} RSI9 {hm['rsi9']}")
            return None
        # Entry / SL / Target - RET-200 ka SL EMA200 ke neeche hai
        df_d = get_data_safe(symbol, period="6mo", interval="1d")
        if df_d is None or len(df_d) < 30:
            return None
        cmp_ = safe_float(df_d["Close"].iloc[-1])
        atr = safe_float(calc_atr(df_d).iloc[-1])
        # Entry: EMA200 ke paas - CMP hi entry hai, kyunki retracement pe hi khade hain
        entry_low = round(max(e200_now, cmp_ * 0.998), 2)
        entry_high = round(cmp_, 2)
        if entry_low >= entry_high:
            entry_low = round(cmp_ * 0.998, 2)
        # SL: EMA200 se 0.5% neeche ya 1% - jo bada ho
        sl_by_ema = round(e200_now * 0.995, 2)
        sl_by_pct = round(cmp_ * 0.99, 2)
        sl = round(min(sl_by_ema, sl_by_pct), 2)
        if sl % 1 == 0:
            sl -= 0.30
        risk = entry_high - sl
        if risk <= 0:
            risk = round(cmp_ * 0.01, 2)
            sl = round(cmp_ - risk, 2)
        t1 = round(entry_high + risk * 1.5, 2)
        t2 = round(entry_high + risk * 2.5, 2)
        sl_pct = round(risk / entry_high * 100, 2)
        score = 82
        if dist_pct <= 0.2:
            score += 5
        if hm["signal"] == "HILEGA":
            score += 5
        if mo_rsi > 65:
            score += 5
        prob = min(95, score)
        win = min(92, 72 + (score - 82) * 1.0)
        return {"symbol": symbol, "strategy": "RET-200", "tag": "RET-200", "emoji": "↩️", "cmp": round(cmp_, 2), "entry_low": entry_low, "entry_high": entry_high, "sl": sl, "t1": t1, "t2": t2, "sl_pct": sl_pct, "risk": round(risk, 2), "score": score, "prob": prob, "win": win, "monthly_ema8": round(mo_ema8, 2), "monthly_ema20": round(mo_ema20, 2), "monthly_rsi": round(mo_rsi, 1), "weekly_close": round(wk_close, 2), "weekly_ema20": round(wk_ema20, 2), "weekly_open": round(wk_open, 2), "weekly_prev_close": round(wk_prev_close, 2), "dist_weekly_pct": round(abs(wk_close - wk_ema20) / wk_ema20 * 100, 2), "e200_now": round(e200_now, 2), "e400_now": round(e400_now, 2), "e200_prev": round(safe_float(e200_series.iloc[-2]), 2), "e400_prev": round(safe_float(e400_series.iloc[-2]), 2), "dist_15_pct": round(dist_pct, 2), "cmp_15": round(cmp_15, 2), "atr": round(atr, 2), "hm": hm}
    except Exception as e:
        print(f"RET-200 {symbol} err {e}")
        return None

# ===== STRATEGY 2 - PROXY AVWP =====
def check_proxy_avwp_strategy(symbol):
    try:
        df_d = get_data_safe(symbol, period="1y", interval="1d")
        if df_d is None or len(df_d) < 60:
            return None
        close = safe_float(df_d["Close"].iloc[-1])
        prev_close = safe_float(df_d["Close"].iloc[-2])
        high_1ago = safe_float(df_d["High"].iloc[-2])
        high_5ago = safe_float(df_d["High"].iloc[-6])
        vol = safe_float(df_d["Volume"].iloc[-1])
        vol_sma20 = safe_float(df_d["Volume"].iloc[-21:-1].mean())
        ema20 = safe_float(df_d["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = safe_float(df_d["Close"].ewm(span=50, adjust=False).mean().iloc[-1])
        rsi9 = safe_float(calc_rsi(df_d["Close"], 9).iloc[-1])
        if not (close > high_1ago):
            return None
        if not (close > high_5ago):
            return None
        if not (close > ema20):
            return None
        if not (ema20 > ema50):
            return None
        if not (vol_sma20 > 0 and vol > vol_sma20 * 1.5):
            return None
        if not (rsi9 > 55):
            return None
        if not (close > 100):
            return None
        if not (close > prev_close):
            return None
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        if mo is None or len(mo) < 15:
            return None
        mo_rsi = safe_float(calc_rsi(mo["Close"], 14).iloc[-1])
        if not (mo_rsi > 60):
            return None
        pb = 0
        try:
            ticker = yf.Ticker(symbol + ".NS")
            info = ticker.info
            pb = safe_float(info.get("priceToBook", 0))
        except Exception:
            pb = 0
        if pb > 0 and not (pb > 1):
            return None
        # HM Filter for Proxy also - 15m HILEGA check, MILEGA = SKIP
        df_15 = get_15m_df(symbol)
        hm = check_hm_15m(df_15) if df_15 is not None else {"signal": "NO_DATA", "rsi9": 0, "ema3": 0, "wma21": 0}
        if hm["signal"] == "MILEGA":
            print(f"  Proxy {symbol} SKIP - HM MILEGA")
            return None
        atr = safe_float(calc_atr(df_d).iloc[-1])
        cmp_ = close
        entry_low = round(cmp_ * 0.998, 2)
        entry_high = round(cmp_, 2)
        prev_low = safe_float(df_d["Low"].iloc[-2])
        sl_by_low = round(prev_low * 0.996, 2)
        sl_by_pct = round(cmp_ * 0.99, 2)
        sl = round(min(sl_by_low, sl_by_pct), 2)
        if sl % 1 == 0:
            sl -= 0.30
        risk = entry_high - sl
        if risk <= 0:
            risk = round(cmp_ * 0.01, 2)
            sl = round(cmp_ - risk, 2)
        t1 = round(entry_high + risk * 1.5, 2)
        t2 = round(entry_high + risk * 2.5, 2)
        sl_pct = round(risk / entry_high * 100, 2)
        vol_ratio = round(vol / vol_sma20, 2) if vol_sma20 > 0 else 0
        score = 75
        if vol_ratio > 2.0:
            score += 10
        elif vol_ratio > 1.5:
            score += 5
        if rsi9 > 65:
            score += 5
        if rsi9 > 70:
            score += 5
        if mo_rsi > 70:
            score += 5
        if hm["signal"] in ["HILEGA", "HILEGA_HOLD"]:
            score += 3
        prob = min(95, score)
        win = min(92, 65 + (score - 75) * 1.0)
        return {"symbol": symbol, "strategy": "PROXY AVWP", "tag": "PROXY AVWP", "emoji": "📈", "cmp": round(cmp_, 2), "entry_low": entry_low, "entry_high": entry_high, "sl": sl, "t1": t1, "t2": t2, "sl_pct": sl_pct, "risk": round(risk, 2), "score": score, "prob": prob, "win": win, "rsi9": round(rsi9, 1), "monthly_rsi": round(mo_rsi, 1), "ema20": round(ema20, 2), "ema50": round(ema50, 2), "vol_ratio": vol_ratio, "pb": round(pb, 2), "prev_close": round(prev_close, 2), "high_1ago": round(high_1ago, 2), "high_5ago": round(high_5ago, 2), "atr": round(atr, 2), "hm": hm}
    except Exception as e:
        print(f"Proxy AVWP {symbol} err {e}")
        return None

def get_market():
    try:
        nifty = get_data_safe("^NSEI", period="3mo", interval="1d")
        n_cmp = safe_float(nifty["Close"].iloc[-1]) if nifty is not None else 0
        n_rsi = safe_float(calc_rsi(nifty["Close"]).iloc[-1]) if nifty is not None else 50
        return {"nifty": n_cmp, "rsi": n_rsi}
    except Exception:
        return {"nifty": 0, "rsi": 50}

def send_telegram(msg):
    if not BOT_TOKEN:
        print("No BOT_TOKEN")
        return
    for cid in CHAT_IDS:
        try:
            chunks = [msg[i:i+3800] for i in range(0, len(msg), 3800)] or [msg]
            for idx, ch in enumerate(chunks):
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                resp = requests.post(url, json={"chat_id": cid, "text": ch}, timeout=20)
                print(f"Telegram to {cid} chunk {idx+1}/{len(chunks)} status {resp.status_code}")
        except Exception as e:
            print(f"Telegram send err {cid} {e}")

def record_paper(symbol, r, bot_name):
    try:
        file_exists = os.path.exists(PAPER_FILE)
        with open(PAPER_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["date", "bot", "symbol", "entry", "sl", "t1", "t2", "qty", "status", "exit_price", "pnl", "exit_reason"])
            w.writerow([datetime.now(IST).strftime("%Y-%m-%d"), bot_name, symbol, r["entry_high"], round(r["sl"] * 0.995), r["t1"], r["t2"], PAPER_QTY, "OPEN", "", "", ""])
        print(f"Paper recorded {bot_name} {symbol}")
    except Exception as e:
        print(f"Paper record err {e}")

def is_already_papered_today(symbol, bot_name):
    try:
        if not os.path.exists(PAPER_FILE):
            return False
        today = datetime.now(IST).strftime("%Y-%m-%d")
        with open(PAPER_FILE, "r") as f:
            rows = list(csv.DictReader(f))
            for r in rows:
                if r.get("date") == today and r.get("symbol") == symbol and r.get("bot") == bot_name:
                    return True
        return False
    except Exception:
        return False

def build_full_msg(market, fresh_list, ret_list, proxy_list, mode):
    now_str = datetime.now(IST).strftime("%d-%m %I:%M %p IST")
    data_src = "Upstox Live" if UPSTOX_ENABLED else "Yahoo Fallback"
    msg = f"BALA V1.2 - {now_str} - {mode}\nData: {data_src}\n"
    msg += f"Market: Nifty:{market['nifty']:.0f} RSI:{market['rsi']:.0f}\n"
    msg += f"Scan:{len(NIFTY500)} | Fresh:{len(fresh_list)} | RET-200:{len(ret_list)} | Proxy:{len(proxy_list)}\n\n"
    msg += "=== 1. BALA FRESH 🔥 + RET-200 ↩️ ===\n"
    msg += "Monthly EMA8>EMA20 + RSI>60 | Weekly Close>EMA20 <=EMA20x1.03 >Open >Prev | 15m EMA200>EMA400 + HILEGA\n\n"
    combined = fresh_list + ret_list
    combined = sorted(combined, key=lambda x: x["score"], reverse=True)
    if len(combined) == 0:
        msg += "No Fresh / RET-200 today.\n\n"
    else:
        for i, r in enumerate(combined[:5]):
            sl_gtt = round(r["sl"] * 0.995)
            hm = r.get("hm", {})
            if r["strategy"] == "RET-200":
                msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} Score:{r['score']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}% ↩️ RET-200\n"
                msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
                msg += f"   15m: CMP15 {r.get('cmp_15', r['cmp']):.0f} near EMA200 {r['e200_now']:.0f} ({r.get('dist_15_pct', 0):.2f}% upar) > EMA400 {r['e400_now']:.0f} | HM {hm.get('signal', '')} RSI9 {hm.get('rsi9', 0)}\n"
                msg += f"   Monthly: EMA8 {r['monthly_ema8']:.0f} > EMA20 {r['monthly_ema20']:.0f} RSI {r['monthly_rsi']:.0f} | Weekly Close {r['weekly_close']:.0f} > EMA20 {r['weekly_ema20']:.0f}\n"
            else:
                msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} Score:{r['score']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}% 🔥 FRESH CROSS\n"
                msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
                msg += f"   Monthly: EMA8 {r['monthly_ema8']:.0f} > EMA20 {r['monthly_ema20']:.0f} RSI {r['monthly_rsi']:.0f}\n"
                msg += f"   Weekly: Close {r['weekly_close']:.0f} > EMA20 {r['weekly_ema20']:.0f} ({r['dist_weekly_pct']:.1f}% upar) > Open {r['weekly_open']:.0f} > Prev {r['weekly_prev_close']:.0f}\n"
                msg += f"   15m: EMA200 Now {r['e200_now']:.0f} > EMA400 {r['e400_now']:.0f} | Prev EMA200 {r['e200_prev']:.0f} <= EMA400 {r['e400_prev']:.0f} = FRESH | HM {hm.get('signal', '')} RSI9 {hm.get('rsi9', 0)}\n"
            msg += f"   PAPER GTT: SL {sl_gtt:.0f} | T1 {r['t1']:.0f} 50% | T2 {r['t2']:.0f} 50% | Qty {PAPER_QTY} VIRTUAL\n\n"
    msg += "=== 2. PROXY AVWP 📈 ===\n"
    msg += "Daily Close > 1D High + 5D High + EMA20 > EMA50 + Vol 1.5x + RSI9>55 + Close>100 + Monthly RSI>60 + P/B>1 + HILEGA\n\n"
    if len(proxy_list) == 0:
        msg += "No Proxy AVWP today.\n\n"
    else:
        for i, r in enumerate(proxy_list[:5]):
            sl_gtt = round(r["sl"] * 0.995)
            hm = r.get("hm", {})
            msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} Score:{r['score']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}% 📈 PROXY AVWP\n"
            msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
            msg += f"   Daily: Close {r['cmp']:.0f} > 1D High {r['high_1ago']:.0f} > 5D High {r['high_5ago']:.0f} | EMA20 {r['ema20']:.0f} > EMA50 {r['ema50']:.0f} | RSI9 {r['rsi9']:.0f} | Vol {r['vol_ratio']:.1f}x | Monthly RSI {r['monthly_rsi']:.0f} | P/B {r['pb']:.1f} | HM {hm.get('signal', '')}\n"
            msg += f"   PAPER GTT: SL {sl_gtt:.0f} | T1 {r['t1']:.0f} 50% | T2 {r['t2']:.0f} 50% | Qty {PAPER_QTY} VIRTUAL\n\n"
    fresh_syms = set([x["symbol"] for x in fresh_list])
    ret_syms = set([x["symbol"] for x in ret_list])
    proxy_syms = set([x["symbol"] for x in proxy_list])
    overlap = (fresh_syms | ret_syms) & proxy_syms
    if overlap:
        msg += f"⭐⭐ DOUBLE CONFIRM - Dono me aaya: {', '.join(list(overlap))} - Sabse strong hai\n\n"
    msg += "Rule: Entry CMP ke paas hi lo. T1 pe 50% book, SL to Entry. Swing: Hold till T2.\nPAPER ONLY: No real GTT placed.\n"
    return msg

def build_quick_msg(market, new_list, mode):
    now_str = datetime.now(IST).strftime("%d-%m %I:%M %p IST")
    msg = f"BALA V1.2 - NEW SIGNAL - {now_str} - {mode}\n"
    msg += f"Market: Nifty:{market['nifty']:.0f} RSI:{market['rsi']:.0f}\n\n"
    for i, r in enumerate(new_list):
        sl_gtt = round(r["sl"] * 0.995)
        hm = r.get("hm", {})
        if r["strategy"] == "RET-200":
            msg += f"{i+1}. {r['symbol']} ↩️ RET-200 CMP:{r['cmp']:.0f} P:{r['prob']:.0f}% Score:{r['score']:.0f}\n"
            msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
            msg += f"   15m: CMP15 {r.get('cmp_15', r['cmp']):.0f} near EMA200 {r['e200_now']:.0f} ({r.get('dist_15_pct', 0):.2f}%) > EMA400 {r['e400_now']:.0f} | HM {hm.get('signal', '')} RSI9 {hm.get('rsi9', 0)}\n"
        else:
            msg += f"{i+1}. {r['symbol']} 🔥 FRESH CROSS CMP:{r['cmp']:.0f} P:{r['prob']:.0f}% Score:{r['score']:.0f}\n"
            msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
            msg += f"   15m: EMA200 {r['e200_now']:.0f} > EMA400 {r['e400_now']:.0f} FRESH | HM {hm.get('signal', '')} RSI9 {hm.get('rsi9', 0)}\n"
        msg += f"   PAPER GTT: SL {sl_gtt:.0f} | T1 {r['t1']:.0f} 50% | T2 {r['t2']:.0f} 50% | Qty {PAPER_QTY} VIRTUAL\n\n"
    msg += "Rule: Entry CMP ke paas hi lo. T1 pe 50% book, SL to Entry.\nPAPER ONLY\n"
    return msg

def scan_fresh_and_ret():
    fresh_list = []
    ret_list = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        def scan_one(sym):
            df_15 = get_15m_df(sym)
            if df_15 is None:
                return (None, None)
            f = check_fresh_cross_strategy(sym, df_15=df_15)
            r = None
            if f is None:
                r = check_ret200_strategy(sym, df_15=df_15)
            return (f, r)
        futs = {ex.submit(scan_one, sym): sym for sym in NIFTY500}
        for fut in futs:
            try:
                f, r = fut.result()
                if f:
                    fresh_list.append(f)
                    print(f"  ✅ FRESH PASS {f['symbol']} CMP {f['cmp']}")
                if r:
                    ret_list.append(r)
                    print(f"  ✅ RET-200 PASS {r['symbol']} CMP {r['cmp']} EMA200 {r['e200_now']} Dist {r.get('dist_15_pct', 0)}%")
            except Exception as e:
                print(f"Scan err {futs[fut]} {e}")
    fresh_list = sorted(fresh_list, key=lambda x: x["score"], reverse=True)
    ret_list = sorted(ret_list, key=lambda x: x["score"], reverse=True)
    return fresh_list, ret_list

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="auto", choices=["auto", "full", "quick"])
    args = parser.parse_args()
    now_ist = datetime.now(IST)
    print(f"BALA V1.2 Start {now_ist.strftime('%d-%m-%Y %H:%M %A IST')} Arg Mode:{args.mode}")
    try:
        # Auto mode: 9:30-9:44 = FULL, baaki time = QUICK
        if args.mode == "auto":
            hh = now_ist.hour
            mm = now_ist.minute
            if hh == 9 and mm < 45:
                mode = "full"
            elif hh == 9 and mm >= 45:
                mode = "quick"
            elif hh >= 10 and hh < 15:
                mode = "quick"
            else:
                mode = "full"
        else:
            mode = args.mode
        print(f"Resolved Mode: {mode} Time:{now_ist.strftime('%H:%M')}")
        market = get_market()
        if mode == "full":
            fresh_list, ret_list = scan_fresh_and_ret()
            print(f"Full scan Fresh {len(fresh_list)} Ret {len(ret_list)} - Now Proxy...")
            proxy_list = []
            with ThreadPoolExecutor(max_workers=10) as ex:
                futs_proxy = {ex.submit(check_proxy_avwp_strategy, sym): sym for sym in NIFTY500}
                for fut in futs_proxy:
                    try:
                        r = fut.result()
                        if r:
                            proxy_list.append(r)
                            print(f"  ✅ PROXY PASS {r['symbol']} CMP {r['cmp']} RSI9 {r['rsi9']} Vol {r['vol_ratio']}x")
                    except Exception as e:
                        print(f"Proxy scan err {futs_proxy[fut]} {e}")
            proxy_list = sorted(proxy_list, key=lambda x: x["score"], reverse=True)
            print(f"PASS: Fresh {len(fresh_list)} / Ret {len(ret_list)} / Proxy {len(proxy_list)}")
            for r in fresh_list[:5]:
                try:
                    if not is_already_papered_today(r["symbol"], "BALA_FRESH_CROSS"):
                        record_paper(r["symbol"], r, "BALA_FRESH_CROSS")
                except Exception as e:
                    print(f"Paper skip {e}")
            for r in ret_list[:5]:
                try:
                    if not is_already_papered_today(r["symbol"], "BALA_RET200"):
                        record_paper(r["symbol"], r, "BALA_RET200")
                except Exception as e:
                    print(f"Paper skip {e}")
            for r in proxy_list[:5]:
                try:
                    if not is_already_papered_today(r["symbol"], "PROXY_AVWP"):
                        record_paper(r["symbol"], r, "PROXY_AVWP")
                except Exception as e:
                    print(f"Paper skip {e}")
            msg = build_full_msg(market, fresh_list, ret_list, proxy_list, "FULL 9:30 AM")
            send_telegram(msg)
            print("BALA V1.2 FULL Done")
        else:
            # QUICK MODE - Sirf Fresh + Ret, naya signal mile toh hi Telegram
            fresh_list, ret_list = scan_fresh_and_ret()
            combined = fresh_list + ret_list
            new_list = []
            for r in combined:
                bot_name = "BALA_FRESH_CROSS" if r["strategy"] == "FRESH CROSS" else "BALA_RET200"
                if not is_already_papered_today(r["symbol"], bot_name):
                    new_list.append(r)
            print(f"QUICK: Fresh {len(fresh_list)} Ret {len(ret_list)} New {len(new_list)}")
            if len(new_list) == 0:
                print("QUICK: No new signal - Silent, no Telegram")
                return
            new_list = sorted(new_list, key=lambda x: x["score"], reverse=True)[:5]
            for r in new_list:
                try:
                    bot_name = "BALA_FRESH_CROSS" if r["strategy"] == "FRESH CROSS" else "BALA_RET200"
                    record_paper(r["symbol"], r, bot_name)
                except Exception as e:
                    print(f"Paper skip {e}")
            msg = build_quick_msg(market, new_list, "QUICK 15-MIN")
            send_telegram(msg)
            print("BALA V1.2 QUICK Done - New signal sent")
    except Exception as e:
        print(f"V1.2 CRASH {e}")
        traceback.print_exc()
        try:
            send_telegram(f"BALA V1.2 CRASHED: {e} Time: {now_ist}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
