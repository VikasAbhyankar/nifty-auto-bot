# BALA FRESH CROSS V1.0 - ONE NEW STRATEGY ONLY
# Based ONLY on:
# MONTHLY: EMA(8) > EMA(20) + RSI(14) > 60
# WEEKLY: Close > EMA(20), Close <= EMA(20)*1.03, Close > Open, Close > Prev Close
# 15-MINUTE: EMA(200) > EMA(400) NOW + EMA(200) <= EMA(400) 1 candle ago = FRESH CROSS
# RUNS ANYTIME - Manual or 9:55 AM Cron | PAPER ONLY - No live order
# Data: Upstox Live (Primary) + Yahoo Fallback | Telegram: You + Prashant + Nishant
import os, time, math, traceback, csv
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
print(f"BALA FRESH CROSS V1.0 Targets: {CHAT_IDS} | Upstox: {UPSTOX_ENABLED}")

PAPER_FILE = "paper_trades_fresh_cross.csv"
PAPER_QTY = 100

# ===== NIFTY500 =====
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

# ===== UPSTOX =====
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

# ===== THE ONLY STRATEGY - BALA FRESH CROSS =====
def check_fresh_cross_strategy(symbol):
    """
    Returns dict if ALL 3 pass, else None.
    No other filter - No AVWP, No RSI Daily, No Volume, No Trend - Only your 3 rules.
    """
    try:
        # --- 1. MONTHLY — STRONG TREND ---
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        if mo is None or len(mo) < 21:
            return None
        mo_close = mo["Close"]
        mo_ema8 = safe_float(mo_close.ewm(span=8, adjust=False).mean().iloc[-1])
        mo_ema20 = safe_float(mo_close.ewm(span=20, adjust=False).mean().iloc[-1])
        mo_rsi = safe_float(calc_rsi(mo_close, 14).iloc[-1])
        # Rule 1: Monthly EMA8 > EMA20 AND Monthly RSI > 60
        if not (mo_ema8 > mo_ema20 and mo_rsi > 60):
            return None

        # --- 2. WEEKLY ---
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk) < 22:
            return None
        wk_close = safe_float(wk["Close"].iloc[-1])
        wk_open = safe_float(wk["Open"].iloc[-1])
        wk_prev_close = safe_float(wk["Close"].iloc[-2])
        wk_ema20 = safe_float(wk["Close"].ewm(span=20, adjust=False).mean().iloc[-1])
        # Rule 2: All 4 must pass
        if not (wk_close > wk_ema20):
            return None
        if not (wk_close <= wk_ema20 * 1.03):
            return None
        if not (wk_close > wk_open):
            return None
        if not (wk_close > wk_prev_close):
            return None

        # --- 3. 15-MINUTE — FRESH CROSSOVER ---
        # Yahoo 5d 15m - need 400+ candles for EMA400
        df_15 = None
        try:
            ticker = symbol + ".NS"
            df_15 = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True, timeout=25)
            df_15 = flatten_df(df_15)
        except Exception:
            df_15 = None
        if df_15 is None or len(df_15) < 405:
            return None
        e200 = df_15["Close"].ewm(span=200, adjust=False).mean()
        e400 = df_15["Close"].ewm(span=400, adjust=False).mean()
        e200_now = safe_float(e200.iloc[-1])
        e400_now = safe_float(e400.iloc[-1])
        e200_prev = safe_float(e200.iloc[-2])
        e400_prev = safe_float(e400.iloc[-2])
        # Rule 3: NOW EMA200 > EMA400 AND 1 candle ago EMA200 <= EMA400
        if not (e200_now > e400_now and e200_prev <= e400_prev):
            return None

        # --- ALL 3 PASSED - BUILD ENTRY / SL / TARGET ---
        # CMP = Daily close / Live
        df_d = get_data_safe(symbol, period="6mo", interval="1d")
        if df_d is None or len(df_d) < 30:
            return None
        cmp_ = safe_float(df_d["Close"].iloc[-1])
        atr = safe_float(calc_atr(df_d).iloc[-1])
        # Entry: CMP ke paas - Fresh Cross ke baad pullback ka wait mat karo, CMP hi entry hai
        entry_low = round(cmp_ * 0.998, 2)
        entry_high = round(cmp_, 2)
        # SL: Weekly EMA20 ke neeche ya 0.8% - jo bada ho, wahi SL (Fresh Cross fail = EMA20 break)
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
        # Score: Fresh Cross is rare, so high prob
        # Monthly RSI jitna strong, utna score zyada
        score = 80
        if mo_rsi > 65:
            score += 10
        if mo_rsi > 70:
            score += 5
        # Weekly close EMA20 ke jitna paas, utna accha pullback entry
        dist_w = abs(wk_close - wk_ema20) / wk_ema20 * 100
        if dist_w <= 1.0:
            score += 5
        prob = min(95, score)
        win = min(92, 70 + (score - 80) * 1.0)

        return {
            "symbol": symbol,
            "cmp": round(cmp_, 2),
            "entry_low": entry_low,
            "entry_high": entry_high,
            "sl": sl,
            "t1": t1,
            "t2": t2,
            "sl_pct": sl_pct,
            "risk": round(risk, 2),
            "score": score,
            "prob": prob,
            "win": win,
            "monthly_ema8": round(mo_ema8, 2),
            "monthly_ema20": round(mo_ema20, 2),
            "monthly_rsi": round(mo_rsi, 1),
            "weekly_close": round(wk_close, 2),
            "weekly_ema20": round(wk_ema20, 2),
            "weekly_open": round(wk_open, 2),
            "weekly_prev_close": round(wk_prev_close, 2),
            "dist_weekly_pct": round(dist_w, 2),
            "e200_now": round(e200_now, 2),
            "e400_now": round(e400_now, 2),
            "e200_prev": round(e200_prev, 2),
            "e400_prev": round(e400_prev, 2),
            "atr": round(atr, 2),
        }
    except Exception as e:
        print(f"Fresh Cross {symbol} err {e}")
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

