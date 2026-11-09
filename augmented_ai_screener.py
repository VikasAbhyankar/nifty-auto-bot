"""
MASTER V19.2 ULTIMATE - TRUE BALA + NEURAL + AUGMENTED AI + DEEP LEARNING

CONTAINS ALL STRATEGIES:

1. TRUE BALA: CMP>8>20>50 + HM + RSI>55 + Vol>0.4x
2. HTF CLUSTER: Trend + HM
3. TREND: 8>20>50 EMA
4. HM: Above 200EMA
5. BTST: AVWAP > Prev 30m High + Price > AVWAP
6. ENTRY/SL/T1/T2: Entry ±0.2%, SL 50EMA/ATR, T1 5%, T2 10%
7. NIFTY S/R: S1,S2,R1,R2 Pivot
8. BANKNIFTY S/R: S1,S2,R1,R2 Pivot
9. MARKET DIRECTION: Nifty+BankNifty Trend + RSI + Breadth
10. NEURAL NETWORK: 5-input weighted scoring (w1=0.30 market, w2=0.25 trend...)
11. AUGMENTED AI: Rule + Neural + Market bias = Highest Prob
12. DEEP LEARNING DECISION: FinalRank = 50% Rule + 50% Neural + Market Boost

AUTO RUN: 9:15 AM IST Morning, 9:45 AM IST BTST, 3:00 PM IST Closing
GitHub Cron: 03:45 UTC, 04:15 UTC, 09:30 UTC
"""

import os, requests, yfinance as yf, pandas as pd, numpy as np, time
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""

NIFTY500 = [
"RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","LICI","BAJFINANCE","LT","HCLTECH","ITC","KOTAKBANK","SUNPHARMA","MARUTI","TITAN","ULTRACEMCO","AXISBANK","NTPC","ONGC","BAJAJFINSV","DMART","ADANIENT","ADANIPORTS","POWERGRID","WIPRO","TATASTEEL","HDFCLIFE","SBILIFE","ASIANPAINT","BAJAJAUTO","COALINDIA","TATAMOTORSPV","JSWSTEEL","HINDALCO","GRASIM","CIPLA","TECHM","BPCL","DIVISLAB","DRREDDY","EICHERMOT","INDUSINDBK","BRITANNIA","SHRIRAMFIN","APOLLOHOSP","TATACONSUM","VEDL",
"COFORGE","ZYDUSLIFE","PERSISTENT","HAL","PIDILITIND","HAVELLS","DABUR","BERGEPAINT","GODREJCP","COLPAL","MARICO","MUTHOOTFIN","BANDHANBNK","IDFCFIRSTB","FEDERALBNK","PNB","BANKBARODA","CANBK","UNIONBANK","IDFC","IRFC","PFC","RECLTD","HUDCO","IRCTC","RVNL","IRCON","NBCC","SJVN","NHPC","TATAPOWER","ADANIGREEN","TORNTPOWER","CESC","JSWENERGY","THERMAX","BHEL","ABB","SIEMENS","CUMMINSIND","VOLTAS","BLUESTARCO","POLYCAB","KEI","FINOLEX","RRKABEL","KAYNES","DIXON","AMBER","SYRMA","CROMPTON","BATAINDIA","RELAXO","METROBRAND","KALYANKJIL","PAGEIND","TRENT","ABFRL","NYKAA","JUBLFOOD","DEVYANI","DOMS","KAJARIACER","CERA","LTIM","LTTS","MPHASIS","KPITTECH","TATAELXSI","SONACOMS","MOTHERSON","BOSCHLTD","ASHOKLEY","TVSMOTOR","HEROMOTOCO","BALKRISIND","MRF","CEATLTD","APOLLOTYRE","ENDURANCE","MINDACORP","UNOMINDA","SUNDARMFIN","CHOLAFIN","MMFIN","CREDITACC","UJJIVANSFB","EQUITASBNK","AUBANK","BAJAJHLDNG","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDZINC","APLAPOLLO","RATNAMANI","WELCORP","TRIDENT","RAYMOND","SRFL","DEEPAKNTR","NAVINFLUOR","GUJFLUORO","BALRAMCHIN","EIDPARRY","RENUKA","AVANTIFEED","AARTIIND","ATUL","GHCL","TATACHEM","DEEPAKFERT","GNFC","GSFC","FACT","RCF","CHAMBALFERT","COROMANDEL","UPL","PIIND","RALLIS","DHANUKA","SUMICHEM","ASTRAL","SUPREMEIND","PRINCEPIPE","MOLDTEK","TIME","POLYPLEX","GARWARE","SRF","JINDALPOLY","COSMOFIRST","INOXWIND","SUZLON","BORORENEW","WEBELSOLAR","AFFLE","MAPMYINDIA","TATACOMM","BHARTIHEXA","INDIAMART","JUSTDIAL","NAUKRI","ZOMATO","PAYTM","POLICYBZR","DELHIVERY","EASEMYTRIP","SWIGGY","OFSS","BSOFT","HAPPSTMNDS","INTELLECT","MASTEK","MINDSPACE","EMBASSY","BRIGADE","PRESTIGE","PHOENIXLTD","DLF","GODREJPROP","OBEROIRLTY","SOBHA","SUNTECK","LODHA","ANANTRAJ","MAHLIFE","IBREALEST","RAILTEL","IEX","MCX","BSE","CDSL","CAMS","KFINTECH","INDIGO","TITAGARH","JWL","JUPITER","TEXRAIL","BEML","COCHINSHIP","GRSE","MAZDOCK","BDL","BEL","BHARATFORG","TANLA","WELSPUNLIV","FLUOROCHEM","GULFOILLUB","INDIANB","GPPL"
]

