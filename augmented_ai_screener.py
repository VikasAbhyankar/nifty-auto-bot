# MASTER V20.1 - MULTI-AGENT TRUE BALA + BALA MTF + AVWAP LADDER
# Data: Upstox Live (Primary) + Yahoo Fallback | Telegram: You + Prashant + Nishant
# Timings IST: 9:00 MARKET_DIR, 9:45 DAY_SWING, 15:00 BTST, 16:00 PRO
# Agents: Market, Data, TrueBala, WeeklyMTF, BTST, Risk, Messenger
import os, sys, time, math, json, traceback
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

# 3 Chats - All must have pressed START on bot
# 5239892901 = Prashant, 9000971028 = Nishant, 3rd = You from Secret
CHAT_IDS = []
# Order: You first, then Prashant, Nishant - But all get same msg same run
_raw_ids = []
if CHAT_FROM_ENV:
    for x in str(CHAT_FROM_ENV).split(","):
        x = x.strip()
        if x and x not in _raw_ids: _raw_ids.append(x)
for fid in ["5239892901", "9000971028"]:
    if fid not in _raw_ids: _raw_ids.append(fid)
CHAT_IDS = _raw_ids
print(f"V20.1 Telegram Targets: {CHAT_IDS} | Upstox Enabled: {UPSTOX_ENABLED}")

# ===== UPSTOX CLIENT =====
def upstox_headers():
    return {"Authorization": f"Bearer {UPSTOX_TOKEN}", "Accept": "application/json"}
def to_upstox_key(symbol):
    # NIFTY 500 symbol like RELIANCE -> NSE_EQ|RELIANCE, ^NSEI handled separately
    if symbol == "^NSEI": return "NSE_INDEX|Nifty 50"
    if symbol == "^NSEBANK": return "NSE_INDEX|Nifty Bank"
    if symbol == "^INDIAVIX": return "NSE_INDEX|India VIX"
    base = symbol.replace(".NS","").replace("-","_").upper()
    return f"NSE_EQ|{base}"
def upstox_live_price(instrument_key):
    if not UPSTOX_ENABLED: return None
    try:
        r = requests.get(f"{UPSTOX_BASE}/market-quote/quotes", headers=upstox_headers(),
                         params={"instrument_key": instrument_key}, timeout=10)
        if r.status_code != 200: return None
        d = r.json().get("data", {}).get(instrument_key, {})
        lp = d.get("last_price") or d.get("ltp")
        return float(lp) if lp else None
    except: return None
