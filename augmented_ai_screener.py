import os, requests, yfinance as yf, pandas as pd, numpy as np, time
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""

# === FULL NIFTY 500 LIST ===
NIFTY500 = [
"RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","LICI","BAJFINANCE","LT","HCLTECH","ITC","KOTAKBANK","SUNPHARMA","MARUTI","TITAN","ULTRACEMCO","AXISBANK","NTPC","ONGC","BAJAJFINSV","DMART","ADANIENT","ADANIPORTS","POWERGRID","WIPRO","TATASTEEL","HDFCLIFE","SBILIFE","ASIANPAINT","BAJAJAUTO","COALINDIA","TATAMOTORSPV","JSWSTEEL","HINDALCO","GRASIM","CIPLA","TECHM","BPCL","DIVISLAB","DRREDDY","EICHERMOT","INDUSINDBK","BRITANNIA","SHRIRAMFIN","APOLLOHOSP","TATACONSUM","VEDL",
"TANLA","WELSPUNLIV","COFORGE","ZYDUSLIFE","PERSISTENT","HAL","FLUOROCHEM","GULFOILLUB","INDIANB","GPPL","PIDILITIND","HAVELLS","DABUR","BERGEPAINT","GODREJCP","COLPAL","MARICO","UBL","MUTHOOTFIN","BANDHANBNK","IDFCFIRSTB","FEDERALBNK","PNB","BANKBARODA","CANBK","UNIONBANK","IOB","UCOBANK","BANKINDIA","MAHABANK","CENTRALBK","PSB","JKBANK","KARURVYSYA","RBLBANK","CUB","DCBBANK","YESBANK","IDFC","IRFC","PFC","RECLTD","HUDCO","IRCTC","RVNL","IRCON","NBCC","SJVN","NHPC","TATAPOWER","ADANIGREEN","ADANITRANS","TORNTPOWER","CESC","JSWENERGY","THERMAX","BHEL","ABB","SIEMENS","CUMMINSIND","VOLTAS","BLUESTARCO","POLYCAB","KEI","FINOLEX","RRKABEL","KAYNES","DIXON","AMBER","SYRMA","CROMPTON","BATAINDIA","RELAXO","METROBRAND","KALYANKJIL","PAGEIND","TRENT","ABFRL","SHOPPERSTOP","VMART","NYKAA","JUBLFOOD","DEVYANI","WESTLIFE","SAPPHIRE","DOMS","TTKPRESTIG","VIPIND","KAJARIACER","CERA","SOMANY","GREENPANEL","CENTURYPLY","NILKAMAL","LAOPALA","BOROSIL","RAJESHEXPO",
"LTIM","LTTS","MPHASIS","KPITTECH","TATAELXSI","SONACOMS","MOTHERSON","BOSCHLTD","ASHOKLEY","TVSMOTOR","HEROMOTOCO","BALKRISIND","MRF","CEATLTD","APOLLOTYRE","JKTYRE","ENDURANCE","MINDACORP","UNOMINDA","SUNDARMFIN","CHOLAFIN","MMFIN","CREDITACC","UJJIVANSFB","EQUITASBNK","AUBANK","BAJAJHLDNG","JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDZINC","APLAPOLLO","RATNAMANI","WELCORP","TRIDENT","ALOKIND","RAYMOND","SRFL","DEEPAKNTR","NAVINFLUOR","GUJFLUORO","BALRAMCHIN","EIDPARRY","RENUKA","DWARKESH","AVANTIFEED","AARTIIND","ATUL","GHCL","TATACHEM","DEEPAKFERT","GNFC","GSFC","FACT","RCF","CHAMBALFERT","COROMANDEL","UPL","PIIND","RALLIS","DHANUKA","SUMICHEM","ASTRAL","SUPREMEIND","PRINCEPIPE","JAINIRRIG","MOLDTEK","TIME","POLYPLEX","GARWARE","SRF","JINDALPOLY","COSMOFIRST","INOXWIND","SUZLON","BORORENEW","WEBELSOLAR","NTPC","POWERGRID","NHPC","SJVN","ABB","SIEMENS","CUMMINSIND","VOLTAS","BLUESTARCO","HAVELLS","POLYCAB","KEI","FINOLEXCABLE","RRKABEL","KAYNES","DIXON","AMBER","SYRMA","CROMPTON","BATAINDIA","RELAXO","METROBRAND","KALYANKJIL","TITAN","PAGEIND","TRENT","ABFRL","SHOPPERSTOP","VMART","NYKAA","TATACONSUM","JUBLFOOD","DEVYANI","WESTLIFE","SAPPHIRE","DOMS","TTKPRESTIG","VIPIND","KAJARIACER","CERA","SOMANY","GREENPANEL","CENTURYPLY","NILKAMAL","LAOPALA","BOROSIL","RAJESHEXPO","AFFLE","MAPMYINDIA","TATACOMM","BHARTIHEXA","INDIAMART","JUSTDIAL","NAUKRI","ZOMATO","PAYTM","POLICYBZR","DELHIVERY","EASEMYTRIP","IRCTC","SWIGGY","TANLA","TATAELXSI","LTTS","LTIM","OFSS","BSOFT","HAPPSTMNDS","INTELLECT","MASTEK","MINDSPACE","EMBASSY","BRIGADE","PRESTIGE","PHOENIXLTD","DLF","GODREJPROP","OBEROIRLTY","SOBHA","SUNTECK","LODHA","ANANTRAJ","MAHLIFE","IBREALEST","NBCC","HUDCO","RVNL","IRCON","RAILTEL","IRFC","PFC","RECLTD","IEX","MCX","BSE","CDSL","CAMS","KFINTECH","CREDITACC","UJJIVAN","EQUITAS","AUBANK","FEDERALBNK","IDFCFIRSTB","KARURVYSYA","CUB","RBLBANK","BANDHANBNK","PNB","BANKBARODA","CANBK","UNIONBANK","INDIANB","MAHABANK","IOB","CENTRALBK","UCOBANK","BANKINDIA","PSB","JKBANK","YESBANK","IDFC","IRCTC","INDIGO","INTERGLOBE","TITAGARH","JWL","JUPITER","TEXRAIL","BEML","COCHINSHIP","GRSE","MAZDOCK","HAL","BDL","BEL","BHARATFORG","ASHOKLEY","TVSMOTOR","BAJAJAUTO","EICHERMOT","HEROMOTOCO","MARUTI","MM","TATAMOTORSPV","MOTHERSON","SONACOMS","BOSCHLTD","BALKRISIND","MRF","CEATLTD","APOLLOTYRE","JKTYRE","ENDURANCE","MINDACORP","UNOMINDA"
]

