import yfinance as yf
import pandas as pd
import os, requests
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]
CAPITAL = float(os.getenv("CAPITAL") or 100000)  # Set CAPITAL=100000 in GitHub secrets

def send_telegram(msg):
    for cid in CHAT_IDS:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg}, timeout=20)
        except: pass

def load_nifty500():
    try:
        if os.path.exists("nifty500_list.csv"):
            df = pd.read_csv("nifty500_list.csv")
            return df['Symbol'].dropna().tolist()[:500]
    except: pass
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC"]

def get_nifty():
    df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    atr_pct = float(last['ATR']/price*100); sh = float(df['High'].tail(20).max())
    score=0
    if price>ema20: score+=30
    if ema20>ema50: score+=30
    if atr_pct>1: score+=20
    if price>sh*0.99: score+=20
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
    try:
        low_idx = df['Low'].tail(20).idxmin()
        ds = df.loc[low_idx:]; avwap = float(((ds['Close']*ds['Volume']).cumsum() / ds['Volume'].cumsum()).iloc[-1])
    except: avwap = ema20
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
    t1 = price+1.5*atr; t2 = price+3*atr; sl = max(ema20, price-1.2*atr)
    risk_per_share = price - sl
    rr = (t1-price)/risk_per_share if risk_per_share>0 else 0
    wins=0; tot=0
    for i in range(20,len(df)-5):
        if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA20'].iloc[i]>df['EMA50'].iloc[i]:
            tot+=1
            if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i]): wins+=1
    winp = int(wins/tot*100) if tot>0 else 50
    winp = min(95, max(45, winp + (points-60)//2))
    is_sniper = price>avwap and price>ema20 and vr>1.2
    # POSITION SIZE SCORE
    score_weight = (winp * points * (1 + rr))  # Higher win + points + RR = bigger size
    return {"price":price,"points":points,"rsi":rsi,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"risk":risk_per_share,"rr":rr,"win":winp,"avwap":avwap,"sniper":is_sniper,"breakout":price>=high20*0.98,"trend":price>ema20 and ema20>ema50,"weight":score_weight}

def main():
    regime, nscore, nprice, natr = get_nifty()
    symbols = load_nifty500()
    symbols_ns = [s+".NS" for s in symbols]
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
            if res and res['points']>=60 and res['win']>=65:  # Only 65%+ win for safety
                picks.append({"sym":sym, **res})
        except: continue
    
    # Sort by weight
    picks = sorted(picks, key=lambda x: x['weight'], reverse=True)[:10]
    
    # Calculate position sizing
    total_weight = sum([p['weight'] for p in picks]) if picks else 1
    for p in picks:
        p['alloc_pct'] = (p['weight'] / total_weight) * 100
        p['alloc_value'] = (CAPITAL * p['alloc_pct'] / 100)
        # Risk 1.5% per trade max
        risk_amount = CAPITAL * 0.015
        qty_by_risk = int(risk_amount / p['risk']) if p['risk']>0 else 0
        qty_by_capital = int(p['alloc_value'] / p['price'])
        p['qty'] = min(qty_by_risk, qty_by_capital)  # Safer of two
        p['qty'] = max(1, p['qty'])  # At least 1

    msg = f"🤖 MASTER BOT 500 - {date.today()}\n"
    msg += f"NIFTY {nprice:.0f} Score:{nscore}/100 {regime}\n"
    msg += f"Capital: Rs.{int(CAPITAL):,} | Risk: 1.5%/trade\n"
    msg += f"{'✅ TRADE' if nscore>=60 else '🛑 NO TRADE'} | {len(symbols)} scanned\n"
    msg += f"--------------------------\n"
    msg += f"📈 TOP SAFE (Win>=65%):\n"
    for i,p in enumerate(picks,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f} {p['win']}% {p['points']}pts\n"
        msg += f"   QTY:{p['qty']} ({p['alloc_pct']:.0f}%) Val:Rs.{int(p['alloc_value']):,}\n"
        msg += f"   ->{p['t1']:.0f} SL:{p['sl']:.0f} RR:{p['rr']:.1f}\n"
    
    msg += f"\n💡 Size = Win% x Points x RR\n"
    msg += f"BHARTIARTL 95% = Largest size"
    
    print(msg)
    send_telegram(msg)

if __name__=="__main__":
    main()
