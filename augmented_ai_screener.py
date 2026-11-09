import os, requests, yfinance as yf, pandas as pd, numpy as np, time
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""

NIFTY500 = [
"RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","LICI","BAJFINANCE","LT","HCLTECH","ITC","KOTAKBANK","SUNPHARMA","MARUTI","TITAN","ULTRACEMCO","AXISBANK","NTPC","ONGC","BAJAJFINSV","DMART","ADANIENT","ADANIPORTS","POWERGRID","WIPRO","TATASTEEL","HDFCLIFE","SBILIFE","ASIANPAINT","BAJAJAUTO","COALINDIA","TATAMOTORSPV","JSWSTEEL","HINDALCO","GRASIM","CIPLA","TECHM","BPCL","DIVISLAB","DRREDDY","EICHERMOT","INDUSINDBK","BRITANNIA","SHRIRAMFIN","APOLLOHOSP","TATACONSUM","VEDL",
"TANLA","WELSPUNLIV","COFORGE","ZYDUSLIFE","PERSISTENT","HAL","FLUOROCHEM","GULFOILLUB","INDIANB","GPPL","PIDILITIND","HAVELLS","DABUR","BERGEPAINT","GODREJCP","COLPAL","MARICO","UBL","MUTHOOTFIN","BANDHANBNK","IDFCFIRSTB","FEDERALBNK","PNB","BANKBARODA","CANBK","UNIONBANK","IOB","UCOBANK","BANKINDIA","MAHABANK","CENTRALBK","PSB","JKBANK","KARURVYSYA","RBLBANK","CUB","DCBBANK","YESBANK","IDFC","IRFC","PFC","RECLTD","HUDCO","IRCTC","RVNL","IRCON","NBCC","SJVN","NHPC","TATAPOWER","ADANIGREEN","ADANITRANS","TORNTPOWER","CESC","JSWENERGY","THERMAX","BHEL","ABB","SIEMENS","CUMMINSIND","VOLTAS","BLUESTARCO","POLYCAB","KEI","FINOLEX","RRKABEL","KAYNES","DIXON","AMBER","SYRMA","CROMPTON","BATAINDIA","RELAXO","METROBRAND","KALYANKJIL","PAGEIND","TRENT","ABFRL","SHOPPERSTOP","VMART","NYKAA","JUBLFOOD","DEVYANI","WESTLIFE","SAPPHIRE","DOMS","TTKPRESTIG","VIPIND","KAJARIACER","CERA","SOMANY","GREENPANEL","CENTURYPLY","NILKAMAL","LAOPALA","BOROSIL","RAJESHEXPO",
"LTIM","LTTS","MPHASIS","KPITTECH","TATAELXSI","SONACOMS","MOTHERSON","BOSCHLTD","ASHOKLEY","TVSMOTOR","HEROMOTOCO","BALKRISIND","MRF","CEATLTD","APOLLOTYRE","JKTYRE","ENDURANCE","MINDACORP","UNOMINDA","SUNDARMFIN","CHOLAFIN","MMFIN","CREDITACC","UJJIVANSFB","EQUITASBNK","AUBANK","BAJAJHLDNG","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDZINC","APLAPOLLO","RATNAMANI","WELCORP","TRIDENT","ALOKIND","RAYMOND","SRFL","DEEPAKNTR","NAVINFLUOR","GUJFLUORO","BALRAMCHIN","EIDPARRY","RENUKA","DWARKESH","AVANTIFEED","AARTIIND","ATUL","GHCL","TATACHEM","DEEPAKFERT","GNFC","GSFC","FACT","RCF","CHAMBALFERT","COROMANDEL","UPL","PIIND","RALLIS","DHANUKA","SUMICHEM","ASTRAL","SUPREMEIND","PRINCEPIPE","JAINIRRIG","MOLDTEK","TIME","POLYPLEX","GARWARE","SRF","JINDALPOLY","COSMOFIRST","INOXWIND","SUZLON","BORORENEW","WEBELSOLAR","NTPC","POWERGRID","AFFLE","MAPMYINDIA","TATACOMM","BHARTIHEXA","INDIAMART","JUSTDIAL","NAUKRI","ZOMATO","PAYTM","POLICYBZR","DELHIVERY","EASEMYTRIP","SWIGGY","OFSS","BSOFT","HAPPSTMNDS","INTELLECT","MASTEK","MINDSPACE","EMBASSY","BRIGADE","PRESTIGE","PHOENIXLTD","DLF","GODREJPROP","OBEROIRLTY","SOBHA","SUNTECK","LODHA","ANANTRAJ","MAHLIFE","IBREALEST","RAILTEL","IEX","MCX","BSE","CDSL","CAMS","KFINTECH","INDIGO","TITAGARH","JWL","JUPITER","TEXRAIL","BEML","COCHINSHIP","GRSE","MAZDOCK","BDL","BEL","BHARATFORG"
]

