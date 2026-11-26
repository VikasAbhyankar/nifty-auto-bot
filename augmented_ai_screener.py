# MASTER V20.5 - FINAL CLEAN - BOT 1 = FINDER ONLY
# Job: Find strongest 3 Swing stocks - EARLY ENTRY + SMALL SL + HIGH PROB
# RUNS ANYTIME - No Time Guard - Manual or 9:55 AM Cron
# Data: Upstox Live (Primary) + Yahoo Fallback | Telegram: You + Prashant + Nishant
# Agents: Market, Data, TrueBala, WeeklyMTF, Risk, Messenger + BALA AVWP
# PAPER TRADING ONLY - No live order, No real GTT. Virtual SL/T1/T2 tracked in paper_trades.csv
# CHANGELOG V20.5: ONLY Bala AVWP Swing me add - Monthly Strong Trend (Mandatory) + Weekly Pullback Done (Mandatory) + 15m Fresh Crossover EMA200>EMA400 (Bonus +15, Not Mandatory)
import os, sys, time, math, json, traceback, csv
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
UPSTOX_EXPIRY = os.getenv("UPSTOX_TOKEN_EXPIRY", "2027-11-14")
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
print(f"V20.5 Telegram Targets: {CHAT_IDS} | Upstox Enabled: {UPSTOX_ENABLED}")

PAPER_FILE = "paper_trades.csv"
PAPER_QTY = 100

def swing_gtt_plan(entry_low, entry_high, sl_bot, t1_bot, t2_bot):
    try:
        sl_gtt = round(float(sl_bot) * 0.995)
        entry_avg = round((float(entry_low) + float(entry_high)) / 2)
        return {"entry": entry_avg, "sl_gtt": sl_gtt, "t1": round(float(t1_bot)), "t2": round(float(t2_bot)), "trail_sl": entry_avg}
    except Exception as e:
        print(f"swing_gtt_plan err {e}")
        return {"entry": round(float(entry_low)), "sl_gtt": round(float(sl_bot)), "t1": round(float(t1_bot)), "t2": round(float(t2_bot)), "trail_sl": round(float(entry_low))}

def record_paper_trade(bot_name, symbol, plan, qty=PAPER_QTY):
    try:
        file_exists = os.path.exists(PAPER_FILE)
        if file_exists:
            try:
                with open(PAPER_FILE, "r") as rf:
                    rows = list(csv.DictReader(rf))
                    today = datetime.now(IST).strftime("%Y-%m-%d")
                    for r in rows:
                        if r.get("date") == today and r.get("bot") == bot_name and r.get("symbol") == symbol and r.get("status") == "OPEN":
                            print(f"Paper duplicate skip {bot_name} {symbol}")
                            return False
            except Exception:
                pass
        with open(PAPER_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["date", "bot", "symbol", "entry", "sl", "t1", "t2", "qty", "status", "exit_price", "pnl", "exit_reason"])
            w.writerow([datetime.now(IST).strftime("%Y-%m-%d"), bot_name, symbol, plan["entry"], plan["sl_gtt"], plan["t1"], plan["t2"], qty, "OPEN", "", "", ""])
        print(f"Paper recorded {bot_name} {symbol} Entry {plan['entry']} SL {plan['sl_gtt']} T1 {plan['t1']} T2 {plan['t2']}")
        return True
    except Exception as e:
        print(f"record_paper_trade err {e}")
        return False

def check_paper_trades():
    updates = []
    if not os.path.exists(PAPER_FILE):
        return updates
    try:
        with open(PAPER_FILE, "r") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return updates
        changed = False
        for r in rows:
            if r.get("status") != "OPEN":
                continue
            symbol = r.get("symbol", "")
            try:
                entry = float(r.get("entry") or 0)
                sl = float(r.get("sl") or 0)
                t1 = float(r.get("t1") or 0)
                t2 = float(r.get("t2") or 0)
                qty = float(r.get("qty") or PAPER_QTY)
                if entry <= 0:
                    continue
                cmp_price = None
                try:
                    if UPSTOX_ENABLED:
                        cmp_price = upstox_live_price(to_upstox_key(symbol))
                except Exception:
                    cmp_price = None
                if not cmp_price:
                    try:
                        df = get_data_safe(symbol, period="5d", interval="1d")
                        if df is not None and len(df) > 0:
                            cmp_price = safe_float(df["Close"].iloc[-1])
                    except Exception:
                        cmp_price = None
                if not cmp_price or cmp_price <= 0:
                    continue
                pnl_pct = (cmp_price - entry) / entry * 100 if entry else 0
                if cmp_price <= sl:
                    pnl = round((cmp_price - entry) * qty, 2)
                    r["status"] = "CLOSED_SL"
                    r["exit_price"] = cmp_price
                    r["pnl"] = pnl
                    r["exit_reason"] = "SL HIT"
                    updates.append(f"{symbol} PAPER EXIT - SL HIT @ {cmp_price:.0f} P&L {pnl_pct:.1f}% Rs {pnl:.0f} (PAPER)")
                    changed = True
                elif t2 > 0 and cmp_price >= t2:
                    pnl = round((cmp_price - entry) * qty, 2)
                    r["status"] = "CLOSED_T2"
                    r["exit_price"] = cmp_price
                    r["pnl"] = pnl
                    r["exit_reason"] = "T2 HIT"
                    updates.append(f"{symbol} PAPER EXIT - T2 HIT @ {cmp_price:.0f} P&L {pnl_pct:.1f}% Rs {pnl:.0f} (PAPER)")
                    changed = True
                elif t1 > 0 and cmp_price >= t1:
                    if r.get("exit_reason") != "T1_HIT":
                        pnl_50 = round((t1 - entry) * (qty * 0.5), 2)
                        r["exit_reason"] = "T1_HIT"
                        updates.append(f"{symbol} PAPER T1 HIT @ {t1:.0f} P&L {pnl_pct:.1f}% Book 50% Rs {pnl_50:.0f} | Trail SL to Entry {entry:.0f} (PAPER)")
                        changed = True
            except Exception as e:
                print(f"check_paper {symbol} err {e}")
                continue
        if changed:
            with open(PAPER_FILE, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["date", "bot", "symbol", "entry", "sl", "t1", "t2", "qty", "status", "exit_price", "pnl", "exit_reason"])
                w.writeheader()
                w.writerows(rows)
        return updates
    except Exception as e:
        print(f"check_paper_trades err {e}")
        return updates