NIFTY500 = list(dict.fromkeys([x.strip().upper() for x in NIFTY500 if x.strip()]))
print(f"NIFTY500 deduped: {len(NIFTY500)} unique")

FAILED_FILE = "failed_symbols.txt"
AUTO_EXCLUDE = set()
try:
    if os.path.exists(FAILED_FILE):
        with open(FAILED_FILE, "r") as f:
            AUTO_EXCLUDE = set([x.strip().upper() for x in f.read().split(",") if x.strip()])
except:
    AUTO_EXCLUDE = set()

def safe_float(x):
    try:
        if isinstance(x, pd.Series): return float(x.iloc[0])
        return float(x)
    except: return 0.0

def get_data_safe(symbol):
    if symbol.upper() in AUTO_EXCLUDE: return None
    try:
        df = yf.download(symbol+".NS", period="1y", progress=False, auto_adjust=False, timeout=15)
        if df is not None and len(df) > 100 and safe_float(df['Close'].iloc[-1]) > 0:
            return df
    except: pass
    return None

# === MARKET DIRECTION + NIFTY/BANKNIFTY S1 S2 R1 R2 ===
def get_market_direction():
    try:
        def calc_pivot(df):
            prev_high = safe_float(df['High'].iloc[-2]) if len(df) > 2 else safe_float(df['High'].iloc[-1])
            prev_low = safe_float(df['Low'].iloc[-2]) if len(df) > 2 else safe_float(df['Low'].iloc[-1])
            prev_close = safe_float(df['Close'].iloc[-2]) if len(df) > 2 else safe_float(df['Close'].iloc[-1])
            pp = (prev_high + prev_low + prev_close) / 3
            r1 = 2*pp - prev_low
            s1 = 2*pp - prev_high
            r2 = pp + (prev_high - prev_low)
            s2 = pp - (prev_high - prev_low)
            r3 = prev_high + 2*(pp - prev_low)
            s3 = prev_low - 2*(prev_high - pp)
            return {"pp":pp,"r1":r1,"s1":s1,"r2":r2,"s2":s2,"r3":r3,"s3":s3,"prev_high":prev_high,"prev_low":prev_low,"prev_close":prev_close}
        
        nifty = yf.download("^NSEI", period="6mo", progress=False, auto_adjust=False, timeout=10)
        if nifty is None or len(nifty) < 50:
            nifty = yf.download("^NSEI.NS", period="6mo", progress=False, auto_adjust=False, timeout=10)
        nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
        nifty['EMA50'] = nifty['Close'].ewm(span=50).mean()
        nifty['EMA200'] = nifty['Close'].ewm(span=200).mean()
        diff = nifty['Close'].diff(); gain = diff.where(diff>0,0).rolling(14).mean(); loss = -diff.where(diff<0,0).rolling(14).mean(); rs = gain/loss; nifty['RSI'] = 100 - (100/(1+rs))
        
        nifty_cmp = safe_float(nifty['Close'].iloc[-1])
        nifty_ema20 = safe_float(nifty['EMA20'].iloc[-1])
        nifty_ema50 = safe_float(nifty['EMA50'].iloc[-1])
        nifty_ema200 = safe_float(nifty['EMA200'].iloc[-1])
        nifty_rsi = safe_float(nifty['RSI'].iloc[-1])
        nifty_pivot = calc_pivot(nifty)
        
        try:
            bn = yf.download("^NSEBANK", period="6mo", progress=False, auto_adjust=False, timeout=10)
            if bn is None or len(bn) < 50:
                bn = yf.download("^NSEBANK.NS", period="6mo", progress=False, auto_adjust=False, timeout=10)
            bn['EMA20'] = bn['Close'].ewm(span=20).mean()
            bn_cmp = safe_float(bn['Close'].iloc[-1])
            bn_ema20 = safe_float(bn['EMA20'].iloc[-1])
            bn_pivot = calc_pivot(bn)
        except:
            bn_cmp = nifty_cmp; bn_ema20 = nifty_ema20; bn_pivot = nifty_pivot
        
        above_20 = 1 if nifty_cmp > nifty_ema20 else 0
        above_50 = 1 if nifty_cmp > nifty_ema50 else 0
        above_200 = 1 if nifty_cmp > nifty_ema200 else 0
        rsi_bull = 1 if nifty_rsi > 55 else 0
        bn_bull = 1 if bn_cmp > bn_ema20 else 0
        bull_score = above_20 + above_50 + above_200 + rsi_bull + bn_bull
        
        if bull_score >= 4:
            direction = "BULLISH 🚀"; bias = 1.25; prob_boost = 15
        elif bull_score <= 1:
            direction = "BEARISH 🔴"; bias = 0.65; prob_boost = -20
        elif bull_score == 2:
            direction = "WEAK 🟡"; bias = 0.85; prob_boost = -5
        else:
            direction = "SIDEWAYS ⚪"; bias = 1.0; prob_boost = 0
        
        return {"direction":direction,"bias":bias,"prob_boost":prob_boost,"bull_score":bull_score,"nifty_cmp":nifty_cmp,"nifty_ema20":nifty_ema20,"nifty_ema50":nifty_ema50,"nifty_ema200":nifty_ema200,"nifty_rsi":nifty_rsi,"nifty_pivot":nifty_pivot,"bn_cmp":bn_cmp,"bn_ema20":bn_ema20,"bn_pivot":bn_pivot}
    except Exception as e:
        print(f"Market direction fail {e}")
        return {"direction":"SIDEWAYS ⚪","bias":1.0,"prob_boost":0,"bull_score":2,"nifty_cmp":0,"nifty_ema20":0,"nifty_ema50":0,"nifty_ema200":0,"nifty_rsi":50,"nifty_pivot":{"pp":0,"r1":0,"s1":0,"r2":0,"s2":0,"r3":0,"s3":0,"prev_high":0,"prev_low":0,"prev_close":0},"bn_cmp":0,"bn_ema20":0,"bn_pivot":{"pp":0,"r1":0,"s1":0,"r2":0,"s2":0,"r3":0,"s3":0,"prev_high":0,"prev_low":0,"prev_close":0}}