def upstox_candles_to_df(candles):
    # Upstox: [timestamp, open, high, low, close, volume, oi]
    if not candles: return None
    try:
        df = pd.DataFrame(candles, columns=["ts","Open","High","Low","Close","Volume","OI"][:len(candles[0])] if len(candles[0])>5 else ["ts","Open","High","Low","Close","Volume"])
        # If 7 cols, keep first 6
        df = df[["ts","Open","High","Low","Close","Volume"]]
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts").sort_index()
        for c in ["Open","High","Low","Close","Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        print(f"Upstox df convert err {e}"); return None
def get_upstox_candles(symbol, interval="day", days_back=365):
    # interval: day, week, month, 30minute, 1hour, 15minute
    if not UPSTOX_ENABLED: return None
    try:
        ikey = to_upstox_key(symbol)
        # Historical candles: /market-candle/historical/{ikey}/{interval}/{to}/{from}
        # For simplicity use intraday for intraday, historical for daily+
        now = datetime.now(IST)
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if interval in ["30minute","1hour","15minute"]:
            url = f"{UPSTOX_BASE}/market-candle/intraday/{ikey}/{interval}"
            r = requests.get(url, headers=upstox_headers(), timeout=20)
        else:
            # Upstox v3 historical: /market-candle/historical/{ikey}/{interval}/{to_date}/{from_date}
            url = f"{UPSTOX_BASE}/market-candle/historical/{ikey}/{interval}/{to_date}/{from_date}"
            r = requests.get(url, headers=upstox_headers(), timeout=25)
        if r.status_code != 200:
            print(f"Upstox candle fail {symbol} {interval} {r.status_code} {r.text[:200]}")
            return None
        candles = r.json().get("data", {}).get("candles", [])
        df = upstox_candles_to_df(candles)
        return df
    except Exception as e:
        print(f"Upstox candle err {symbol} {e}"); return None

# NIFTY 500 - Keep your full list - Short list below, REPLACE with your V19.3 full list
NIFTY500 = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","TATAMOTORS","ETERNAL","CDSL","PNB","KALYANKJIL","TITAN","ITC","LT","AXISBANK","KOTAKBANK","BAJFINANCE","HINDUNILVR","MARUTI","TATASTEEL","JSWSTEEL","ULTRACEMCO","ADANIENT","ADANIPORTS","POWERGRID","NTPC","ONGC","COALINDIA","BPCL","IOC","HDFCLIFE","SBILIFE","ICICIPRULI","BAJAJFINSV","M&M","EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","APOLLOHOSP","DIVISLAB","SUNPHARMA","CIPLA","DRREDDY","GRASIM","HINDALCO","VEDL","TATAPOWER","ADANIGREEN","ADANIPOWER","IRFC","RVNL","HAL","BEL","BDL","MAZAGON","COCHINSHIP","BHEL","NHPC","SJVN","PFC","RECLTD","HUDCO","NBCC","IRCON","RAILTEL","TITAGARH","JUPITERWAGONS","GENSOL","SUZLON","IREDA","TATATECH","TATAELXSI","KPITTECH","PERSISTENT","COFORGE","LTIM","MPHASIS","TECHM","WIPRO","HCLTECH","ZOMATO","PAYTM","NYKAA","POLICYBZR","DELHIVERY","DMART","TRENT","VBL","NESTLEIND","BRITANNIA","DABUR","MARICO","GODREJCP","COLPAL","TATACONSUM","HATSUN","PAGEIND","RELAXO","CAMPUS","BATAINDIA","METROBRANDS","KAYNES","DIXON","AMBER","PGEL","SYRMA","CROMPTON","HAVELLS","POLYCAB","KEI","FINOLEX","SUPREMEIND","ASTRAL","APLAPOLLO","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDCOPPER","MOIL","GMDCLTD","MANGLMCEM","RAMCOCEM","SHREECEM","ACC","AMBUJACEM","DALMIABHA","JKCEMENT","STAR","ORIENTCEM","HEIDELBERG","PRISMJOHN","SAGAR","INDIACEM","CERA","KAJARIA","SOMANY","HSIL","RAJESHEXPO","THANGAMAYIL","KALYAN","PNBGILTS","PNBHOUSING","CANFIN","LICHSGFIN","GICHSGFIN","REPCOHOME","AAVAS","HOMEFIRST","APTUS","MANAPPURAM","MUTHOOTFIN","IIFL","CHOLAFIN","SHRIRAMFIN","MAHABANK","CENTRALBK","UCOBANK","BANKOFMAHA","INDIANB","IOB","PSB","J&KBANK","KARURVYSYA","FEDERALBNK","RBLBANK","IDFCFIRSTB","YESBANK","BANDHANBNK","CSBBANK","DCBBANK","CUB","TMB","KARNATAKA","SOUTHBANK","INDUSINDBK","AUBANK","EQUITASBNK","UJJIVANSFB","CAPITALSFB","ESAFSFB","JANA","SURYO","SPANDANA","CREDITACC","ARMAN","FIVE-STAR","SATIN","UJJIVAN","MFIN","MASFIN","PAISALO","CAPRIGLOBAL","PIRAMAL","JMFINANCIL","MOTILALOFS","ANGELONE","BSE","MCX","CDSL","NSDL","CAMS","KFINTECH","ANANDRATHI","NUVAMA","360ONE","IIFLSEC","GEOJIT","SMC","SHAREINDIA","EMKAY","MONARCH","PRUDENT","DPABHUSHAN","MANINFRA","OBEROIRLTY","PRESTIGE","BRIGADE","SOBHA","GODREJPROP","DLF","PHOENIXLTD","MACPOWER","ASHIANA","SUNTERRA","SHRIRAMPROP","PURAVANKARA","ARVIND","VARDHMAN","TRIDENT","WELSPUNLIV","INDOCOUNT","GOKEX","RAYMOND","KPRMILL","PAGE","WELCORP","JINDALSAW","RATNAMANI","MAHSEAMLES","APL","JTLIND","MANAKSIA","JINDALPOLY","HIMATSEIDE","BANSWRAS","RSWM","DONEAR","ALOKINDS","FILATEX","VTL","SUTLEJTEX","NITINSPIN","GHCL","GHCLTEXTIL","VARDHMANACR","INDORAMA","JBF","GARDENREACH","GRSE","PARADEEP","FACT","RCF","GSFC","GNFC","DEEPAKFERT","ZUARI","MANGCHE","CHAMBLFERT","NFL","KRIBHCO","COROMANDEL","UPL","PIIND","SUMICHEM","ATUL","AARTIIND","DEEPAKNTR","FINEORG","ALKYLAMINE","BALAMINES","VINATIORGA","CLEAN","ROSSARI","NEOGEN","ANURAS","GOPAL","LAXMI","TATACHEM","DCMSHRIRAM","TATAGU","IGL","MGL","GUJGASLTD","PETRONET","GAIL","OIL","MRPL","CHENNPETRO","NRL","BALMERLAWRIE","GULFOILLUB","CASTROLIND","SAVITA","APARINDS","TIDEWATER","PANAMAPET","GANDHARTU","MORGANITE","CARBORUNIV","GRINDWELL","WENDT","MMTC","STCINDIA","KIOCL","FERRO","IMFA","SHAKTI","JSL","JINDALSTEL"]

def safe_float(x, default=0.0):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return default
        return float(x)
    except: return default

def flatten_df(df):
    if df is None or len(df)==0: return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).capitalize() if str(c).lower() in ["open","high","low","close","volume"] else str(c) for c in df.columns]
    cols = {}
    for c in df.columns:
        lc = str(c).lower()
        if lc=="open": cols[c]="Open"
        elif lc=="high": cols[c]="High"
        elif lc=="low": cols[c]="Low"
        elif lc=="close": cols[c]="Close"
        elif lc=="volume": cols[c]="Volume"
    df = df.rename(columns=cols)
    return df

