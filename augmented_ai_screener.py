import yfinance as yf
import pandas as pd
import os, requests
from datetime import date
import numpy as np

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.replace(" ", ",").split(",") if x.strip()]
CAPITAL = float(os.getenv("CAPITAL") or 100000)

def send_telegram(msg):
    for cid in CHAT_IDS:
        try:
            for i in range(0, len(msg), 4000):
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": msg[i:i+4000]}, timeout=20)
        except: pass

def wma(series, period):
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def load_nifty500():
    try:
        if os.path.exists("nifty500_list.csv"):
            df = pd.read_csv("nifty500_list.csv")
            return df['Symbol'].dropna().tolist()[:500]
    except: pass
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","BSE","BHARTIHEXA","LTTS","HCLTECH","SHYAMMETL","WIPRO","COFORGE","TECHM","PERSISTENT","TITAN","KALYANKJIL","WABAG","M&M","HINDALCO","INDUSINDBK","DIVISLAB","INDHOTEL","HAL","BANKBARODA","PNB","CIPLA","FDC","FSL","ULTRACEMCO","JSWSTEEL","IOC","HDFCBANK"]

def get_indices():
    indices_map = {"NIFTY":"^NSEI", "BANKNIFTY":"^NSEBANK", "FINNIFTY":"^CNXFIN", "IT":"^CNXIT"}
    result = {}
    for name, ticker in indices_map.items():
        try:
            df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
            if len(df)==0: continue
            last = df.iloc[-1]
            h = float(last['High']); l = float(last['Low']); c = float(last['Close'])
            pp = (h+l+c)/3; r1 = 2*pp - l; s1 = 2*pp - h; r2 = pp + (h-l); s2 = pp - (h-l)
            result[name] = {"price":c, "pp":pp, "s1":s1, "s2":s2, "r1":r1, "r2":r2}
        except: pass
    return result

def get_market_sentiment(all_data, symbols):
    df_n = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
    df_n['EMA20'] = df_n['Close'].ewm(span=20).mean()
    df_n['EMA50'] = df_n['Close'].ewm(span=50).mean()
    df_n['ATR'] = (df_n['High'] - df_n['Low']).rolling(14).mean()
    last = df_n.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    atr_pct = float(last['ATR']/price*100); sh = float(df_n['High'].tail(20).max())
    nifty_score=0
    if price>ema20: nifty_score+=30
    if ema20>ema50: nifty_score+=30
    if atr_pct>1: nifty_score+=20
    if price>sh*0.99: nifty_score+=20
    above=0; total=0
    for sym in symbols[:120]:
        try:
            sym_ns = sym+".NS"
            if sym_ns not in all_data.columns.get_level_values(0): continue
            df = all_data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df)<25: continue
            df['EMA20'] = df['Close'].ewm(span=20).mean()
            if float(df['Close'].iloc[-1]) > float(df['EMA20'].iloc[-1]): above+=1
            total+=1
        except: continue
    breadth = (above/total*100) if total>0 else 50
    if nifty_score>=80 and breadth>=65:
        regime="TRENDING_BULL"; sentiment="Extreme Bull - Buy Trend + Bala WMA"
        weights={"trend":30,"bala_wma":35,"breakout":20,"sniper":10,"dip":5}; min_win=70
    elif nifty_score>=60 and breadth>=55:
        regime="MILD_BULL"; sentiment="Mild Bull - Balanced"
        weights={"trend":20,"bala_wma":20,"breakout":20,"sniper":20,"dip":20}; min_win=68
    elif nifty_score>=40:
        regime="RANGE"; sentiment="Range - Buy Dip + Sniper"
        weights={"trend":15,"bala_wma":10,"breakout":5,"sniper":30,"dip":40}; min_win=75
    else:
        regime="BEAR"; sentiment="Bear - No Trade"
        weights={"trend":0,"bala_wma":0,"breakout":0,"sniper":0,"dip":0}; min_win=80
    return regime, nifty_score, price, breadth, sentiment, weights, min_win