# === ANALYZE WITH ALL STRATEGIES ===
def analyze(symbol):
    df = get_data_safe(symbol)
    if df is None or len(df) < 150: return None
    try:
        df['EMA8'] = df['Close'].ewm(span=8).mean(); df['EMA20'] = df['Close'].ewm(span=20).mean(); df['EMA50'] = df['Close'].ewm(span=50).mean(); df['EMA200'] = df['Close'].ewm(span=200).mean()
        diff = df['Close'].diff(); gain = diff.where(diff>0,0).rolling(14).mean(); loss = -diff.where(diff<0,0).rolling(14).mean(); rs = gain/loss; df['RSI14'] = 100 - (100/(1+rs))
        diff9 = df['Close'].diff(); gain9 = diff9.where(diff9>0,0).rolling(9).mean(); loss9 = -diff9.where(diff9<0,0).rolling(9).mean(); rs9 = gain9/loss9; df['RSI9'] = 100 - (100/(1+rs9))
        df['VolAvg'] = df['Volume'].rolling(20).mean(); df['ATR'] = (df['High']-df['Low']).rolling(14).mean()
        cmp = safe_float(df['Close'].iloc[-1]); ema8 = safe_float(df['EMA8'].iloc[-1]); ema20 = safe_float(df['EMA20'].iloc[-1]); ema50 = safe_float(df['EMA50'].iloc[-1]); ema200 = safe_float(df['EMA200'].iloc[-1]); rsi14 = safe_float(df['RSI14'].iloc[-1]); rsi9 = safe_float(df['RSI9'].iloc[-1]); vol = safe_float(df['Volume'].iloc[-1]); vol_avg = safe_float(df['VolAvg'].iloc[-1]); vol_ratio = vol/vol_avg if vol_avg>0 else 0.5; atr = safe_float(df['ATR'].iloc[-1]); high_20 = safe_float(df['High'].rolling(20).max().iloc[-1]); low_20 = safe_float(df['Low'].rolling(20).min().iloc[-1])
        if cmp < 5 or ema8 == 0: return None
        
        trend = cmp > ema8 and ema8 > ema20 and ema20 > ema50
        hm = cmp > ema200
        rsi_ok = rsi14 > 55
        vol_ok = vol_ratio > 0.4
        
        true_bala = hm and trend and rsi_ok and vol_ok
        htf_cluster = trend and hm
        
        score = (25 if trend else 0)+(20 if hm else 0)+(15 if rsi_ok else 0)+(10 if vol_ok else 0)+(40 if true_bala else 0)+(20 if htf_cluster else 0)
        win = min(85, 50+score*0.2); prob = min(95, 60+(15 if trend else 0))
        
        entry_low = round(cmp * 0.998, 2); entry_high = round(cmp * 1.002, 2)
        sl = round(min(ema50*0.97, cmp - atr*1.5), 2)
        if (cmp - sl)/cmp > 0.04: sl = round(cmp * 0.96, 2)
        t1 = round(cmp * 1.05, 2); t2 = round(max(high_20, cmp * 1.10), 2)
        
        return {"symbol":symbol,"cmp":cmp,"rsi14":rsi14,"rsi9":rsi9,"vol_ratio":vol_ratio,"ema8":ema8,"ema20":ema20,"ema50":ema50,"ema200":ema200,"true_bala":true_bala,"htf_cluster":htf_cluster,"trend":trend,"hm":hm,"score":score,"win":win,"prob":prob,"entry_low":entry_low,"entry_high":entry_high,"sl":sl,"t1":t1,"t2":t2,"atr":atr,"high_20":high_20,"low_20":low_20}
    except Exception as e:
        print(f"{symbol} err {e}")
        return None