def get_data_safe(symbol, period="1y", interval="1d"):
    # V20.1: Try Upstox first, Yahoo fallback
    # Map interval
    upstox_interval = "day"
    days_back = 365
    if interval == "1d": upstox_interval="day"; days_back=365
    elif interval == "1wk": upstox_interval="week"; days_back=730
    elif interval == "1mo": upstox_interval="month"; days_back=1825
    elif interval == "1h": upstox_interval="1hour"; days_back=30
    elif interval == "30m": upstox_interval="30minute"; days_back=5
    # Try Upstox
    if UPSTOX_ENABLED:
        df = get_upstox_candles(symbol, upstox_interval, days_back)
        if df is not None and len(df)>=50:
            # Override last close with live price for exact entry at 9:45 / 15:00
            try:
                live = upstox_live_price(to_upstox_key(symbol))
                if live and live>0:
                    # Only override Close of last candle, keep OHLC history for EMA
                    df.loc[df.index[-1], "Close"] = live
                    print(f"Upstox Live {symbol}: {live}")
            except: pass
            return flatten_df(df)
        else:
            print(f"Upstox fail {symbol} {interval} -> Yahoo fallback")
    # Yahoo fallback
    try:
        if symbol.startswith("^"): ticker = symbol
        else: ticker = symbol + ".NS"
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False, timeout=25)
        df = flatten_df(df)
        if df is None or len(df)<50: return None
        return df
    except: return None

def calc_pivot(df):
    try:
        prev = df.iloc[-2]; curr = df.iloc[-1]
        h = safe_float(prev["High"]); l = safe_float(prev["Low"]); c = safe_float(prev["Close"])
        pp = (h+l+c)/3; r1 = 2*pp - l; s1 = 2*pp - h; r2 = pp + (h-l); s2 = pp - (h-l); r3 = h + 2*(pp-l); s3 = l - 2*(h-pp)
        return {"pp":pp,"r1":r1,"r2":r2,"s1":s1,"s2":s2,"r3":r3,"s3":s3,"prev_high":h,"prev_low":l,"prev_close":c}
    except: return {"pp":0,"r1":0,"r2":0,"s1":0,"s2":0,"r3":0,"s3":0,"prev_high":0,"prev_low":0,"prev_close":0}

def get_market_direction():
    try:
        nifty = get_data_safe("^NSEI", period="3mo", interval="1d")
        bn = get_data_safe("^NSEBANK", period="3mo", interval="1d")
        n_cmp = safe_float(nifty["Close"].iloc[-1]) if nifty is not None else 0
        bn_cmp = safe_float(bn["Close"].iloc[-1]) if bn is not None else 0
        def rsi(series, period=14):
            delta = series.diff(); gain = delta.where(delta>0,0).rolling(period).mean(); loss = (-delta.where(delta<0,0)).rolling(period).mean()
            rs = gain/(loss.replace(0,1e-9)); return 100 - (100/(1+rs))
        n_rsi = safe_float(rsi(nifty["Close"]).iloc[-1]) if nifty is not None else 50
        bull=0
        if nifty is not None and len(nifty)>60:
            nifty["E8"]=nifty["Close"].ewm(span=8,adjust=False).mean(); nifty["E20"]=nifty["Close"].ewm(span=20,adjust=False).mean(); nifty["E50"]=nifty["Close"].ewm(span=50,adjust=False).mean()
            if n_cmp>safe_float(nifty["E8"].iloc[-1]): bull+=1
            if n_cmp>safe_float(nifty["E20"].iloc[-1]): bull+=1
            if n_cmp>safe_float(nifty["E50"].iloc[-1]): bull+=1
            if n_rsi>50: bull+=1
            if n_cmp>safe_float(nifty["Close"].iloc[-2]): bull+=1
        direction = "BULLISH" if bull>=4 else "BEARISH" if bull<=1 else "WEAK" if bull==2 else "SIDEWAYS"
        return {"direction":direction,"nifty_cmp":n_cmp,"bn_cmp":bn_cmp,"nifty_rsi":n_rsi,"bull_score":bull,"nifty_pivot":calc_pivot(nifty) if nifty is not None else calc_pivot(pd.DataFrame()),"bn_pivot":calc_pivot(bn) if bn is not None else calc_pivot(pd.DataFrame())}
    except Exception as e:
        print(f"Market err {e}"); return {"direction":"SIDEWAYS","nifty_cmp":0,"bn_cmp":0,"nifty_rsi":50,"bull_score":3,"nifty_pivot":calc_pivot(pd.DataFrame()),"bn_pivot":calc_pivot(pd.DataFrame())}

