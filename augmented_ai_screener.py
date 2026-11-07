import yfinance as yf
import pandas as pd
import os, requests
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]
CAPITAL = float(os.getenv("CAPITAL") or 100000)

def send_telegram(msg):
    # Telegram max 4096 chars, split
    for cid in CHAT_IDS:
        try:
            for i in range(0, len(msg), 3500):
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg[i:i+3500]}, timeout=20)
        except: pass

def load_nifty500():
    try:
        if os.path.exists("nifty500_list.csv"):
            df = pd.read_csv("nifty500_list.csv")
            return df['Symbol'].dropna().tolist()[:500]
    except: pass
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC"]

def get_indices():
    # Nifty, BankNifty, IT, FinNifty
    indices_map = {"NIFTY":"^NSEI", "BANKNIFTY":"^NSEBANK", "FINNIFTY":"^CNXFIN", "IT":"^CNXIT"}
    result = {}
    for name, ticker in indices_map.items():
        try:
            df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
            if len(df)==0: continue
            last = df.iloc[-1]
            h = float(last['High']); l = float(last['Low']); c = float(last['Close'])
            # Classic Pivot
            pp = (h+l+c)/3
            r1 = 2*pp - l
            s1 = 2*pp - h
            r2 = pp + (h-l)
            s2 = pp - (h-l)
            result[name] = {"price":c, "pp":pp, "s1":s1, "s2":s2, "r1":r1, "r2":r2}
        except: pass
    return result

def get_nifty_regime():
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
    return regime, score, price

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
    entry = price
    t1 = price + 1.5*atr
    t2 = price + 3.0*atr
    sl = max(ema20, price - 1.2*atr)
    risk = price - sl
    rr1 = (t1-price)/risk if risk>0 else 0
    rr2 = (t2-price)/risk if risk>0 else 0
    wins=0; tot=0
    for i in range(20,len(df)-5):
        if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA20'].iloc[i]>df['EMA50'].iloc[i]:
            tot+=1
            if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i]): wins+=1
    winp = int(wins/tot*100) if tot>0 else 50
    winp = min(95, max(45, winp + (points-60)//2))
    is_sniper = price>avwap and price>ema20 and vr>1.2
    weight = (winp * points * (1 + rr1))
    return {"price":price,"entry":entry,"points":points,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"risk":risk,"rr1":rr1,"rr2":rr2,"win":winp,"avwap":avwap,"sniper":is_sniper,"breakout":price>=high20*0.98,"trend":price>ema20 and ema20>ema50,"weight":weight}

def main():
    regime, nscore, nprice = get_nifty_regime()
    indices = get_indices()
    symbols = load_nifty500()
    symbols_ns = [s+".NS" for s in symbols]
    all_data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker', threads=True)
    
    all_picks=[]
    for sym in symbols:
        try:
            sym_ns = sym+".NS"
            if sym_ns not in all_data.columns.get_level_values(0): continue
            df = all_data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df)<30 or df['Close'].isna().all(): continue
            res = analyze(df)
            if res and res['points']>=60:
                all_picks.append({"sym":sym, **res})
        except: continue

    # Separate lists
    top_trend = sorted([p for p in all_picks if p['trend']], key=lambda x:(x['win'],x['points']), reverse=True)[:10]
    top_sniper = sorted([p for p in all_picks if p['sniper']], key=lambda x:(x['win'],x['points']), reverse=True)[:7]
    top_break = sorted([p for p in all_picks if p['breakout']], key=lambda x:x['vr'], reverse=True)[:7]
    
    # Top 3 to trade (65%+ win only)
    safe_picks = [p for p in all_picks if p['win']>=65]
    top3 = sorted(safe_picks, key=lambda x:x['weight'], reverse=True)[:3]
    total_weight = sum([p['weight'] for p in top3]) if top3 else 1
    for p in top3:
        p['alloc_pct'] = (p['weight']/total_weight)*100
        p['alloc_value'] = CAPITAL * p['alloc_pct']/100
        risk_amount = CAPITAL*0.015
        qty_by_risk = int(risk_amount/p['risk']) if p['risk']>0 else 0
        qty_by_cap = int(p['alloc_value']/p['price'])
        p['qty'] = max(1, min(qty_by_risk, qty_by_cap))

    # BUILD MESSAGE
    msg = f"🤖 MASTER BOT 500 V8.5 - {date.today()}\n"
    msg += f"NIFTY {nprice:.0f} Score:{nscore}/100 {regime}\n"
    msg += f"{'✅ TRADE' if nscore>=60 else '🛑 NO TRADE'} | {len(symbols)} scanned | Cap:Rs.{int(CAPITAL):,}\n\n"

    msg += f"📊 INDICES S/R:\n"
    for name, d in indices.items():
        msg += f"{name} {d['price']:.0f} | S2:{d['s2']:.0f} S1:{d['s1']:.0f} PP:{d['pp']:.0f} R1:{d['r1']:.0f} R2:{d['r2']:.0f}\n"
    
    msg += f"\n--------------------------\n"
    msg += f"📈 TOP TREND (10):\n"
    for i,p in enumerate(top_trend,1):
        msg += f"{i}. {p['sym']} {p['win']}% {p['points']}pts\n"
        msg += f"   E:{p['entry']:.0f} T1:{p['t1']:.0f} T2:{p['t2']:.0f} SL:{p['sl']:.0f}\n"

    msg += f"\n🎯 SNIPER AVWAP (7):\n"
    for i,p in enumerate(top_sniper,1):
        msg += f"{i}. {p['sym']} {p['price']:.0f}>{p['avwap']:.0f} {p['win']}%\n"
        msg += f"   E:{p['entry']:.0f} T1:{p['t1']:.0f} T2:{p['t2']:.0f} SL:{p['sl']:.0f}\n"

    msg += f"\n🚀 BREAKOUT (7):\n"
    for i,p in enumerate(top_break,1):
        msg += f"{i}. {p['sym']} Vol:{p['vr']:.1f}x {p['points']}pts {p['win']}%\n"
        msg += f"   E:{p['entry']:.0f} T1:{p['t1']:.0f} T2:{p['t2']:.0f} SL:{p['sl']:.0f}\n"

    msg += f"\n--------------------------\n"
    msg += f"💎 TOP 3 TO TRADE (SAFE):\n"
    for i,p in enumerate(top3,1):
        msg += f"{i}. {p['sym']} {p['win']}% {p['points']}pts QTY:{p['qty']} ({p['alloc_pct']:.0f}%)\n"
        msg += f"   ENTRY:{p['entry']:.0f} | T1:{p['t1']:.0f} (RR{ p['rr1']:.1f}) T2:{p['t2']:.0f} (RR{ p['rr2']:.1f}) SL:{p['sl']:.0f}\n"
        msg += f"   Val:Rs.{int(p['alloc_value']):,} Risk:Rs.{int(p['risk']*p['qty'])}\n\n"
    
    print(msg)
    send_telegram(msg)

if __name__=="__main__":
    main()