# === DEDUPLICATE ===
NIFTY500 = list(dict.fromkeys([x.strip().upper() for x in NIFTY500 if x.strip()]))
print(f"Deduped Nifty500: {len(NIFTY500)} unique")

FAILED_FILE = "failed_symbols.txt"
AUTO_EXCLUDE = set()
try:
    if os.path.exists(FAILED_FILE):
        with open(FAILED_FILE, "r") as f:
            AUTO_EXCLUDE = set([x.strip().upper() for x in f.read().split(",") if x.strip()])
except:
    AUTO_EXCLUDE = set()

RENAME_MAP = {"TATAMOTORS":"TATAMOTORSPV","M&M":"M&M","BAJAJ-AUTO":"BAJAJAUTO","L&TFH":"LTF"}

def safe_float(x):
    try:
        if isinstance(x, pd.Series): return float(x.iloc[0])
        return float(x)
    except: return 0.0

def get_data_safe(symbol):
    if symbol.upper() in AUTO_EXCLUDE:
        return None
    try_symbol = RENAME_MAP.get(symbol.upper(), symbol)
    for attempt in range(2):
        try:
            df = yf.download(try_symbol+".NS", period="1y", progress=False, auto_adjust=False, timeout=15)
            if df is not None and len(df) > 100 and safe_float(df['Close'].iloc[-1]) > 0:
                return df
        except:
            time.sleep(1)
            continue
    print(f"TEMP FAIL {symbol}")
    return None