def analyze_from_df(symbol, df):
    try:
        if df is None or len(df)<60: return None
        df = df.copy()
        df["E8"]=df["Close"].ewm(span=8,adjust=False).mean(); df["E20"]=df["Close"].ewm(span=20,adjust=False).mean(); df["E50"]=df["Close"].ewm(span=50,adjust=False).mean(); df["E200"]=df["Close"].ewm(span=200,adjust=False).mean()
        cmp_ = safe_float(df["Close"].iloc[-1]); e8=safe_float(df["E8"].iloc[-1]); e20=safe_float(df["E20"].iloc[-1]); e50=safe_float(df["E50"].iloc[-1]); e200=safe_float(df["E200"].iloc[-1])
        delta=df["Close"].diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean(); rs=gain/(loss.replace(0,1e-9)); rsi=safe_float((100-(100/(1+rs))).iloc[-1])
        vol_ratio = safe_float(df["Volume"].iloc[-1]/df["Volume"].iloc[-21:-1].mean()) if safe_float(df["Volume"].iloc[-21:-1].mean())>0 else 0
        hm = cmp_>e200
        true_bala = (cmp_>e8>e20>e50) and hm and rsi>55 and vol_ratio>0.4
        trend = (cmp_>e8>e20>e50)
        htf = trend and hm
        score=0
        if trend: score+=30
        if hm: score+=15
        if rsi>60: score+=15
        elif rsi>55: score+=10
        if vol_ratio>1.0: score+=15
        elif vol_ratio>0.6: score+=8
        if cmp_>e200: score+=10
        sl = round(e50*0.99,2) if e50>0 else round(cmp_*0.97,2)
        risk = cmp_-sl
        t1 = round(cmp_+risk*2,2) if risk>0 else cmp_
        t2 = round(cmp_+risk*4,2) if risk>0 else cmp_
        entry_low = round(e20,2); entry_high = round(cmp_,2)
        prob = min(95, 55 + score*0.35); win = min(92, 50 + score*0.3)
        return {"symbol":symbol,"cmp":cmp_,"ema8":e8,"ema20":e20,"ema50":e50,"ema200":e200,"rsi":rsi,"vol_ratio":vol_ratio,"hm":hm,"true_bala":true_bala,"trend":trend,"htf":htf,"score":score,"final_rank":score,"prob":prob,"win":win,"sl":sl,"t1":t1,"t2":t2,"entry_low":entry_low,"entry_high":entry_high}
    except Exception as e:
        print(f"Analyze {symbol} err {e}"); return None

def check_btst_avwap(symbol):
    try:
        # V20.1: Upstox 30m first
        df = None
        if UPSTOX_ENABLED:
            df = get_upstox_candles(symbol, "30minute", 5)
        if df is None:
            df = yf.download(symbol+".NS", period="5d", interval="30m", progress=False, auto_adjust=False, timeout=20)
            df = flatten_df(df)
        if df is None or len(df)<10: return False,0,0,0
        tp=(df["High"]+df["Low"]+df["Close"])/3
        avwap=(tp*df["Volume"]).cumsum()/df["Volume"].cumsum().replace(0,np.nan)
        av = safe_float(avwap.iloc[-1]); prev_30_high = safe_float(df["High"].iloc[-2]); price=safe_float(df["Close"].iloc[-1])
        ok = (av>prev_30_high) and (price>av)
        return ok,av,prev_30_high,price
    except: return False,0,0,0