def upstox_headers():
    return {"Authorization": f"Bearer {UPSTOX_TOKEN}", "Accept": "application/json"}

def to_upstox_key(symbol):
    if symbol == "^NSEI":
        return "NSE_INDEX|Nifty 50"
    if symbol == "^NSEBANK":
        return "NSE_INDEX|Nifty Bank"
    if symbol == "^INDIAVIX":
        return "NSE_INDEX|India VIX"
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
            print(f"Upstox candle fail {symbol} {interval} {r.status_code} {r.text[:200]}")
            return None
        candles = r.json().get("data", {}).get("candles", [])
        return upstox_candles_to_df(candles)
    except Exception as e:
        print(f"Upstox candle err {symbol} {e}")
        return None

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
    elif interval == "30m":
        upstox_interval = "30minute"
        days_back = 5
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
        else:
            print(f"Upstox fail {symbol} {interval} -> Yahoo fallback")
    try:
        ticker = symbol if symbol.startswith("^") else symbol + ".NS"
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False, timeout=25)
        df = flatten_df(df)
        if df is None or len(df) < 50:
            return None
        return df
    except Exception:
        return None

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

def calc_pivot(df):
    try:
        prev = df.iloc[-2]
        h = safe_float(prev["High"])
        l = safe_float(prev["Low"])
        c = safe_float(prev["Close"])
        pp = (h + l + c) / 3
        r1 = 2 * pp - l
        s1 = 2 * pp - h
        r2 = pp + (h - l)
        s2 = pp - (h - l)
        r3 = h + 2 * (pp - l)
        s3 = l - 2 * (h - pp)
        return {"pp": pp, "r1": r1, "r2": r2, "s1": s1, "s2": s2, "r3": r3, "s3": s3, "prev_high": h, "prev_low": l, "prev_close": c}
    except Exception:
        return {"pp": 0, "r1": 0, "r2": 0, "s1": 0, "s2": 0, "r3": 0, "s3": 0, "prev_high": 0, "prev_low": 0, "prev_close": 0}

def make_early_entry_small_sl(cmp_, avwp, atr, swing_low, ema20):
    if avwp and avwp > 0:
        entry_low = round(min(avwp, cmp_) * 0.998, 2)
        entry_high = round(cmp_, 2)
    else:
        entry_low = round(max(ema20, cmp_ * 0.995), 2)
        entry_high = round(cmp_, 2)
    if entry_low >= entry_high:
        entry_low = round(cmp_ * 0.995, 2)
    candidates = []
    if swing_low and swing_low > 0:
        candidates.append(swing_low * 0.996)
    if atr and atr > 0:
        candidates.append(cmp_ - atr * 1.0)
    candidates.append(cmp_ * 0.992)
    sl = round(min(candidates), 2)
    if sl > cmp_ * 0.997:
        sl = round(cmp_ * 0.997, 2)
    if sl % 1 == 0:
        sl -= 0.30
    risk = entry_high - sl
    if risk <= 0:
        risk = round(cmp_ * 0.005, 2)
        sl = round(cmp_ - risk, 2)
    t1 = round(entry_high + risk * 1.5, 2)
    t2 = round(entry_high + risk * 2.5, 2)
    sl_pct = round(risk / entry_high * 100, 2)
    return {"entry_low": entry_low, "entry_high": entry_high, "sl": sl, "t1": t1, "t2": t2, "risk": round(risk, 2), "sl_pct": sl_pct}