def check_btst_avwap(symbol):
    try:
        df_30 = yf.download(symbol+".NS", period="5d", interval="30m", progress=False, auto_adjust=False, timeout=15)
        if df_30 is None or len(df_30) < 20: return False, 0, 0, 0
        df_30['TP'] = (df_30['High'] + df_30['Low'] + df_30['Close']) / 3
        df_30['PV'] = df_30['TP'] * df_30['Volume']
        df_30['AVWAP'] = df_30['PV'].cumsum() / df_30['Volume'].cumsum()
        curr_price = safe_float(df_30['Close'].iloc[-1]); curr_avwap = safe_float(df_30['AVWAP'].iloc[-1]); prev_30m_high = safe_float(df_30['High'].iloc[-2])
        btst_ok = curr_avwap > prev_30m_high and curr_price > curr_avwap
        return btst_ok, curr_avwap, prev_30m_high, curr_price
    except:
        return False, 0, 0, 0

def neural_score(base_score, market_info, stock_data):
    market_bias = market_info['bias']; trend_strength = 1.0 if stock_data['trend'] else 0.4; hm_strength = 1.0 if stock_data['hm'] else 0.3; rsi_norm = stock_data['rsi14']/100; vol_norm = min(stock_data['vol_ratio'], 2.0)/2.0
    w1=0.30; w2=0.25; w3=0.20; w4=0.15; w5=0.10
    neural = (w1*market_bias + w2*trend_strength + w3*hm_strength + w4*rsi_norm + w5*vol_norm) * 100
    final = base_score * 0.5 + neural * 0.5 + market_info['prob_boost']
    if market_info['direction'].startswith("BEARISH") and final > 75:
        final = final * 0.7
    return max(0, final)

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"ERROR: BOT_TOKEN missing={not BOT_TOKEN} CHAT_ID missing={not CHAT_ID}"); return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 3500):
        chunk = msg[i:i+3500]
        try:
            r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=20)
            print(f"Telegram chunk {i//3500+1} status {r.status_code}")
        except Exception as e:
            print(f"Telegram failed: {e}")