def check_bala_mtf(symbol):
    try:
        wk = get_data_safe(symbol, period="2y", interval="1wk")
        if wk is None or len(wk)<30: return None
        wk["W8"]=wk["Close"].ewm(span=8,adjust=False).mean(); wk["W20"]=wk["Close"].ewm(span=20,adjust=False).mean(); wk["W50"]=wk["Close"].ewm(span=50,adjust=False).mean()
        w_cmp=safe_float(wk["Close"].iloc[-1]); w8=safe_float(wk["W8"].iloc[-1]); w20=safe_float(wk["W20"].iloc[-1]); w50=safe_float(wk["W50"].iloc[-1])
        tp_w=(wk["High"]+wk["Low"]+wk["Close"])/3; avwap_w=(tp_w*wk["Volume"]).cumsum()/wk["Volume"].cumsum().replace(0,np.nan); w_avwap=safe_float(avwap_w.iloc[-1])
        prev_ath=safe_float(wk["High"].iloc[:-1].max())
        dist_to_w20=abs(w_cmp-w20)/w20*100 if w20>0 else 99
        weekly_pullback=(w8>w20>w50) and (w_cmp>w20) and (dist_to_w20<=5.0) and (w_cmp>w_avwap)
        weekly_strong=(w8>w20>w50) and (w_cmp>prev_ath) and (w_cmp>w_avwap)
        mo = get_data_safe(symbol, period="5y", interval="1mo")
        mtf_ok=False; m8=m20=m50=m100=0
        if mo is not None and len(mo)>=20:
            mo["M8"]=mo["Close"].ewm(span=8,adjust=False).mean(); mo["M20"]=mo["Close"].ewm(span=20,adjust=False).mean(); mo["M50"]=mo["Close"].ewm(span=50,adjust=False).mean(); mo["M100"]=mo["Close"].ewm(span=100,adjust=False).mean()
            m8=safe_float(mo["M8"].iloc[-1]); m20=safe_float(mo["M20"].iloc[-1]); m50=safe_float(mo["M50"].iloc[-1]); m100=safe_float(mo["M100"].iloc[-1]); mtf_ok=(m8>m20>m50>m100)
        hr = get_data_safe(symbol, period="1y", interval="1h")
        htf_ok=False; h200=h400=0
        if hr is not None and len(hr)>=450:
            hr["H200"]=hr["Close"].ewm(span=200,adjust=False).mean(); hr["H400"]=hr["Close"].ewm(span=400,adjust=False).mean(); h200=safe_float(hr["H200"].iloc[-1]); h400=safe_float(hr["H400"].iloc[-1]); htf_ok=h200>h400
        dy = get_data_safe(symbol, period="6mo", interval="1d")
        ladder={"e1":0,"e2":0,"e3":0,"sl":0}
        if dy is not None and len(dy)>=60:
            low1_idx=dy["Low"].iloc[-20:].idxmin(); low2_idx=dy["Low"].iloc[-60:-20].idxmin() if len(dy)>60 else low1_idx; low3_idx=dy["Low"].iloc[-120:-60].idxmin() if len(dy)>120 else low2_idx
            def avwap_from(s_idx):
                try:
                    sub=dy.loc[s_idx:]; tp=(sub["High"]+sub["Low"]+sub["Close"])/3; av=(tp*sub["Volume"]).cumsum()/sub["Volume"].cumsum().replace(0,np.nan); return safe_float(av.iloc[-1])
                except: return 0
            e1=avwap_from(low1_idx); e2=avwap_from(low2_idx); e3=avwap_from(low3_idx); ladder={"e1":e1,"e2":e2,"e3":e3,"sl":e1}
        bala_score=0
        if weekly_pullback: bala_score+=30
        if weekly_strong: bala_score+=20
        if mtf_ok: bala_score+=20
        if htf_ok: bala_score+=15
        if w_cmp>prev_ath: bala_score+=15
        return {"weekly_pullback":weekly_pullback,"weekly_strong":weekly_strong,"mtf_ok":mtf_ok,"htf_ok":htf_ok,"w8":w8,"w20":w20,"w50":w50,"w_avwap":w_avwap,"prev_ath":prev_ath,"m8":m8,"m20":m20,"m50":m50,"m100":m100,"h200":h200,"h400":h400,"ladder":ladder,"bala_score":bala_score,"dist_to_w20":dist_to_w20}
    except Exception as e:
        print(f"Bala {symbol} err {e}"); return None

def neural_score(score, market, r):
    base=score
    if market["direction"]=="BULLISH": base+=10
    elif market["direction"]=="BEARISH": base-=15
    return round(base,1)