NIFTY500 = list(dict.fromkeys([x.strip().upper() for x in NIFTY500 if x.strip()]))
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

def analyze(symbol):
    df = get_data_safe(symbol)
    if df is None or len(df) < 150: return None
    try:
        df['EMA8'] = df['Close'].ewm(span=8).mean(); df['EMA20'] = df['Close'].ewm(span=20).mean(); df['EMA50'] = df['Close'].ewm(span=50).mean(); df['EMA200'] = df['Close'].ewm(span=200).mean()
        df['RSI14'] = 100 - (100/(1+(df['Close'].diff().where(lambda x: x>0,0).rolling(14).mean() / -df['Close'].diff().where(lambda x: x<0,0).rolling(14).mean()))); df['RSI9'] = 100 - (100/(1+(df['Close'].diff().where(lambda x: x>0,0).rolling(9).mean() / -df['Close'].diff().where(lambda x: x<0,0).rolling(9).mean())))
        df['VolAvg'] = df['Volume'].rolling(20).mean(); df['ATR'] = (df['High']-df['Low']).rolling(14).mean()
        cmp = safe_float(df['Close'].iloc[-1]); ema8 = safe_float(df['EMA8'].iloc[-1]); ema20 = safe_float(df['EMA20'].iloc[-1]); ema50 = safe_float(df['EMA50'].iloc[-1]); ema200 = safe_float(df['EMA200'].iloc[-1]); rsi14 = safe_float(df['RSI14'].iloc[-1]); rsi9 = safe_float(df['RSI9'].iloc[-1]); vol = safe_float(df['Volume'].iloc[-1]); vol_avg = safe_float(df['VolAvg'].iloc[-1]); vol_ratio = vol/vol_avg if vol_avg>0 else 0.5; atr = safe_float(df['ATR'].iloc[-1]); high_20 = safe_float(df['High'].rolling(20).max().iloc[-1])
        if cmp < 5 or ema8 == 0: return None
        trend = cmp > ema8 and ema8 > ema20 and ema20 > ema50; hm = cmp > ema200; rsi_ok = rsi14 > 55; true_bala = hm and trend and rsi_ok and vol_ratio > 0.4; htf_cluster = trend and hm
        score = (25 if trend else 0)+(20 if hm else 0)+(15 if rsi_ok else 0)+(10 if vol_ratio > 0.5 else 0)+(40 if true_bala else 0)+(20 if htf_cluster else 0)
        win = min(85, 50+score*0.2); prob = min(95, 60+(15 if trend else 0))
        
        # === ENTRY / SL / T1 / T2 LOGIC ===
        entry_low = round(cmp * 0.998, 2)  # -0.2% dip entry
        entry_high = round(cmp * 1.002, 2) # +0.2% breakout
        sl = round(min(ema50*0.97, cmp - atr*1.5), 2)  # 50EMA or ATR based, whichever higher
        # Ensure SL max 4% away
        if (cmp - sl)/cmp > 0.04:
            sl = round(cmp * 0.96, 2)
        t1 = round(cmp * 1.05, 2)  # 5% target
        t2 = round(max(high_20, cmp * 1.10), 2)  # 10% or 20-day high
        
        return {"symbol":symbol,"cmp":cmp,"rsi14":rsi14,"rsi9":rsi9,"vol_ratio":vol_ratio,"ema8":ema8,"ema20":ema20,"ema50":ema50,"ema200":ema200,"avwap":cmp,"wtf":"BULL","true_bala":true_bala,"htf_cluster":htf_cluster,"trend":trend,"hm":hm,"score":score,"win":win,"prob":prob,"entry_low":entry_low,"entry_high":entry_high,"sl":sl,"t1":t1,"t2":t2,"atr":atr}
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

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"ERROR: BOT_TOKEN missing={not BOT_TOKEN} CHAT_ID missing={not CHAT_ID}")
        return
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
    hour = now_ist.hour; minute = now_ist.minute
    is_btst_scan = (hour == 9 and minute >= 35 and minute <= 59)
    scan_type = "BTST" if is_btst_scan else "MORNING" if hour < 12 else "CLOSING"
    print(f"IST: {now_ist} | Scan Type: {scan_type}")
    
    results = []; seen = {}; btst_results = []
    
    for idx, sym in enumerate(NIFTY500):
        if sym.upper() in AUTO_EXCLUDE: continue
        if idx % 50 == 0 and idx > 0:
            print(f"Progress {idx}/{len(NIFTY500)}")
            time.sleep(2)
        base = analyze(sym)
        if not base: continue
        if scan_type == "BTST":
            btst_ok, avwap_30, prev_high, curr_price = check_btst_avwap(sym)
            if btst_ok:
                base['btst_ok']=True; base['avwap_30']=avwap_30; base['prev_30m_high']=prev_high
                base['final_rank']=base['score']*0.4 + base['win']*0.25 + base['prob']*0.25 + 20 + (15 if base['true_bala'] else 0)
                btst_results.append(base)
        else:
            if base['symbol'] not in seen or base['score'] > seen[base['symbol']]['score']:
                seen[base['symbol']]=base
    
    if scan_type == "BTST":
        btst_results = sorted(btst_results, key=lambda x: x['final_rank'], reverse=True)
        now_str = now_ist.strftime("%d-%m %I:%M %p")
        msg = f"🚀 BTST SCAN - {now_str}\nAVWAP > Prev 30m High | Price > AVWAP\nFound: {len(btst_results)}/{len(NIFTY500)} stocks\n\n"
        if len(btst_results)==0:
            msg += "No BTST stocks today! Market weak.\n"
        else:
            msg += f"🔥 BTST BEST 3 - BUY TOMORROW\n\n"
            for i, r in enumerate(btst_results[:3]):
                msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f}\n"
                msg += f"Entry: {r['entry_low']:.0f}-{r['entry_high']:.0f} (Buy on dip)\n"
                msg += f"SL: {r['sl']:.0f} ({((r['cmp']-r['sl'])/r['cmp']*100):.1f}%)\n"
                msg += f"T1: {r['t1']:.0f} (+5%) T2: {r['t2']:.0f} (+{((r['t2']/r['cmp']-1)*100):.0f}%)\n"
                msg += f"AVWAP:{r['avwap_30']:.0f} > 30mH:{r['prev_30m_high']:.0f} | R:{r['final_rank']:.0f} RSI:{r['rsi14']:.0f}\n\n"
        print(msg); send_telegram(msg); return
    
    results = list(seen.values())
    for r in results:
        r['final_rank'] = r['score']*0.4 + r['win']*0.25 + r['prob']*0.25 + (15 if r['true_bala'] else 0) + (10 if r['htf_cluster'] else 0)
    results = sorted(results, key=lambda x: x['final_rank'], reverse=True)
    
    true_bala_list = sorted([x for x in results if x['true_bala']], key=lambda x: x['final_rank'], reverse=True)
    htf_list = [x for x in results if x['htf_cluster'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]]]
    htf_list = sorted(htf_list, key=lambda x: x['final_rank'], reverse=True)
    trend_list = [x for x in results if x['trend'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]+htf_list[:3]]]
    trend_list = sorted(trend_list, key=lambda x: x['final_rank'], reverse=True)
    hm_list = [x for x in results if x['hm'] and x['symbol'] not in [y['symbol'] for y in true_bala_list[:3]+htf_list[:3]+trend_list[:3]]]
    hm_list = sorted(hm_list, key=lambda x: x['final_rank'], reverse=True)
    
    now_str = now_ist.strftime("%d-%m %I:%M %p")
    msg = f"🚀 MASTER V18.7 {scan_type} - {now_str}\nScan: {len(results)}/{len(NIFTY500)} | TB:{len(true_bala_list)} | HTF:{len(htf_list)}\n\n"
    
    def add_section(title, lst):
        nonlocal msg
        msg += f"{title} - Best 3\n"
        for i, r in enumerate(lst[:3]):
            msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} R:{r['final_rank']:.0f}\n"
            msg += f"   Entry:{r['entry_low']:.0f}-{r['entry_high']:.0f} SL:{r['sl']:.0f} T1:{r['t1']:.0f} T2:{r['t2']:.0f}\n"
        msg += f"\n"
    
    add_section("🔥 TRUE BALA", true_bala_list)
    add_section("💎 HTF CLUSTER", htf_list)
    add_section("📈 TREND", trend_list)
    add_section("🏔️ HM", hm_list)
    
    msg += f"🏆 FINAL BEST 3 - SYSTEM AUTO\n\n"
    for i, r in enumerate(results[:3]):
        risk = ((r['cmp']-r['sl'])/r['cmp']*100)
        reward1 = ((r['t1']/r['cmp']-1)*100)
        reward2 = ((r['t2']/r['cmp']-1)*100)
        msg += f"{i+1}. {r['symbol']} CMP:{r['cmp']:.0f} FinalRank:{r['final_rank']:.1f} {'🔥TB' if r['true_bala'] else ''}\n"
        msg += f"Entry: {r['entry_low']:.0f} - {r['entry_high']:.0f}\n"
        msg += f"SL: {r['sl']:.0f} (-{risk:.1f}%) | T1: {r['t1']:.0f} (+{reward1:.0f}%) | T2: {r['t2']:.0f} (+{reward2:.0f}%)\n"
        msg += f"RSI:{r['rsi14']:.0f} Vol:{r['vol_ratio']:.1f}x 8E:{r['ema8']:.0f} 20E:{r['ema20']:.0f}\n\n"
    
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
