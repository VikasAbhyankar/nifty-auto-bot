# MASTER V20.5 - FINAL CLEAN - BOT 1 = FINDER ONLY
# Job: Find strongest 3 Swing stocks - EARLY ENTRY + SMALL SL + HIGH PROB
# RUNS ANYTIME - No Time Guard - Manual or 9:55 AM Cron
# Data: Upstox Live (Primary) + Yahoo Fallback | Telegram: You + Prashant + Nishant
# Agents: Market, Data, TrueBala, WeeklyMTF, Risk, Messenger + BALA AVWP
# PAPER TRADING ONLY - No live order, No real GTT. Virtual SL/T1/T2 tracked in paper_trades.csv
# CHANGELOG V20.5: ONLY Bala AVWP Swing me add - Monthly Strong Trend (Mandatory) + Weekly Pullback Done (Mandatory) + 15m Fresh Crossover EMA200>EMA400 (Bonus +15, Not Mandatory) - Bot 2 / Adaptive untouched
import os, sys, time, math, json, traceback, csv
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor

# ===== IST - LOCKED =====
try:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
except:
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

# ===== PAPER TRADING - BOT1 SWING ONLY =====
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

# ===== UPSTOX CLIENT =====
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
    except:
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

# ===== NIFTY500 - DEDUPED =====
_NIFTY500_RAW = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","TATAMOTORS","ETERNAL","CDSL","PNB","KALYANKJIL","TITAN","ITC","LT","AXISBANK","KOTAKBANK","BAJFINANCE","HINDUNILVR","MARUTI","TATASTEEL","JSWSTEEL","ULTRACEMCO","ADANIENT","ADANIPORTS","POWERGRID","NTPC","ONGC","COALINDIA","BPCL","IOC","HDFCLIFE","SBILIFE","ICICIPRULI","BAJAJFINSV","M&M","EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","APOLLOHOSP","DIVISLAB","SUNPHARMA","CIPLA","DRREDDY","GRASIM","HINDALCO","VEDL","TATAPOWER","ADANIGREEN","ADANIPOWER","IRFC","RVNL","HAL","BEL","BDL","MAZAGON","COCHINSHIP","BHEL","NHPC","SJVN","PFC","RECLTD","HUDCO","NBCC","IRCON","RAILTEL","TITAGARH","JUPITERWAGONS","GENSOL","SUZLON","IREDA","TATATECH","TATAELXSI","KPITTECH","PERSISTENT","COFORGE","LTIM","MPHASIS","TECHM","WIPRO","HCLTECH","ZOMATO","PAYTM","NYKAA","POLICYBZR","DELHIVERY","DMART","TRENT","VBL","NESTLEIND","BRITANNIA","DABUR","MARICO","GODREJCP","COLPAL","TATACONSUM","HATSUN","PAGEIND","RELAXO","CAMPUS","BATAINDIA","METROBRANDS","KAYNES","DIXON","AMBER","PGEL","SYRMA","CROMPTON","HAVELLS","POLYCAB","KEI","FINOLEX","SUPREMEIND","ASTRAL","APLAPOLLO","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDCOPPER","MOIL","GMDCLTD","MANGLMCEM","RAMCOCEM","SHREECEM","ACC","AMBUJACEM","DALMIABHA","JKCEMENT","STAR","ORIENTCEM","HEIDELBERG","PRISMJOHN","SAGAR","INDIACEM","CERA","KAJARIA","SOMANY","HSIL","RAJESHEXPO","THANGAMAYIL","KALYAN","PNBGILTS","PNBHOUSING","CANFIN","LICHSGFIN","GICHSGFIN","REPCOHOME","AAVAS","HOMEFIRST","APTUS","MANAPPURAM","MUTHOOTFIN","IIFL","CHOLAFIN","SHRIRAMFIN","MAHABANK","CENTRALBK","UCOBANK","BANKOFMAHA","INDIANB","IOB","PSB","J&KBANK","KARURVYSYA","FEDERALBNK","RBLBANK","IDFCFIRSTB","YESBANK","BANDHANBNK","CSBBANK","DCBBANK","CUB","TMB","KARNATAKA","SOUTHBANK","INDUSINDBK","AUBANK","EQUITASBNK","UJJIVANSFB","CAPITALSFB","ESAFSFB","JANA","SURYO","SPANDANA","CREDITACC","ARMAN","FIVE-STAR","SATIN","UJJIVAN","MFIN","MASFIN","PAISALO","CAPRIGLOBAL","PIRAMAL","JMFINANCIL","MOTILALOFS","ANGELONE","BSE","MCX","CDSL","NSDL","CAMS","KFINTECH","ANANDRATHI","NUVAMA","360ONE","IIFLSEC","GEOJIT","SMC","SHAREINDIA","EMKAY","MONARCH","PRUDENT","DPABHUSHAN","MANINFRA","OBEROIRLTY","PRESTIGE","BRIGADE","SOBHA","GODREJPROP","DLF","PHOENIXLTD","MACPOWER","ASHIANA","SUNTERRA","SHRIRAMPROP","PURAVANKARA","ARVIND","VARDHMAN","TRIDENT","WELSPUNLIV","INDOCOUNT","GOKEX","RAYMOND","KPRMILL","PAGE","WELCORP","JINDALSAW","RATNAMANI","MAHSEAMLES","APL","JTLIND","MANAKSIA","JINDALPOLY","HIMATSEIDE","BANSWRAS","RSWM","DONEAR","ALOKINDS","FILATEX","VTL","SUTLEJTEX","NITINSPIN","GHCL","GHCLTEXTIL","VARDHMANACR","INDORAMA","JBF","GARDENREACH","GRSE","PARADEEP","FACT","RCF","GSFC","GNFC","DEEPAKFERT","ZUARI","MANGCHE","CHAMBLFERT","NFL","KRIBHCO","COROMANDEL","UPL","PIIND","SUMICHEM","ATUL","AARTIIND","DEEPAKNTR","FINEORG","ALKYLAMINE","BALAMINES","VINATIORGA","CLEAN","ROSSARI","NEOGEN","ANURAS","GOPAL","LAXMI","TATACHEM","DCMSHRIRAM","TATAGU","IGL","MGL","GUJGASLTD","PETRONET","GAIL","OIL","MRPL","CHENNPETRO","NRL","BALMERLAWRIE","GULFOILLUB","CASTROLIND","SAVITA","APARINDS","TIDEWATER","PANAMAPET","GANDHARTU","MORGANITE","CARBORUNIV","GRINDWELL","WENDT","MMTC","STCINDIA","KIOCL","FERRO","IMFA","SHAKTI","JSL","JINDALSTEL"]
NIFTY500 = list(dict.fromkeys(_NIFTY500_RAW))

def safe_float(x, default=0.0):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except:
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
            except:
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
    except:
        return None

def calc_rsi(series, period=14):
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss.replace(0, 1e-9))
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series([50] * len(series), index=series.index)

def calc_atr(df, n=14):
    try:
        h = df["High"]
        l = df["Low"]