def send_telegram(msg):
    if not BOT_TOKEN: print("No BOT_TOKEN"); return
    # Send to all 3 simultaneously - Loop, no auth check
    for cid in CHAT_IDS:
        try:
            chunks=[msg[i:i+3800] for i in range(0,len(msg),3800)] or [msg]
            for idx, ch in enumerate(chunks):
                url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                resp=requests.post(url, json={"chat_id":cid,"text":ch}, timeout=20)
                print(f"Telegram to {cid} chunk {idx+1}/{len(chunks)} status {resp.status_code}")
                if resp.status_code!=200:
                    print(f"Telegram error {cid}: {resp.text[:500]} - Did user press START?")
                    # 403 = User has not pressed START / blocked bot
        except Exception as e: print(f"Telegram send err {cid} {e}")

class Agent:
    def __init__(self, name): self.name=name; self.result=None; self.error=None
    def run(self, *a, **k):
        st=time.time()
        try:
            self.result=self.execute(*a, **k)
            cnt=len(self.result) if isinstance(self.result,(list,dict)) else "OK"
            print(f"✅ {self.name} Done in {time.time()-st:.1f}s - {cnt}")
        except Exception as e:
            self.error=str(e); self.result=[] if "List" in self.name or "Agent" in self.name else {}
            print(f"❌ {self.name} Failed: {e} - Continuing")
            traceback.print_exc()
        return self.result
    def execute(self, *a, **k): raise NotImplementedError

class MarketAgent(Agent):
    def __init__(self): super().__init__("Market Agent")
    def execute(self, *a, **k): return get_market_direction()
class DataAgent(Agent):
    def __init__(self): super().__init__("Data Agent")
    def execute(self, symbols, *a, **k):
        data={}
        for sym in symbols:
            df=get_data_safe(sym)
            if df is not None: data[sym]=df
        return data
class TrueBalaAgent(Agent):
    def __init__(self): super().__init__("True Bala Agent")
    def execute(self, data_dict, market, *a, **k):
        out=[]
        for sym, df in data_dict.items():
            base=analyze_from_df(sym, df)
            if base: out.append(base)
        return sorted(out, key=lambda x: x["final_rank"], reverse=True)
class WeeklyAgent(Agent):
    def __init__(self): super().__init__("Weekly MTF Agent")
    def execute(self, top_symbols, *a, **k):
        out=[]
        for sym in top_symbols[:20]:
            bala=check_bala_mtf(sym)
            if bala and bala["weekly_pullback"]: out.append({"symbol":sym,"bala":bala})
        return out
class BTSTAgent(Agent):
    def __init__(self): super().__init__("BTST Agent")
    def execute(self, symbols, *a, **k):
        out=[]
        for sym in symbols:
            ok,av,ph,pr=check_btst_avwap(sym)
            if ok: out.append({"symbol":sym,"avwap":av,"prev_high":ph,"cmp":pr})
        return out
class RiskAgent(Agent):
    def __init__(self): super().__init__("Risk Neural Agent")
    def execute(self, all_results, market, *a, **k):
        for r in all_results:
            r["final_rank"]=neural_score(r["score"], market, r)
            risk=r["cmp"]-r["sl"]
            if risk>0: r["t2"]=round(r["cmp"]+risk*4,2)
        return sorted(all_results, key=lambda x: x["final_rank"], reverse=True)
class MessengerAgent(Agent):
    def __init__(self): super().__init__("Messenger Agent")
    def execute(self, scan_type, market, results, btst_list, bala_list, *a, **k):
        msg=build_msg(scan_type, market, results, btst_list, bala_list)
        send_telegram(msg)
        return {"sent":True,"len":len(msg)}