def main():
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    hour = now_ist.hour
    minute = now_ist.minute
    
    scan_env = os.getenv("SCAN_TYPE", "AUTO").upper()
    
    if scan_env == "BTST":
        scan_type = "BTST"
    elif scan_env == "POST":
        scan_type = "POST"
    elif scan_env == "MARKET_DIR":
        scan_type = "MARKET_DIR"
    else:
        # AUTO based on IST time
        if hour == 15:  # 3 PM IST = BTST
            scan_type = "BTST"
        elif hour == 16 or hour == 10:  # 4 PM IST = POST (10 is UTC fallback)
            scan_type = "POST"
        else:  # 9:45 AM IST and any other morning time = Market Direction
            scan_type = "MARKET_DIR"
    
    market = get_market_direction()
    print(f"Market: {market['direction']} | Nifty:{market['nifty_cmp']:.0f} RSI:{market['nifty_rsi']:.0f} Bias:{market['bias']} BullScore:{market['bull_score']}/5")
    
    results = []; seen = {}; btst_results = []
    
    for idx, sym in enumerate(NIFTY500):
        if sym.upper() in AUTO_EXCLUDE: continue
        if idx % 50 == 0 and idx > 0:
            print(f"Progress {idx}/{len(NIFTY500)}")
            time.sleep(1.5)
        base = analyze(sym)
        if not base: continue
        
        final_rank = neural_score(base['score'], market, base)
        base['final_rank'] = final_rank
        base['market_dir'] = market['direction']
        base['prob'] = min(95, base['prob'] + market['prob_boost'])
        base['win'] = min(90, base['win'] * market['bias'])
        
        if base['symbol'] not in seen or base['final_rank'] > seen[base['symbol']]['final_rank']:
            seen[base['symbol']]=base
        
        if scan_type == "BTST":
            btst_ok, avwap_30, prev_high, curr_price = check_btst_avwap(sym)
            if btst_ok:
                base['btst_ok']=True; base['avwap_30']=avwap_30; base['prev_30m_high']=prev_high
                btst_results.append(base)
    
    results = list(seen.values())
    results = sorted(results, key=lambda x: x['final_rank'], reverse=True)
    btst_results = sorted(btst_results, key=lambda x: x['final_rank'], reverse=True)
    
    true_bala_list = sorted([x for x in results if x['true_bala']], key=lambda x: x['final_rank'], reverse=True)
    htf_list = [x for x in results if x['htf_cluster'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]]]
    htf_list = sorted(htf_list, key=lambda x: x['final_rank'], reverse=True)
    trend_list = [x for x in results if x['trend'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]+htf_list[:3]]]
    trend_list = sorted(trend_list, key=lambda x: x['final_rank'], reverse=True)
    hm_list = [x for x in results if x['hm'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]+htf_list[:3]+trend_list[:3]]]
    hm_list = sorted(hm_list, key=lambda x: x['final_rank'], reverse=True)
    
    now_str = now_ist.strftime("%d-%m %I:%M %p")
    msg = f"🚀 MASTER V19.2 NEURAL - {now_str}\n"
    msg += f"Market: {market['direction']} | Nifty:{market['nifty_cmp']:.0f} RSI:{market['nifty_rsi']:.0f} Bull:{market['bull_score']}/5\n"
    
    npv = market['nifty_pivot']; bpv = market['bn_pivot']
    msg += f"\n📊 NIFTY S/R:\nCMP:{market['nifty_cmp']:.0f} PP:{npv['pp']:.0f} R1:{npv['r1']:.0f} R2:{npv['r2']:.0f} S1:{npv['s1']:.0f} S2:{npv['s2']:.0f}\n"
    msg += f"PrevH:{npv['prev_high']:.0f} L:{npv['prev_low']:.0f} | R3:{npv['r3']:.0f} S3:{npv['s3']:.0f}\n"
    msg += f"🏦 BANKNIFTY S/R:\nCMP:{market['bn_cmp']:.0f} PP:{bpv['pp']:.0f} R1:{bpv['r1']:.0f} R2:{bpv['r2']:.0f} S1:{bpv['s1']:.0f} S2:{bpv['s2']:.0f}\n"
    msg += f"PrevH:{bpv['prev_high']:.0f} L:{bpv['prev_low']:.0f} | R3:{bpv['r3']:.0f} S3:{bpv['s3']:.0f}\n"
    
    if market['nifty_cmp'] > npv['r1']:
        msg += f"Zone: Above R1 Strong Bull 🚀\n"
    elif market['nifty_cmp'] > npv['pp']:
        msg += f"Zone: PP-R1 Bullish 🟢\n"
    elif market['nifty_cmp'] > npv['s1']:
        msg += f"Zone: S1-PP Weak 🟡\n"
    else:
        msg += f"Zone: Below S1 Bearish 🔴\n"
    
    msg += f"\nScan:{len(results)}/{len(NIFTY500)} TB:{len(true_bala_list)} HTF:{len(htf_list)} BTST:{len(btst_results)}\n\n"
    
    if scan_type == "BTST":
        msg += f"🔥 BTST (AVWAP>30m High) Best 3\n"
        if len(btst_results)>0:
            for i, r in enumerate(btst_results[:3]):
                msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} R:{r['final_rank']:.0f} P:{r['prob']:.0f}%\n"
                msg += f"Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
                msg += f"AVWAP:{r['avwap_30']:.0f}>30mH:{r['prev_30m_high']:.0f} Vol:{r['vol_ratio']:.1f}x\n\n"
        else:
            msg += f"0 BTST - Market {market['direction']} weak, no breakout!\n\n"
    
    def add_section(title, lst):
        nonlocal msg
        msg += f"{title} Best 3\n"
        for i, r in enumerate(lst[:3]):
            msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} R:{r['final_rank']:.0f} P:{r['prob']:.0f}% W:{r['win']:.0f}%\n"
            msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
        msg += f"\n"
    
    add_section("🔥 TRUE BALA", true_bala_list)
    add_section("💎 HTF CLUSTER", htf_list)
    add_section("📈 TREND", trend_list)
    add_section("🏔️ HM", hm_list)
    
    msg += f"🏆 FINAL BEST 3 HIGHEST PROB WIN\n\n"
    for i, r in enumerate(results[:3]):
        risk = ((r['cmp']-r['sl'])/r['cmp']*100); rr1 = (r['t1']-r['cmp'])/(r['cmp']-r['sl']) if r['cmp']!=r['sl'] else 0
        msg += f"{i+1}. {r['symbol']} R:{r['final_rank']:.1f} P:{r['prob']:.0f}% W:{r['win']:.0f}% {'🔥TB' if r['true_bala'] else ''}\n"
        msg += f"CMP:{r['cmp']:.0f} Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} (-{risk:.1f}%)\n"
        msg += f"T1:{r['t1']:.0f} T2:{r['t2']:.0f} RR:{rr1:.1f} RSI:{r['rsi14']:.0f} Vol:{r['vol_ratio']:.1f}x\n"
        msg += f"8E:{r['ema8']:.0f} 20E:{r['ema20']:.0f} 50E:{r['ema50']:.0f} 200E:{r['ema200']:.0f}\n\n"
    
    if market['direction'].startswith("BULLISH"):
        msg += f"💡 Deep: Market BULLISH, Go Long TB+BTST, Highest Win!\n"
    elif market['direction'].startswith("BEARISH"):
        msg += f"💡 Deep: Market BEARISH, Avoid longs, Only HM safe!\n"
    else:
        msg += f"💡 Deep: Market SIDEWAYS, Selective TB, Tight SL!\n"
    
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