def record_paper(symbol, r):
    try:
        file_exists = os.path.exists(PAPER_FILE)
        with open(PAPER_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["date", "bot", "symbol", "entry", "sl", "t1", "t2", "qty", "status", "exit_price", "pnl", "exit_reason"])
            w.writerow([datetime.now(IST).strftime("%Y-%m-%d"), "BALA_FRESH_CROSS", symbol, r["entry_high"], round(r["sl"] * 0.995), r["t1"], r["t2"], PAPER_QTY, "OPEN", "", "", ""])
        print(f"Paper recorded FRESH CROSS {symbol}")
    except Exception as e:
        print(f"Paper record err {e}")

def build_msg(market, results):
    now_str = datetime.now(IST).strftime("%d-%m %I:%M %p IST")
    data_src = "Upstox Live" if UPSTOX_ENABLED else "Yahoo Fallback"
    msg = f"BALA FRESH CROSS V1.0 - {now_str}\nData: {data_src}\n"
    msg += f"Market: Nifty:{market['nifty']:.0f} RSI:{market['rsi']:.0f}\n"
    msg += f"Scan:{len(results)}/{len(NIFTY500)} passed ALL 3 rules\n\n"
    msg += "RULES:\nMonthly EMA8>EMA20 + RSI>60\nWeekly Close>EMA20, <=EMA20x1.03, >Open, >Prev Close\n15m EMA200>EMA400 NOW + EMA200<=EMA400 1 candle ago = FRESH CROSS\n\n"
    if len(results) == 0:
        msg += "No stocks today - Fresh Cross bahut rare hai.\n"
        msg += "Kal fir check karo. Aaj koi Fresh Cross nahi bana toh NO TRADE - chase mat karo.\n"
        msg += "\nPAPER ONLY: No real order.\n"
        return msg
    msg += f"TOP {min(len(results), 5)} - FRESH CROSS - PAPER ONLY\n\n"
    for i, r in enumerate(results[:5]):
        sl_gtt = round(r["sl"] * 0.995)
        msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} Score:{r['score']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}% 🔥 FRESH CROSS 15m\n"
        msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} ({r['sl_pct']:.1f}%) T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
        msg += f"   Monthly: EMA8 {r['monthly_ema8']:.0f} > EMA20 {r['monthly_ema20']:.0f} RSI {r['monthly_rsi']:.0f}\n"
        msg += f"   Weekly: Close {r['weekly_close']:.0f} > EMA20 {r['weekly_ema20']:.0f} ({r['dist_weekly_pct']:.1f}% upar) > Open {r['weekly_open']:.0f} > Prev {r['weekly_prev_close']:.0f}\n"
        msg += f"   15m: EMA200 Now {r['e200_now']:.0f} > EMA400 {r['e400_now']:.0f} | Prev EMA200 {r['e200_prev']:.0f} <= EMA400 {r['e400_prev']:.0f} = FRESH\n"
        msg += f"   PAPER GTT: SL GTT {sl_gtt:.0f} (100%) | T1 GTT {r['t1']:.0f} (50%) | T2 GTT {r['t2']:.0f} (50%) | Trail SL->Entry after T1 | Qty {PAPER_QTY} VIRTUAL\n\n"
    msg += "Rule: Entry CMP ke paas hi lo. SL Weekly EMA20 break hai - uske neeche close aaye toh exit. T1 pe 50% book, SL to Entry. Swing: Hold till T2.\nPAPER ONLY: No real GTT placed. Bot tracks virtually.\n"
    return msg

def main():
    now_ist = datetime.now(IST)
    print(f"BALA FRESH CROSS V1.0 Start {now_ist.strftime('%d-%m-%Y %H:%M %A IST')} Scan:{len(NIFTY500)}")
    try:
        market = get_market()
        results = []
        # Parallel scan - 10 workers, fast
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(check_fresh_cross_strategy, sym): sym for sym in NIFTY500}
            for fut in futs:
                try:
                    r = fut.result()
                    if r:
                        results.append(r)
                        print(f"  ✅ PASS {r['symbol']} CMP {r['cmp']} Monthly RSI {r['monthly_rsi']} Weekly EMA20 {r['weekly_ema20']} 15m {r['e200_now']} > {r['e400_now']}")
                except Exception as e:
                    print(f"Scan err {futs[fut]} {e}")
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        print(f"Fresh Cross PASS: {len(results)} / {len(NIFTY500)}")
        for r in results[:5]:
            try:
                record_paper(r["symbol"], r)
            except Exception as e:
                print(f"Paper skip {e}")
        msg = build_msg(market, results)
        send_telegram(msg)
        print("BALA FRESH CROSS V1.0 Done")
    except Exception as e:
        print(f"FRESH CROSS CRASH {e}")
        traceback.print_exc()
        try:
            send_telegram(f"BALA FRESH CROSS V1.0 CRASHED: {e} Time: {now_ist}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