def build_msg(scan_type, market, results, btst_list, bala_list):
    now_ist=datetime.now(IST); now_str=now_ist.strftime("%d-%m %I:%M %p IST")
    title={"MARKET_DIR":"MARKET DIRECTION - PRE OPEN","DAY_SWING":"DAY + SWING TRADING","BTST":"BTST FOR TOMORROW","PRO":"DAY OVERALL + TOMORROW DIRECTION"}.get(scan_type,"MARKET DIRECTION")
    data_src = "Upstox Live" if UPSTOX_ENABLED else "Yahoo Fallback"
    msg=f"MASTER V20.1 - {now_str} - {title}\nData: {data_src}\n"
    msg+=f"Market: {market['direction']} | Nifty:{market['nifty_cmp']:.0f} RSI:{market['nifty_rsi']:.0f} Bull:{market['bull_score']}/5\n"
    npv=market["nifty_pivot"]; bpv=market["bn_pivot"]
    msg+=f"\nNIFTY S/R:\nCMP:{market['nifty_cmp']:.0f} PP:{npv['pp']:.0f} R1:{npv['r1']:.0f} R2:{npv['r2']:.0f} S1:{npv['s1']:.0f} S2:{npv['s2']:.0f}\nPrevH:{npv['prev_high']:.0f} L:{npv['prev_low']:.0f} | R3:{npv['r3']:.0f} S3:{npv['s3']:.0f}\n"
    msg+=f"BANKNIFTY S/R:\nCMP:{market['bn_cmp']:.0f} PP:{bpv['pp']:.0f} R1:{bpv['r1']:.0f} R2:{bpv['r2']:.0f} S1:{bpv['s1']:.0f} S2:{bpv['s2']:.0f}\nPrevH:{bpv['prev_high']:.0f} L:{bpv['prev_low']:.0f} | R3:{bpv['r3']:.0f} S3:{bpv['s3']:.0f}\n"
    if market["nifty_cmp"]>npv["r1"] and npv["r1"]>0: zone="Above R1 Strong Bull"
    elif market["nifty_cmp"]>npv["pp"] and npv["pp"]>0: zone="PP-R1 Bullish"
    elif market["nifty_cmp"]>npv["s1"] and npv["s1"]>0: zone="S1-PP Weak"
    else: zone="Below S1 Bearish"
    msg+=f"Zone: {zone}\n"
    if scan_type=="MARKET_DIR":
        msg+=f"\nScan:{len(results)}/{len(NIFTY500)}\n\nPRE-OPEN PLAN:\n"
        if market["direction"]=="BULLISH": msg+="Buy on dip near PP / S1. Avoid chasing above R1.\nTarget R1 -> R2. SL below PP.\n"
        elif market["direction"]=="BEARISH": msg+="Avoid longs. Sell on rise near PP / R1.\nTarget S1 -> S2. SL above PP.\n"
        else: msg+="No trade zone. Wait for breakout above R1 or breakdown below S1.\nOnly True Bala with tight SL.\n"
        msg+="\n9:45 AM will come Day + Swing list. Wait for it."
        return msg
    if scan_type=="DAY_SWING":
        tb=[x for x in results if x["true_bala"]]; htf=[x for x in results if x["htf"]]; trend=[x for x in results if x["trend"]]; hm=[x for x in results if x["hm"]]
        msg+=f"\nScan:{len(results)}/{len(NIFTY500)} TB:{len(tb)} HTF:{len(htf)}\n\n"
        def add(title, lst):
            nonlocal msg
            msg+=f"{title} Best 3\n"
            if len(lst)==0: msg+="No stocks today\n\n"; return
            for i,r in enumerate(lst[:3]): msg+=f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} R:{r['final_rank']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}%\n   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
            msg+="\n"
        add("DAY - TRUE BALA", tb); add("DAY - HTF CLUSTER", htf); add("SWING - TREND", trend); add("SWING - HM", hm)
        msg+="FINAL BEST 3 FOR TODAY\n\n"
        for i,r in enumerate(results[:3]): msg+=f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
        msg+="\nDay Trade: Use T1 only. Swing: Hold till T2, SL = 50EMA."
        return msg
    if scan_type=="BTST":
        msg+=f"\nScan:{len(results)}/{len(NIFTY500)} BTST:{len(btst_list)}\n\nBTST (AVWAP>30m High) Best 3 - Buy Today, Sell Tomorrow Morning\n"
        if len(btst_list)>0:
            for i,r in enumerate(btst_list[:3]): msg+=f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} AVWAP:{r['avwap']:.0f}>30mH:{r['prev_high']:.0f}\n"
        else: msg+="0 BTST today - Market weak, No breakout. Do NOT force BTST.\n\n"
        if len(bala_list)>0:
            msg+="\nBALA MTF LADDER - Positional\n"
            res_map={x["symbol"]:x for x in results}
            for i,b in enumerate(bala_list[:3]):
                lad=b["bala"]["ladder"]; sym=b["symbol"]; rr=res_map.get(sym,{"cmp":0,"sl":0})
                msg+=f"{i+1}. {sym} CMP:{rr['cmp']:.0f} E1 25% @ {lad['e1']:.0f} | E2 40% @ {lad['e2']:.0f} | E3 35% @ {lad['e3']:.0f} SL:{rr['sl']:.0f}\n"
                msg+=f"   W20:{b['bala']['w20']:.0f} MTF:{'YES' if b['bala']['mtf_ok'] else 'NO'} HTF H200>H400:{'YES' if b['bala']['htf_ok'] else 'NO'} T2 1:4:{rr.get('t2',0):.0f}\n"
        msg+="\nBTST Rule: Buy in last 15 min, SL = Today Low. Exit tomorrow 9:30-10:00 AM."
        return msg
    msg+=f"\nTODAY OVERALL:\nNifty Closed at {market['nifty_cmp']:.0f} vs PP {npv['pp']:.0f} - {zone}\nBull Score: {market['bull_score']}/5 | RSI: {market['nifty_rsi']:.0f}\n"
    if market["nifty_cmp"]>npv["pp"]: msg+="Today: Buyers won. Closed above PP = Positive.\n"
    else: msg+="Today: Sellers won. Closed below PP = Negative.\n"
    msg+=f"\nTOMORROW DIRECTION: {market['direction']}\n"
    if market["direction"]=="BULLISH": msg+="Tomorrow: BULLISH. Plan: Buy dip near PP/S1. Levels: S1 as Support, R1 as Target.\nAvoid shorting.\n"
    elif market["direction"]=="BEARISH": msg+="Tomorrow: BEARISH. Plan: Sell rise near PP/R1. Levels: R1 as Resistance, S1 as Target.\nAvoid longs, only HM safe.\n"
    elif market["direction"]=="WEAK": msg+="Tomorrow: WEAK. Plan: No fresh longs. Wait for Nifty to close above 20EMA.\n"
    else: msg+="Tomorrow: SIDEWAYS. Plan: Buy near S1, Sell near R1. No breakout trade.\n"
    msg+=f"\nTomorrow Key Levels: R1:{npv['r1']:.0f} PP:{npv['pp']:.0f} S1:{npv['s1']:.0f}\nIf Nifty opens above R1 = Strong. If opens below S1 = Weak.\n"
    msg+=f"\nScan:{len(results)}/{len(NIFTY500)} - Full list came at 9:45 AM, see that msg."
    return msg