def analyze(symbol):
    df = get_data_safe(symbol)
    if df is None or len(df) < 150:
        return None
    try:
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        df['RSI14'] = 100 - (100/(1+(df['Close'].diff().where(lambda x: x>0,0).rolling(14).mean() / -df['Close'].diff().where(lambda x: x<0,0).rolling(14).mean())))
        df['RSI9'] = 100 - (100/(1+(df['Close'].diff().where(lambda x: x>0,0).rolling(9).mean() / -df['Close'].diff().where(lambda x: x<0,0).rolling(9).mean())))
        df['VolAvg'] = df['Volume'].rolling(20).mean()
        cmp = safe_float(df['Close'].iloc[-1]); ema8 = safe_float(df['EMA8'].iloc[-1]); ema20 = safe_float(df['EMA20'].iloc[-1]); ema50 = safe_float(df['EMA50'].iloc[-1]); ema200 = safe_float(df['EMA200'].iloc[-1]); rsi14 = safe_float(df['RSI14'].iloc[-1]); rsi9 = safe_float(df['RSI9'].iloc[-1]); vol = safe_float(df['Volume'].iloc[-1]); vol_avg = safe_float(df['VolAvg'].iloc[-1]); vol_ratio = vol/vol_avg if vol_avg > 0 else 0.5
        if cmp < 5 or ema8 == 0: return None
        trend = cmp > ema8 and ema8 > ema20 and ema20 > ema50; hm = cmp > ema200; rsi_ok = rsi14 > 55; true_bala = hm and trend and rsi_ok and vol_ratio > 0.4; htf_cluster = trend and hm
        score = (25 if trend else 0)+(20 if hm else 0)+(15 if rsi_ok else 0)+(10 if vol_ratio > 0.5 else 0)+(40 if true_bala else 0)+(20 if htf_cluster else 0)
        win = min(85, 50+score*0.2); prob = min(95, 60+(15 if trend else 0))
        return {"symbol":symbol,"cmp":cmp,"rsi14":rsi14,"rsi9":rsi9,"vol_ratio":vol_ratio,"ema8":ema8,"ema20":ema20,"ema50":ema50,"ema200":ema200,"avwap":cmp,"wtf":"BULL","true_bala":true_bala,"htf_cluster":htf_cluster,"trend":trend,"hm":hm,"score":score,"win":win,"prob":prob,"sl":ema50*0.95}
    except Exception as e:
        print(f"{symbol} err {e}")
        return None

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
    results = []
    seen = {}
    print(f"Starting scan {len(NIFTY500)} symbols, excluding {len(AUTO_EXCLUDE)}")
    for idx, sym in enumerate(NIFTY500):
        if sym.upper() in AUTO_EXCLUDE:
            continue
        if idx % 50 == 0 and idx > 0:
            print(f"Progress {idx}/{len(NIFTY500)}")
            time.sleep(2)
        res = analyze(sym)
        if res:
            if res['symbol'] not in seen or res['score'] > seen[res['symbol']]['score']:
                seen[res['symbol']] = res
    
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
    
    now = datetime.now().strftime("%d-%m %I:%M %p")
    msg = f"🚀 MASTER V18.5 TRUE BALA - {now}\n"
    msg += f"Scan: {len(results)}/{len(NIFTY500)} | TB:{len(true_bala_list)} | HTF:{len(htf_list)} | Excl:{len(AUTO_EXCLUDE)}\n\n"
    
    def add_section(title, lst):
        nonlocal msg
        msg += f"{title} - Best 3\n"
        for i, r in enumerate(lst[:3]):
            msg += f"{i+1}. {r['symbol']} R:{r['final_rank']:.0f} P:{r['prob']:.0f}% Vol:{r['vol_ratio']:.1f}x CMP:{r['cmp']:.0f} RSI:{r['rsi14']:.0f}\n"
        msg += f"\n"
    
    add_section("🔥 TRUE BALA", true_bala_list)
    add_section("💎 HTF CLUSTER", htf_list)
    add_section("📈 TREND (8>20>50)", trend_list)
    add_section("🏔️ HM (Above 200EMA)", hm_list)
    
    msg += f"🏆 FINAL BEST 3 - SYSTEM AUTO\n\n"
    for i, r in enumerate(results[:3]):
        msg += f"{i+1}. {r['symbol']} FinalRank:{r['final_rank']:.1f} Prob:{r['prob']:.0f}% {'🔥TB' if r['true_bala'] else ''} {'💎HTF' if r['htf_cluster'] else ''}\n"
        msg += f"Score:{r['score']} Win:{r['win']:.0f}% Vol:{r['vol_ratio']:.1f}x CMP:{r['cmp']:.0f} RSI:{r['rsi14']:.0f}/{r['rsi9']:.0f}\n"
        msg += f"8E:{r['ema8']:.0f} 20E:{r['ema20']:.0f} 50E:{r['ema50']:.0f} SL:{r['sl']:.0f} T1:{r['cmp']*1.05:.0f}\n\n"
    
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