def analyze(df, weights):
    df['EMA8'] = df['Close'].ewm(span=8).mean()
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['WMA8'] = wma(df['Close'], 8)
    df['WMA20'] = wma(df['Close'], 20)
    df['WMA50'] = wma(df['Close'], 50)
    df['High20'] = df['High'].rolling(20).max()
    df['Vol20'] = df['Volume'].rolling(20).mean()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    last = df.iloc[-1]
    if pd.isna(last['EMA20']) or pd.isna(last['Vol20']) or pd.isna(last['WMA20']): return None
    price = float(last['Close']); ema8 = float(last['EMA8']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50'])
    wma8 = float(last['WMA8']); wma20 = float(last['WMA20']); wma50 = float(last['WMA50'])
    high20 = float(last['High20']); vol20 = float(last['Vol20']); vol_now = float(last['Volume']); atr = float(last['ATR'])
    h = float(last['High']); l = float(last['Low']); c = float(last['Close'])
    pp = (h+l+c)/3; r1 = 2*pp - l; s1 = 2*pp - h; r2 = pp + (h-l); s2 = pp - (h-l)
    delta = df['Close'].diff(); gain = delta.where(delta>0,0).rolling(14).mean(); loss = -delta.where(delta<0,0).rolling(14).mean(); rs = gain/loss
    rsi = float(100 - (100/(1+rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50
    try:
        low_idx = df['Low'].tail(20).idxmin()
        ds = df.loc[low_idx:]; avwap = float(((ds['Close']*ds['Volume']).cumsum() / ds['Volume'].cumsum()).iloc[-1])
    except: avwap = ema20
    vr = vol_now/vol20 if vol20>0 else 1
    trend_score = 0
    if price>ema20: trend_score+=50
    if ema20>ema50: trend_score+=50
    bala_wma_score = 100 if (wma8 > wma20 > wma50 and price > wma8) else 0
    if bala_wma_score==0 and wma8>wma20: bala_wma_score=50
    dip_score = 0
    dist = abs(price-ema8)/price*100
    if dist<=1: dip_score=100
    elif dist<=2.5: dip_score=80
    elif dist<=4: dip_score=50
    sniper_score = 100 if (price>avwap and price>ema20 and vr>1.2) else 0
    if sniper_score==0 and price>avwap: sniper_score=50
    breakout_score = 0
    if price>=high20*0.995 and vr>1.5: breakout_score=100
    elif price>=high20*0.98 and vr>1.2: breakout_score=70
    elif price>=high20*0.97: breakout_score=40
    composite = (trend_score*weights['trend'] + bala_wma_score*weights['bala_wma'] + breakout_score*weights['breakout'] + sniper_score*weights['sniper'] + dip_score*weights['dip'])/100
    points = int(composite)
    entry = price; t1 = price + 1.5*atr; t2 = price + 3.0*atr
    sl = max(ema20, price - 1.2*atr)
    entry_low = max(ema20, price - 0.4*atr)
    entry_high = price + 0.3*atr
    risk = price - sl; rr1 = (t1-price)/risk if risk>0 else 0; rr2 = (t2-price)/risk if risk>0 else 0
    wins=0; tot=0
    for i in range(20,len(df)-5):
        if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA20'].iloc[i]>df['EMA50'].iloc[i]:
            tot+=1
            if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i]): wins+=1
    winp = int(wins/tot*100) if tot>0 else 50
    winp = min(95, max(45, winp + (composite-50)//2))
    weight = winp * composite * (1+rr1) * (1+vr/3)
    # Buy zone tag
    if price <= s1*1.01: zone="🟢 DEEP DIP - STRONG BUY"
    elif price <= pp: zone="🟡 NEAR SUPPORT - BUY"
    elif price <= r1: zone="🔵 ABOVE PP - MOMENTUM BUY"
    else: zone="🔴 NEAR R1/R2 - WAIT FOR DIP"
    return {"price":price,"entry":entry,"entry_low":entry_low,"entry_high":entry_high,"points":points,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"pp":pp,"r1":r1,"r2":r2,"s1":s1,"s2":s2,"risk":risk,"rr1":rr1,"rr2":rr2,"win":winp,"avwap":avwap,"sniper":sniper_score>=70,"breakout":breakout_score>=70,"trend":trend_score>=50,"weight":weight,"bala_wma":bala_wma_score>=100,"bala_near8":dip_score>=80,"wma8":wma8,"wma20":wma20,"wma50":wma50,"ema8":ema8,"composite":composite,"zone":zone,"scores":{"trend":trend_score,"bala":bala_wma_score,"dip":dip_score,"sniper":sniper_score,"break":breakout_score}}

def main():
    symbols = load_nifty500()
    symbols_ns = [s+".NS" for s in symbols]
    all_data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker', threads=True)
    regime, nscore, nprice, breadth, sentiment, weights, min_win = get_market_sentiment(all_data, symbols)
    indices = get_indices()
    all_picks=[]
    for sym in symbols:
        try:
            sym_ns = sym+".NS"
            if sym_ns not in all_data.columns.get_level_values(0): continue
            df = all_data[sym_ns]
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(0)
            if len(df)<30 or df['Close'].isna().all(): continue
            res = analyze(df, weights)
            if res and res['composite']>=60 and res['win']>=min_win:
                all_picks.append({"sym":sym, **res})
        except: continue

    # FIXED: TOP 10 also filtered by min_win 70% - No more HDFCBANK 45%!
    top_hybrid = sorted(all_picks, key=lambda x:(x['composite'], x['win']), reverse=True)[:10]
    bala_wma_list = sorted([p for p in all_picks if p['bala_wma']], key=lambda x:(x['win'],x['composite']), reverse=True)[:7]
    
    safe_picks = [p for p in all_picks if p['win']>=min_win]
    top3 = sorted(safe_picks, key=lambda x:x['weight'], reverse=True)[:3]
    total_weight = sum([p['weight'] for p in top3]) if top3 else 1
    for idx, p in enumerate(top3):
        if regime=="TRENDING_BULL":
            allocs = [40,35,25]
            p['alloc_pct'] = allocs[idx] if idx<3 else 33
        else:
            p['alloc_pct'] = (p['weight']/total_weight)*100
        p['alloc_value'] = CAPITAL * p['alloc_pct']/100
        risk_amount = CAPITAL*0.015
        qty_by_risk = int(risk_amount/p['risk']) if p['risk']>0 else 0
        qty_by_cap = int(p['alloc_value']/p['price'])
        p['qty'] = max(1, min(qty_by_risk, qty_by_cap))

    msg = f"🤖 MASTER BOT V11.2 FINAL HYBRID - {date.today()}\n"
    msg += f"NIFTY {nprice:.0f} Score:{nscore} Breadth:{breadth:.0f}% {regime}\n"
    msg += f"🧠 {sentiment}\n"
    msg += f"⚖️ W:T{weights['trend']}% B{weights['bala_wma']}% Br{weights['breakout']}% S{weights['sniper']}% D{weights['dip']}% | MinWin:{min_win}% | Filtered: {len(all_picks)} stocks\n\n"
    msg += f"📊 INDICES S/R:\n"
    for name, d in indices.items():
        msg += f"{name} {d['price']:.0f} | S2:{d['s2']:.0f} S1:{d['s1']:.0f} PP:{d['pp']:.0f} R1:{d['r1']:.0f} R2:{d['r2']:.0f}\n"
    msg += f"\n--------------------------\n🏆 HYBRID TOP 10 (Min {min_win}% Win Filtered):\n"
    for i,p in enumerate(top_hybrid,1):
        msg += f"{i}. {p['sym']} Comp:{p['composite']:.0f} Win:{p['win']}% Vol:{p['vr']:.1f}x E:{p['entry']:.0f} {p['zone']}\n"

    msg += f"\n💎 BALA 8-20-50 WMA (7):\n"
    for i,p in enumerate(bala_wma_list,1):
        msg += f"{i}. {p['sym']} {p['wma8']:.0f}>{p['wma20']:.0f}>{p['wma50']:.0f} {p['win']}% Comp:{p['composite']:.0f} {p['zone']}\n"

    msg += f"\n--------------------------\n💎 TOP 3 TO TRADE - FULL LEVELS:\n"
    for i,p in enumerate(top3,1):
        tags=[]
        if p['bala_wma']: tags.append("BALA")
        if p['sniper']: tags.append("SNIPER")
        if p['breakout']: tags.append("BREAK")
        tag_str = f"[{','.join(tags)}]" if tags else ""
        msg += f"\n{i}. {p['sym']} {tag_str} Comp:{p['composite']:.0f} Win:{p['win']}% QTY:{p['qty']} ({p['alloc_pct']:.0f}%) {p['zone']}\n"
        msg += f"   ENTRY RANGE: {p['entry_low']:.0f} - {p['entry_high']:.0f} (CMP:{p['entry']:.0f})\n"
        msg += f"   TARGETS: T1:{p['t1']:.0f} (RR{ p['rr1']:.1f}) | T2:{p['t2']:.0f} (RR{ p['rr2']:.1f})\n"
        msg += f"   STOPLOSS: {p['sl']:.0f} | Risk:Rs.{int(p['risk']*p['qty'])} | Val:Rs.{int(p['alloc_value']):,}\n"
        msg += f"   PIVOT S/R: S2:{p['s2']:.0f} S1:{p['s1']:.0f} PP:{p['pp']:.0f} R1:{p['r1']:.0f} R2:{p['r2']:.0f}\n"
        msg += f"   Logic: T:{p['scores']['trend']:.0f} B:{p['scores']['bala']:.0f} D:{p['scores']['dip']:.0f} S:{p['scores']['sniper']:.0f} Br:{p['scores']['break']:.0f}\n"

    print(msg)
    send_telegram(msg)

if __name__=="__main__":
    main()