def resolve_scan_type(now_ist):
    raw=os.getenv("SCAN_TYPE","AUTO").strip().upper()
    if raw in ["BTST","MARKET_DIR","DAY_SWING","PRO"]: return raw
    if raw in ["DAY","SWING"]: return "DAY_SWING"
    # IST logic - now_ist is already IST
    h=now_ist.hour; m=now_ist.minute
    total = h*60+m
    if 530 <= total < 570: return "MARKET_DIR"  # 8:50-9:30 -> 9:00 run
    if 570 <= total < 890: return "DAY_SWING"   # 9:30-14:50 -> 9:45 run
    if 890 <= total < 950: return "BTST"        # 14:50-15:50 -> 15:00 run
    if total >= 950: return "PRO"               # 15:50+ -> 16:00 run
    return "MARKET_DIR"

def main():
    now_ist=datetime.now(IST); scan_type=resolve_scan_type(now_ist)
    print(f"V20.1 Start {now_ist.strftime('%d-%m-%Y %H:%M IST')} Scan:{scan_type} Chats:{CHAT_IDS}")
    # Weekend check - IST
    if now_ist.weekday()>4:
        print("Weekend IST - No Trade"); return
    try:
        market=MarketAgent().run()
        if scan_type=="MARKET_DIR":
            MessengerAgent().run(scan_type, market, [], [], [])
            print("V20.1 Done - Market Only"); return
        data_dict=DataAgent().run(NIFTY500)
        with ThreadPoolExecutor(max_workers=3) as ex:
            if scan_type=="BTST":
                f_btst=ex.submit(BTSTAgent().run, list(data_dict.keys()))
                f_weekly=ex.submit(WeeklyAgent().run, list(data_dict.keys()))
                f_tb=ex.submit(TrueBalaAgent().run, data_dict, market)
                tb_list=f_tb.result(); btst_list=f_btst.result(); bala_list=f_weekly.result()
            else:
                f_tb=ex.submit(TrueBalaAgent().run, data_dict, market)
                f_btst=ex.submit(BTSTAgent().run, list(data_dict.keys()))
                f_weekly=ex.submit(WeeklyAgent().run, list(data_dict.keys()))
                tb_list=f_tb.result(); btst_list=f_btst.result(); bala_list=f_weekly.result()
        bala_map={b["symbol"]:b["bala"] for b in bala_list}
        for r in tb_list:
            if r["symbol"] in bala_map:
                lad=bala_map[r["symbol"]]["ladder"]
                if lad["e1"]>0: r["sl"]=round(min(lad["e1"]*0.995, r["ema50"]),2)
        final_list=RiskAgent().run(tb_list, market)
        MessengerAgent().run(scan_type, market, final_list, btst_list, bala_list)
        print("V20.1 All Agents Done")
    except Exception as e:
        print(f"V20.1 CRASH {e}"); traceback.print_exc()
        try: send_telegram(f"MASTER V20.1 CRASHED but handled: {e} Time: {now_ist}")
        except: pass

if __name__=="__main__":
    main()