def bala_strong_trend_fresh_cross(sym):
    try:
        mo = get_data_safe(sym, period="5y", interval="1mo")
        if mo is None or len(mo) < 20:
            return {"is_strong": False, "is_fresh": False, "reason": "No monthly data"}
        mo_close = mo["Close"]
        mo_ema8 = safe_float(mo_close.ewm(span=8, adjust=False).mean().iloc[-1])
        mo_ema20 = safe_float(mo_close.ewm(span=20, adjust=False).mean().iloc[-1])
        mo_rsi = safe_float(calc_rsi(mo_close).iloc[-1])
        monthly_ok = (mo_ema8 > mo_ema20) and (mo_rsi > 60)
        if not monthly_ok:
            return {"is_strong": False, "is_fresh": False, "reason": f"Monthly fail EMA8 {mo_ema8:.0f} EMA20 {mo_ema20:.0f} RSI {mo_rsi:.0f}", "monthly_rsi": round(mo_rsi, 1)}
        wk = get_data_safe(sym, period="2y", interval="1wk")
        if wk is None or len(wk) < 30:
            return {"is_strong": False, "is_fresh": False, "reason": "No weekly data", "monthly_rsi": round(mo_rsi, 1)}
        wk_close = safe_float(wk["Close"].iloc[-1])
        wk_open = safe_float(wk["Open"].iloc[-1])
        wk_prev_close = safe_float(wk["Close"].iloc[-2])
        wk_ema20 = safe_float(wk["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        weekly_ok = (wk_close > wk_ema20) and (wk_close <= wk_ema20 * 1.03) and (wk_close > wk_open) and (wk_close > wk_prev_close)
        if not weekly_ok:
            return {"is_strong": False, "is_fresh": False, "reason": f"Weekly fail Close {wk_close:.0f} EMA20 {wk_ema20:.0f} Open {wk_open:.0f} Prev {wk_prev_close:.0f}", "monthly_rsi": round(mo_rsi, 1)}
        df_15 = None
        try:
            ticker = sym if sym.startswith("^") else sym + ".NS"
            df_15 = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
            df_15 = flatten_df(df_15)
        except Exception:
            df_15 = None
        if df_15 is None or len(df_15) < 410:
            return {"is_strong": True, "is_fresh": False, "reason": "Strong, no 15m data for cross", "monthly_rsi": round(mo_rsi, 1)}
        e200 = df_15["Close"].ewm(span=200, adjust=False).mean()
        e400 = df_15["Close"].ewm(span=400, adjust=False).mean()
        e200_now = safe_float(e200.iloc[-1])
        e400_now = safe_float(e400.iloc[-1])
        e200_prev = safe_float(e200.iloc[-2])
        e400_prev = safe_float(e400.iloc[-2])
        fresh_cross = (e200_now > e400_now) and (e200_prev <= e400_prev)
        if fresh_cross:
            return {"is_strong": True, "is_fresh": True, "reason": f"FRESH CROSS 15m EMA200 {e200_now:.0f} > EMA400 {e400_now:.0f}", "monthly_rsi": round(mo_rsi, 1)}
        return {"is_strong": True, "is_fresh": False, "reason": "Strong, no fresh 15m cross yet", "monthly_rsi": round(mo_rsi, 1)}
    except Exception as e:
        print(f"Bala Strong Fresh {sym} err {e}")
        return {"is_strong": False, "is_fresh": False, "reason": str(e)}

def _get_swing_lows(df, left=5, right=5):
    lows = []
    try:
        for i in range(left, len(df) - right):
            window = df["Low"].iloc[i-left:i+right+1]
            if df["Low"].iloc[i] == window.min():
                lows.append((df.index[i], safe_float(df["Low"].iloc[i])))
    except Exception as e:
        print(f"swing low err {e}")
    return lows

def _anchored_vwap(df, anchor_idx):
    try:
        sub = df.iloc[anchor_idx:].copy()
        tp = (sub["High"] + sub["Low"] + sub["Close"]) / 3
        pv = (tp * sub["Volume"]).cumsum()
        vv = sub["Volume"].cumsum().replace(0, np.nan)
        return safe_float((pv / vv).iloc[-1])
    except Exception:
        return 0

def bala_avwp_swing(symbol, df_daily):
    try:
        if df_daily is None or len(df_daily) < 220:
            return None
        strong = bala_strong_trend_fresh_cross(symbol)
        if not strong["is_strong"]:
            print(f"Bala AVWP SKIP {symbol} - Strong fail: {strong['reason']}")
            return None
        is_fresh = strong["is_fresh"]
        if is_fresh:
            print(f"Bala AVWP FRESH CROSS {symbol} - {strong['reason']}")
        df = df_daily.copy()
        df["E20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["E50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["E200"] = df["Close"].ewm(span=200, adjust=False).mean()
        df["E400"] = df["Close"].ewm(span=400, adjust=False).mean()
        ema20 = safe_float(df["E20"].iloc[-1])
        ema50 = safe_float(df["E50"].iloc[-1])
        ema200 = safe_float(df["E200"].iloc[-1])
        ema400 = safe_float(df["E400"].iloc[-1])
        close = safe_float(df["Close"].iloc[-1])
        low = safe_float(df["Low"].iloc[-1])
        open_p = safe_float(df["Open"].iloc[-1])
        rsi_d = safe_float(calc_rsi(df["Close"]).iloc[-1])
        vol_ema20 = safe_float(df["Volume"].ewm(span=20, adjust=False).mean().iloc[-1])
        if not (ema20 > ema50 and close > ema200 and low <= ema20 * 1.03 and close >= ema20 * 0.97 and close <= ema20 * 1.04 and close > open_p and close > 100 and 42 <= rsi_d <= 63 and vol_ema20 > 300000):
            return None
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        if mo is None or len(mo) < 15:
            return None
        rsi_m = safe_float(calc_rsi(mo["Close"]).iloc[-1])
        if not (rsi_m > 60):
            return None
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk) < 50:
            return None
        wk["E200"] = wk["Close"].ewm(span=200, adjust=False).mean()
        wk["E400"] = wk["Close"].ewm(span=400, adjust=False).mean()
        w200 = safe_float(wk["E200"].iloc[-1])
        w400 = safe_float(wk["E400"].iloc[-1])
        if math.isnan(w400) or w400 == 0:
            wk["E100"] = wk["Close"].ewm(span=100, adjust=False).mean()
            w400 = safe_float(wk["E100"].iloc[-1])
        if not (ema200 >= ema400 and w200 >= w400):
            return None
        df_1h = get_data_safe(symbol, period="1y", interval="1h")
        if df_1h is None or len(df_1h) < 60:
            return None
        swings = _get_swing_lows(df_1h, 5, 5)
        if len(swings) < 2:
            return None
        latest_idx = df_1h.index.get_loc(swings[-1][0])
        avwp = _anchored_vwap(df_1h, latest_idx)
        if avwp <= 0:
            return None
        price = safe_float(df_1h["Close"].iloc[-1])
        swing_low = swings[-1][1]
        if abs(price - avwp) / avwp <= 0.004 and price >= avwp:
            sl = round(swing_low * 0.996, 2)
            if sl % 1 == 0:
                sl -= 0.30
            risk = price - sl
            if risk <= 0:
                return None
            return {"symbol": symbol, "avwp": round(avwp, 2), "entry_avwp": round(price, 2), "sl_avwp": sl, "swing_low": swing_low, "t1_avwp": round(price + risk * 1.5, 2), "t2_avwp": round(price + risk * 2.5, 2), "rsi_d": round(rsi_d, 1), "rsi_m": round(rsi_m, 1), "is_fresh": is_fresh, "fresh_reason": strong["reason"], "monthly_rsi": strong.get("monthly_rsi", round(rsi_m, 1))}
        return None
    except Exception as e:
        print(f"bala_avwp {symbol} err {e}")
        return None

def get_market_direction():
    try:
        nifty = get_data_safe("^NSEI", period="3mo", interval="1d")
        bn = get_data_safe("^NSEBANK", period="3mo", interval="1d")
        n_cmp = safe_float(nifty["Close"].iloc[-1]) if nifty is not None else 0
        bn_cmp = safe_float(bn["Close"].iloc[-1]) if bn is not None else 0
        n_rsi = safe_float(calc_rsi(nifty["Close"]).iloc[-1]) if nifty is not None else 50
        bull = 0
        if nifty is not None and len(nifty) > 60:
            nifty["E8"] = nifty["Close"].ewm(span=8, adjust=False).mean()
            nifty["E20"] = nifty["Close"].ewm(span=20, adjust=False).mean()
            nifty["E50"] = nifty["Close"].ewm(span=50, adjust=False).mean()
            if n_cmp > safe_float(nifty["E8"].iloc[-1]):
                bull += 1
            if n_cmp > safe_float(nifty["E20"].iloc[-1]):
                bull += 1
            if n_cmp > safe_float(nifty["E50"].iloc[-1]):
                bull += 1
            if n_rsi > 50:
                bull += 1
            if n_cmp > safe_float(nifty["Close"].iloc[-2]):
                bull += 1
        if bull >= 4:
            direction = "BULLISH"
        elif bull <= 1:
            direction = "BEARISH"
        elif bull == 2:
            direction = "WEAK"
        else:
            direction = "SIDEWAYS"
        overheated = n_rsi > 75
        return {"direction": direction, "nifty_cmp": n_cmp, "bn_cmp": bn_cmp, "nifty_rsi": n_rsi, "bull_score": bull, "overheated": overheated, "nifty_pivot": calc_pivot(nifty) if nifty is not None else calc_pivot(pd.DataFrame()), "bn_pivot": calc_pivot(bn) if bn is not None else calc_pivot(pd.DataFrame())}
    except Exception as e:
        print(f"Market err {e}")
        return {"direction": "SIDEWAYS", "nifty_cmp": 0, "bn_cmp": 0, "nifty_rsi": 50, "bull_score": 3, "overheated": False, "nifty_pivot": calc_pivot(pd.DataFrame()), "bn_pivot": calc_pivot(pd.DataFrame())}

def analyze_from_df(symbol, df):
    try:
        if df is None or len(df) < 60:
            return None
        df = df.copy()
        df["E8"] = df["Close"].ewm(span=8, adjust=False).mean()
        df["E20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["E50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["E200"] = df["Close"].ewm(span=200, adjust=False).mean()
        cmp_ = safe_float(df["Close"].iloc[-1])
        e8 = safe_float(df["E8"].iloc[-1])
        e20 = safe_float(df["E20"].iloc[-1])
        e50 = safe_float(df["E50"].iloc[-1])
        e200 = safe_float(df["E200"].iloc[-1])
        rsi = safe_float(calc_rsi(df["Close"]).iloc[-1])
        atr = safe_float(calc_atr(df).iloc[-1])
        vol_mean = safe_float(df["Volume"].iloc[-21:-1].mean())
        vol_ratio = safe_float(df["Volume"].iloc[-1] / vol_mean) if vol_mean > 0 else 0
        hm = cmp_ > e200
        true_bala = (cmp_ > e8 > e20 > e50) and hm and 55 <= rsi <= 68 and vol_ratio > 0.4
        trend = (cmp_ > e8 > e20 > e50)
        htf = trend and hm
        score = 0
        if trend:
            score += 30
        if hm:
            score += 15
        if 60 <= rsi <= 68:
            score += 15
        elif 55 <= rsi < 60:
            score += 10
        if rsi > 70:
            score -= 10
        if vol_ratio > 1.0:
            score += 15
        elif vol_ratio > 0.6:
            score += 8
        if cmp_ > e200:
            score += 10
        plan = make_early_entry_small_sl(cmp_, 0, atr, 0, e20)
        sl = plan["sl"]
        t1 = plan["t1"]
        t2 = plan["t2"]
        entry_low = plan["entry_low"]
        entry_high = plan["entry_high"]
        prob = min(95, 55 + score * 0.35)
        win = min(92, 50 + score * 0.3)
        if plan["sl_pct"] <= 0.8:
            prob = min(95, prob + 5)
            win = min(92, win + 3)
        return {"symbol": symbol, "cmp": cmp_, "ema8": e8, "ema20": e20, "ema50": e50, "ema200": e200, "rsi": rsi, "atr": atr, "vol_ratio": vol_ratio, "hm": hm, "true_bala": true_bala, "trend": trend, "htf": htf, "score": score, "final_rank": score, "prob": prob, "win": win, "sl": sl, "t1": t1, "t2": t2, "entry_low": entry_low, "entry_high": entry_high, "sl_pct": plan["sl_pct"], "bala_avwp": False, "bala_data": None, "is_fresh": False}
    except Exception as e:
        print(f"Analyze {symbol} err {e}")
        return None

def check_bala_mtf(symbol):
    try:
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk) < 30:
            return None
        wk["W8"] = wk["Close"].ewm(span=8, adjust=False).mean()
        wk["W20"] = wk["Close"].ewm(span=20, adjust=False).mean()
        wk["W50"] = wk["Close"].ewm(span=50, adjust=False).mean()
        w_cmp = safe_float(wk["Close"].iloc[-1])
        w8 = safe_float(wk["W8"].iloc[-1])
        w20 = safe_float(wk["W20"].iloc[-1])
        w50 = safe_float(wk["W50"].iloc[-1])
        tp_w = (wk["High"] + wk["Low"] + wk["Close"]) / 3
        avwap_w = (tp_w * wk["Volume"]).cumsum() / wk["Volume"].cumsum().replace(0, np.nan)
        w_avwap = safe_float(avwap_w.iloc[-1])
        prev_ath = safe_float(wk["High"].iloc[:-1].max())
        dist_to_w20 = abs(w_cmp - w20) / w20 * 100 if w20 > 0 else 99
        weekly_pullback = (w8 > w20 > w50) and (w_cmp > w20) and (dist_to_w20 <= 5.0) and (w_cmp > w_avwap)
        weekly_strong = (w8 > w20 > w50) and (w_cmp > prev_ath) and (w_cmp > w_avwap)
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        mtf_ok = False
        m8 = m20 = m50 = m100 = 0
        if mo is not None and len(mo) >= 20:
            mo["M8"] = mo["Close"].ewm(span=8, adjust=False).mean()
            mo["M20"] = mo["Close"].ewm(span=20, adjust=False).mean()
            mo["M50"] = mo["Close"].ewm(span=50, adjust=False).mean()
            mo["M100"] = mo["Close"].ewm(span=100, adjust=False).mean()
            m8 = safe_float(mo["M8"].iloc[-1])
            m20 = safe_float(mo["M20"].iloc[-1])
            m50 = safe_float(mo["M50"].iloc[-1])
            m100 = safe_float(mo["M100"].iloc[-1])
            mtf_ok = (m8 > m20 > m50 > m100)
        hr = get_data_safe(symbol, period="1y", interval="1h")
        htf_ok = False
        h200 = h400 = 0
        if hr is not None and len(hr) >= 450:
            hr["H200"] = hr["Close"].ewm(span=200, adjust=False).mean()
            hr["H400"] = hr["Close"].ewm(span=400, adjust=False).mean()
            h200 = safe_float(hr["H200"].iloc[-1])
            h400 = safe_float(hr["H400"].iloc[-1])
            htf_ok = h200 > h400
        dy = get_data_safe(symbol, period="6mo", interval="1d")
        ladder = {"e1": 0, "e2": 0, "e3": 0, "sl": 0}
        if dy is not None and len(dy) >= 60:
            low1_idx = dy["Low"].iloc[-20:].idxmin()
            low2_idx = dy["Low"].iloc[-60:-20].idxmin() if len(dy) > 60 else low1_idx
            low3_idx = dy["Low"].iloc[-120:-60].idxmin() if len(dy) > 120 else low2_idx
            def avwap_from(s_idx):
                try:
                    sub = dy.loc[s_idx:]
                    tp = (sub["High"] + sub["Low"] + sub["Close"]) / 3
                    av = (tp * sub["Volume"]).cumsum() / sub["Volume"].cumsum().replace(0, np.nan)
                    return safe_float(av.iloc[-1])
                except Exception:
                    return 0
            e1 = avwap_from(low1_idx)
            e2 = avwap_from(low2_idx)
            e3 = avwap_from(low3_idx)
            ladder = {"e1": e1, "e2": e2, "e3": e3, "sl": e1}
        bala_score = 0
        if weekly_pullback:
            bala_score += 30
        if weekly_strong:
            bala_score += 20
        if mtf_ok:
            bala_score += 20
        if htf_ok:
            bala_score += 15
        if w_cmp > prev_ath:
            bala_score += 15
        return {"weekly_pullback": weekly_pullback, "weekly_strong": weekly_strong, "mtf_ok": mtf_ok, "htf_ok": htf_ok, "w8": w8, "w20": w20, "w50": w50, "w_avwap": w_avwap, "prev_ath": prev_ath, "m8": m8, "m20": m20, "m50": m50, "m100": m100, "h200": h200, "h400": h400, "ladder": ladder, "bala_score": bala_score, "dist_to_w20": dist_to_w20}
    except Exception as e:
        print(f"Bala {symbol} err {e}")
        return None

def neural_score(score, market, r):
    base = score
    if market["direction"] == "BULLISH":
        base += 10
    elif market["direction"] == "BEARISH":
        base -= 15
    if market.get("overheated"):
        base -= 5
    return round(base, 1)

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
                if resp.status_code != 200:
                    print(f"Telegram error {cid}: {resp.text[:500]}")
        except Exception as e:
            print(f"Telegram send err {cid} {e}")

class Agent:
    def __init__(self, name):
        self.name = name
        self.result = None
        self.error = None
    def run(self, *a, **k):
        st = time.time()
        try:
            self.result = self.execute(*a, **k)
            cnt = len(self.result) if isinstance(self.result, (list, dict)) else "OK"
            print(f"✅ {self.name} Done in {time.time()-st:.1f}s - {cnt}")
        except Exception as e:
            self.error = str(e)
            self.result = [] if "List" in self.name or "Agent" in self.name else {}
            print(f"❌ {self.name} Failed: {e} - Continuing")
            traceback.print_exc()
        return self.result
    def execute(self, *a, **k):
        raise NotImplementedError

class MarketAgent(Agent):
    def __init__(self):
        super().__init__("Market Agent")
    def execute(self, *a, **k):
        return get_market_direction()

class DataAgent(Agent):
    def __init__(self):
        super().__init__("Data Agent")
    def execute(self, symbols, *a, **k):
        data = {}
        for sym in symbols:
            df = get_data_safe(sym)
            if df is not None:
                data[sym] = df
        return data

class TrueBalaAgent(Agent):
    def __init__(self):
        super().__init__("True Bala Agent")
    def execute(self, data_dict, market, *a, **k):
        out = []
        for sym, df in data_dict.items():
            base = analyze_from_df(sym, df)
            if base:
                out.append(base)
        return sorted(out, key=lambda x: x["final_rank"], reverse=True)

class WeeklyAgent(Agent):
    def __init__(self):
        super().__init__("Weekly MTF Agent")
    def execute(self, top_symbols, *a, **k):
        out = []
        for sym in top_symbols[:20]:
            bala = check_bala_mtf(sym)
            if bala and bala["weekly_pullback"]:
                out.append({"symbol": sym, "bala": bala})
        return out

class RiskAgent(Agent):
    def __init__(self):
        super().__init__("Risk Neural Agent")
    def execute(self, all_results, market, *a, **k):
        for r in all_results:
            r["final_rank"] = neural_score(r["score"], market, r)
        return sorted(all_results, key=lambda x: x["final_rank"], reverse=True)

class MessengerAgent(Agent):
    def __init__(self):
        super().__init__("Messenger Agent")
    def execute(self, market, results, bala_list, paper_updates=None, *a, **k):
        msg = build_msg(market, results, bala_list, paper_updates=paper_updates)
        send_telegram(msg)
        return {"sent": True, "len": len(msg)}

def build_msg(market, results, bala_list, paper_updates=None):
    now_ist = datetime.now(IST)
    now_str = now_ist.strftime("%d-%m %I:%M %p IST")
    data_src = "Upstox Live" if UPSTOX_ENABLED else "Yahoo Fallback"
    msg = f"MASTER V20.5 - {now_str} - DAY + SWING TRADING\nData: {data_src}\n"
    msg += f"Market: {market['direction']} | Nifty:{market['nifty_cmp']:.0f} RSI:{market['nifty_rsi']:.0f} Bull:{market['bull_score']}/5\n"
    if market.get("overheated"):
        msg += "⚠️ NIFTY OVERHEATED (RSI>75) - Chase mat karo, Pullback / AVWP Entry ka wait karo\n"
    npv = market["nifty_pivot"]
    bpv = market["bn_pivot"]
    msg += f"\nNIFTY S/R:\nCMP:{market['nifty_cmp']:.0f} PP:{npv['pp']:.0f} R1:{npv['r1']:.0f} R2:{npv['r2']:.0f} S1:{npv['s1']:.0f} S2:{npv['s2']:.0f}\nPrevH:{npv['prev_high']:.0f} L:{npv['prev_low']:.0f} | R3:{npv['r3']:.0f} S3:{npv['s3']:.0f}\n"
    msg += f"BANKNIFTY S/R:\nCMP:{market['bn_cmp']:.0f} PP:{bpv['pp']:.0f} R1:{bpv['r1']:.0f} R2:{bpv['r2']:.0f} S1:{bpv['s1']:.0f} S2:{bpv['s2']:.0f}\nPrevH:{bpv['prev_high']:.0f} L:{bpv['prev_low']:.0f} | R3:{bpv['r3']:.0f} S3:{bpv['s3']:.0f}\n"
    if market["nifty_cmp"] > npv["r1"] and npv["r1"] > 0:
        zone = "Above R1 Strong Bull"
    elif market["nifty_cmp"] > npv["pp"] and npv["pp"] > 0:
        zone = "PP-R1 Bullish"
    elif market["nifty_cmp"] > npv["s1"] and npv["s1"] > 0:
        zone = "S1-PP Weak"
    else:
        zone = "Below S1 Bearish"
    msg += f"Zone: {zone}\n"
    if paper_updates:
        msg += "\n--- PAPER TRADE UPDATES (VIRTUAL) ---\n"
        for u in paper_updates:
            msg += f"{u}\n"
        msg += "-----------------------------------\n"
    used = set()
    def pick(lst, n=3):
        picked = []
        for r in lst:
            if r["symbol"] not in used:
                picked.append(r)
                used.add(r["symbol"])
                if len(picked) >= n:
                    break
        return picked
    tb_all = [x for x in results if x["true_bala"]]
    htf_all = [x for x in results if x["htf"]]
    trend_all = [x for x in results if x["trend"]]
    hm_all = [x for x in results if x["hm"]]
    bala_all = [x for x in results if x.get("bala_avwp")]
    tb = pick(tb_all, 3)
    htf = pick(htf_all, 3)
    trend = pick(trend_all, 3)
    hm = pick(hm_all, 3)
    bala_pick = pick(bala_all, 3)
    msg += f"\nScan:{len(results)}/{len(NIFTY500)} TB:{len(tb_all)} HTF:{len(htf_all)} BALA_AVWP:{len(bala_all)} | Distinct Lists - No Repeat\n\n"
    def add(title, lst):
        nonlocal msg
        msg += f"{title} Best {len(lst) if lst else 3}\n"
        if len(lst) == 0:
            msg += "No stocks today - Filter strict hai, chase nahi karna\n\n"
            return
        for i, r in enumerate(lst[:3]):
            plan = swing_gtt_plan(r['entry_low'], r['entry_high'], r['sl'], r['t1'], r['t2'])
            tag = " 🟢 BALA AVWP" if r.get("bala_avwp") else ""
            fresh_tag = " 🔥 FRESH CROSS 15m" if r.get("is_fresh") else ""
            msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} R:{r['final_rank']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}%{tag}{fresh_tag}\n   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} (Early) SL:{r['sl']:.0f} ({r.get('sl_pct', 0):.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
            if r.get("bala_data"):
                bd = r["bala_data"]
                msg += f"   AVWP:{bd['avwp']:.0f} SL_AVWP:{bd['sl_avwp']:.0f} RSI D:{bd['rsi_d']:.0f} M:{bd['rsi_m']:.0f} Early Entry\n"
                if bd.get("is_fresh"):
                    msg += f"   Monthly EMA8>EMA20 RSI {bd.get('monthly_rsi', bd['rsi_m']):.0f} | Weekly Close>EMA20 Green | 15m EMA200>EMA400 Fresh Cross\n"
            msg += f"   PAPER GTT: SL GTT {plan['sl_gtt']:.0f} (100%) | T1 GTT {plan['t1']:.0f} (50%) | T2 GTT {plan['t2']:.0f} (50%) | Trail SL->{plan['trail_sl']:.0f} after T1\n"
        msg += "\n"
    add("DAY - TRUE BALA", tb)
    add("DAY - HTF CLUSTER", htf)
    add("SWING - TREND", trend)
    add("SWING - HM", hm)
    if bala_pick:
        add("SWING - BALA AVWP EARLY ENTRY", bala_pick)
    msg += "FINAL BEST 3 FOR TODAY - PAPER TRADE ONLY - SWING\n\n"
    for i, r in enumerate(results[:3]):
        plan = swing_gtt_plan(r["entry_low"], r["entry_high"], r["sl"], r["t1"], r["t2"])
        tag = " 🟢 BALA AVWP" if r.get("bala_avwp") else ""
        fresh_tag = " 🔥 FRESH CROSS 15m" if r.get("is_fresh") else ""
        msg += f"{i+1}. {r['symbol']}{tag}{fresh_tag} CMP:{r['cmp']:.0f} Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r.get('sl_pct', 0):.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
        msg += f"   PAPER: Buy Avg {plan['entry']:.0f} | SL GTT {plan['sl_gtt']:.0f} | T1 {plan['t1']:.0f} 50% | T2 {plan['t2']:.0f} 50% | Qty {PAPER_QTY} VIRTUAL - No real order | Risk/Trade: Rs {abs(plan['entry']-plan['sl_gtt'])*PAPER_QTY:.0f}\n"
    msg += "\nRule: Entry AVWP ke paas hi lo. SL max 0.8% hai. T1 pe 50% book, SL to Entry. Day Trade: Use T1 only. Swing: Hold till T2.\nPAPER ONLY: No real GTT placed in Upstox. Bot tracks SL/T1/T2 virtually in paper_trades.csv\n"
    msg += "\nBot 1 = Finder only. For real trade with Rs 5000 risk + exact qty, follow Bot 2 at 9:45 AM."
    return msg

def main():
    now_ist = datetime.now(IST)
    print(f"V20.5 Start {now_ist.strftime('%d-%m-%Y %H:%M %A IST')} Scan:DAY_SWING Chats:{CHAT_IDS}")
    try:
        paper_updates = []
        try:
            paper_updates = check_paper_trades()
            if paper_updates:
                print(f"Paper updates: {paper_updates}")
        except Exception as e:
            print(f"Paper check skip {e}")
        market = MarketAgent().run()
        data_dict = DataAgent().run(NIFTY500)
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_tb = ex.submit(TrueBalaAgent().run, data_dict, market)
            f_weekly = ex.submit(WeeklyAgent().run, list(data_dict.keys()))
            tb_list = f_tb.result()
            bala_list = f_weekly.result()
        print("V20.5 Bala AVWP check Top 30 - With Strong Trend + Fresh Cross...")
        for r in tb_list[:30]:
            try:
                df_d = data_dict.get(r["symbol"])
                bd = bala_avwp_swing(r["symbol"], df_d)
                if bd:
                    r["bala_avwp"] = True
                    r["bala_data"] = bd
                    r["is_fresh"] = bd.get("is_fresh", False)
                    r["score"] += 12
                    r["prob"] = min(95, r["prob"] + 12)
                    r["win"] = min(92, r["win"] + 5)
                    if bd.get("is_fresh"):
                        r["score"] += 15
                        r["prob"] = min(95, r["prob"] + 10)
                        r["win"] = min(92, r["win"] + 5)
                    plan = make_early_entry_small_sl(r["cmp"], bd["avwp"], r.get("atr", 0), bd["swing_low"], r["ema20"])
                    r["entry_low"] = plan["entry_low"]
                    r["entry_high"] = plan["entry_high"]
                    r["sl"] = plan["sl"]
                    r["t1"] = plan["t1"]
                    r["t2"] = plan["t2"]
                    r["sl_pct"] = plan["sl_pct"]
                    print(f"  BALA AVWP PASS {r['symbol']} AVWP {bd['avwp']} SL {bd['sl_avwp']} Entry {plan['entry_low']}-{plan['entry_high']} Fresh={bd.get('is_fresh')}")
            except Exception as e:
                print(f"Bala AVWP skip {r.get('symbol')} {e}")
        final_list = RiskAgent().run(tb_list, market)
        for r in final_list:
            if r.get("bala_avwp"):
                r["final_rank"] = round(r["final_rank"] + 12, 1)
                if r.get("is_fresh"):
                    r["final_rank"] = round(r["final_rank"] + 15, 1)
        final_list = sorted(final_list, key=lambda x: x["final_rank"], reverse=True)
        if len(final_list) > 0:
            for r in final_list[:3]:
                try:
                    plan = swing_gtt_plan(r["entry_low"], r["entry_high"], r["sl"], r["t1"], r["t2"])
                    record_paper_trade("BOT1_SWING", r["symbol"], plan, qty=PAPER_QTY)
                except Exception as e:
                    print(f"Paper record skip {r.get('symbol')} {e}")
        MessengerAgent().run(market, final_list, bala_list, paper_updates=paper_updates)
        print("V20.5 All Agents Done")
    except Exception as e:
        print(f"V20.5 CRASH {e}")
        traceback.print_exc()
        try:
            send_telegram(f"MASTER V20.5 CRASHED but handled: {e} Time: {now_ist}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
