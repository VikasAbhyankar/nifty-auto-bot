import yfinance as yf
import pandas as pd
import os, requests
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]

def send_telegram(msg):
    for cid in CHAT_IDS:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg}, timeout=20)
        except: pass

def load_nifty500():
    try:
        if os.path.exists("nifty500_list.csv"):
            df = pd.read_csv("nifty500_list.csv")
            syms = df['Symbol'].dropna().tolist()
            print(f"Loaded {len(syms)} from CSV")
            return syms[:500]
    except Exception as e:
        print(f"CSV load failed {e}")
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","HINDUNILVR","MARUTI","KOTAKBANK","AXISBANK","ASIANPAINT","WIPRO","SUNPHARMA","ONGC","NTPC","POWERGRID","M&M","TITAN","ULTRACEMCO","NESTLEIND","ADANIENT","ADANIPORTS","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","BAJAJFINSV","DRREDDY","CIPLA","TECHM","GRASIM","BRITANNIA","EICHERMOT","APOLLOHOSP","INDUSINDBK","HEROMOTOCO","BPCL","DIVISLAB","BAJAJ-AUTO","SBILIFE","HDFCLIFE","UPL","SHRIRAMFIN"]

def get_nifty():
    df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    atr_pct = float(last['ATR']/price*100); sh = float(df['High'].tail(20).max())
    score = 0
    if price > ema20: score+=30
    if ema20 > ema50: score+=30
    if atr_pct > 1: score+=20
    if price > sh*0.99: score+=20
    regime = "TRENDING_BULL" if score>=80 else "MILD_BULL" if score>=50 else "RANGE"
    return regime, score, price, atr_pct

def analyze(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['High20'] = df['High'].rolling(20).max()
    df['Vol20'] = df['Volume'].rolling(20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    if pd.isna(last['EMA20']) or pd.isna(last['Vol20']): return None
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    high20 = float(last['High20']); vol20 = float(last['Vol20']); vol_now = float(last['Volume']); atr = float(last['ATR'])
    delta = df['Close'].diff(); gain = delta.where(delta>0,0).rolling(14).mean(); loss = -delta.where(delta<0,0).rolling(14).mean(); rs = gain/loss
    rsi = float(100 - (100/(1+rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50
    # AVWAP
    try:
        low_idx = df['Low'].tail(20).idxmin()
        ds = df.loc[low_idx:]; avwap = float(((ds['Close']*ds['Volume']).cumsum() / ds['Volume'].cumsum()).iloc[-1])
    except:
        avwap = ema20
    points=0
    if price>ema20: points+=20
    if ema20>ema50: points+=20
    vr = vol_now/vol20 if vol20>0 else 1
    if vr>2: points+=20
    elif vr>1.5: points+=15
    elif vr>1.2: points+=10
    if price>=high20*0.995: points+=20
    elif price>=high20*0.98: points+=10
    if 60<=rsi<=75: points+=20
    elif 55<=rsi<=80: points+=10
    t1 = price+1.5*atr; t2 = price+3*atr; sl = max(ema20, price-1.2*atr); rr = (t1-price)/(price-sl) if (price-sl)>0 else 0
    wins=0; tot=0
    for i in range(20,len(df)-5):
        if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA20'].iloc[i]>df['EMA50'].iloc[i]:
            tot+=1
            if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i]): wins+=1
    winp = int(wins/tot*100) if tot>0 else 50
    winp = min(95, max(45, winp + (points-60)//2))
    is_sniper = price>avwap and price>ema20 and vr>1.2
    return {"price":price,"points":points,"rsi":rsi,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"rr":rr,"win":winp,"avwap":avwap,"sniper":is_sniper,"breakout":price>=high20*0.98,"trend":price>ema20 and ema20>ema50}

def main():
    regime, nscore, nprice, natr = get_nifty()
    symbols = load_nifty500()
    symbols_ns = [s+".NS" for s in symbols]
    # BATCH DOWNLOAD - ULTRA FAST
    all_data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker', threads=True)
    
    picks=[]
    for sym in symbols:
        try:
            sym_ns = sym+".NS"
            if sym_ns not in all_data.columns.get_level_values(0): continue
            df = all_data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df)<30 or df['Close'].isna().all(): continue
            res = analyze(df)
            if res and res['points']>=60: picks.append({"sym":sym, **res})
        except: continue
    
    # Sort
    top_trend = sorted([p for p in picks if p['trend']], key=lambda x:(x['win'],x['points']), reverse=True)[:10]
    top_sniper = sorted([p for p in picks if p['sniper']], key=lambda x:(x['win'],x['points']), reverse=True)[:7]
    top_break = sorted([p for p in picks if p['breakout']], key=lambda x:x['vr'], reverse=True)[:7]

    msg = f"🤖 MASTER BOT 500 - {date.today()}\n"
    msg += f"NIFTY {nprice:.0f} Score:{nscore}/100 {regime} ATR:{natr:.1f}%\n"
    msg += f"{'✅ TRADE' if nscore>=60 else '🛑 NO TRADE'} | Scanned {len(symbols)} stocks\n"
    msg += f"--------------------------\n"
    msg += f"📈 TOP TREND (Nifty500):\n"
    for i,p in enumerate(top_trend,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} {p['win']}% {p['points']}pts\n   ->{p['t1']:.0f} SL:{p['sl']:.0f} RR:{p['rr']:.1f}\n"
    msg += f"\n🎯 SNIPER AVWAP:\n"
    for i,p in enumerate(top_sniper,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f}>{p['avwap']:.0f} Win:{p['win']}% T:{p['t1']:.0f}\n"
    msg += f"\n🚀 BREAKOUT:\n"
    for i,p in enumerate(top_break,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} Vol:{p['vr']:.1f}x {p['points']}pts\n"
    
    print(msg)
    send_telegram(msg)

if __name__=="__main__":
    main()
