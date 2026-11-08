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

def calc_avwap(df, anchor_idx):
    try:
        ds = df.loc[anchor_idx:]
        return float(((ds['Close']*ds['Volume']).cumsum() / ds['Volume'].cumsum()).iloc[-1])
    except: return float(df['Close'].ewm(span=20).mean().iloc[-1])

def clean_df(df):
    # FIX FOR MULTIINDEX ISSUE
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0) if 'Close' in df.columns.get_level_values(0) else df.columns.get_level_values(1)
    # If still has duplicate columns, take first
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def load_nifty500():
    # CLEANED LIST - Removed delisted
    default_list = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","BSE","BHARTIHEXA","LTTS","HCLTECH","SHYAMMETL","WIPRO","COFORGE","TECHM","PERSISTENT","TITAN","M&M","HINDALCO","DIVISLAB","INDHOTEL","HAL","BANKBARODA","PNB","CIPLA","FDC","FSL","SYNGENE","TANLA","UNIONBANK","DRREDDY","TATAELXSI","JSWSTEEL","IOC","ULTRACEMCO","ICICIBANK","BHARTIARTL","ETERNAL","TATAMOTORS","ZENSAR","INDUSINDBK"]
    try:
        if os.path.exists("nifty500_list.csv"):
            df = pd.read_csv("nifty500_list.csv")
            lst = df['Symbol'].dropna().tolist()
            # Clean old names
            replace_map = {"ZOMATO":"ETERNAL","TATAMOTORS":"TATAMOTORS","PEL":"PEL","MCDOWELL-N":"MCDOWELL-N","JUBILANT.N":"JUBILANTFOOD"}
            cleaned=[]
            for s in lst:
                s=s.strip().upper()
                if s in replace_map: s=replace_map[s]
                if s not in cleaned: cleaned.append(s)
            return cleaned[:300]  # Limit to 300 to avoid fails
    except: pass
    return default_list

# ======== V12 MARKET REGIME DETECTION - FIXED =========
def detect_market_regime(all_data, symbols):
    # 1. NIFTY TREND + ADX - FIXED MULTIINDEX
    df_n = yf.download("^NSEI", period="6mo", interval="1d", progress=False, auto_adjust=True)
    df_n = clean_df(df_n)
    
    df_n['EMA20'] = df_n['Close'].ewm(span=20).mean()
    df_n['EMA50'] = df_n['Close'].ewm(span=50).mean()
    df_n['EMA200'] = df_n['Close'].ewm(span=200).mean()
    df_n['ATR'] = (df_n['High'] - df_n['Low']).rolling(14).mean()
    df_n['ATR_PCT'] = df_n['ATR']/df_n['Close']*100
    
    # ADX
    df_n['TR'] = np.maximum(df_n['High']-df_n['Low'], np.maximum((df_n['High']-df_n['Close'].shift()).abs(), (df_n['Low']-df_n['Close'].shift()).abs()))
    df_n['DM+'] = np.where((df_n['High']-df_n['High'].shift()) > (df_n['Low'].shift()-df_n['Low']), np.maximum(df_n['High']-df_n['High'].shift(),0),0)
    df_n['DM-'] = np.where((df_n['Low'].shift()-df_n['Low']) > (df_n['High']-df_n['High'].shift()), np.maximum(df_n['Low'].shift()-df_n['Low'],0),0)
    df_n['ATR14'] = df_n['TR'].rolling(14).mean()
    df_n['DI+'] = 100*(pd.Series(df_n['DM+']).rolling(14).mean()/df_n['ATR14'])
    df_n['DI-'] = 100*(pd.Series(df_n['DM-']).rolling(14).mean()/df_n['ATR14'])
    df_n['DX'] = 100*(df_n['DI+']-df_n['DI-']).abs()/(df_n['DI+']+df_n['DI-'])
    df_n['ADX'] = df_n['DX'].rolling(14).mean()

    last = df_n.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50']); ema200 = float(last['EMA200'])
    atr_pct = float(last['ATR_PCT']); adx = float(last['ADX']) if not pd.isna(last['ADX']) else 20
    di_plus = float(last['DI+']); di_minus = float(last['DI-'])
    
    df_n['SMA20'] = df_n['Close'].rolling(20).mean()
    df_n['STD20'] = df_n['Close'].rolling(20).std()
    df_n['BB_UP'] = df_n['SMA20'] + 2*df_n['STD20']
    df_n['BB_LO'] = df_n['SMA20'] - 2*df_n['STD20']
    df_n['BB_WIDTH'] = (df_n['BB_UP']-df_n['BB_LO'])/df_n['SMA20']*100
    bb_width = float(df_n['BB_WIDTH'].iloc[-1])

    try:
        df_vix = yf.download("^INDIAVIX", period="1mo", interval="1d", progress=False, auto_adjust=True)
        df_vix = clean_df(df_vix)
        vix = float(df_vix['Close'].iloc[-1]) if len(df_vix)>0 else 15
        vix_trend = "HIGH" if vix>20 else "LOW" if vix<14 else "NORMAL"
    except:
        vix = 15; vix_trend="NORMAL"

    if vix>20 and price < ema20:
        pcr_proxy = 1.3
        pcr_signal = "OVERSOLD - REVERSAL EXPECTED (PCR~1.3)"
    elif vix<14 and price > ema20*1.03:
        pcr_proxy = 0.7
        pcr_signal = "OVERBOUGHT - CAUTION (PCR~0.7)"
    else:
        pcr_proxy = 1.0
        pcr_signal = "NEUTRAL (PCR~1.0)"

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

    if ema20 > ema50 > ema200 and adx > 22 and di_plus > di_minus and breadth > 60:
        regime = "TRENDING_BULL"
        desc = f"Strong Uptrend | ADX {adx:.0f} DI+{di_plus:.0f}>DI-{di_minus:.0f} | BB {bb_width:.1f}% | VIX {vix:.1f}"
        strategy = "Use: Bala WMA 8-20-50 + Trend + Breakout + Triple AVWAP"
        weights = {"trend":30,"bala_wma":35,"breakout":20,"sniper":10,"dip":5}
        min_win = 70
    elif adx < 20 and bb_width < 4 and 40 <= breadth <= 65:
        regime = "SIDEWAYS"
        desc = f"Sideways | ADX {adx:.0f} Low | BB {bb_width:.1f}% Squeeze | VIX {vix:.1f}"
        strategy = "Use: Near 8 EMA Dip + Triple AVWAP + RSI Range"
        weights = {"trend":10,"bala_wma":10,"breakout":5,"sniper":30,"dip":45}
        min_win = 75
    elif ema20 < ema50 and di_minus > di_plus and breadth < 45:
        regime = "DOWN_TREND"
        desc = f"Downtrend | ADX {adx:.0f} DI-{di_minus:.0f}>DI+{di_plus:.0f} | VIX {vix:.1f}"
        strategy = "AVOID LONGS | Wait Reversal"
        weights = {"trend":0,"bala_wma":0,"breakout":0,"sniper":0,"dip":0}
        min_win = 85
    else:
        regime = "MILD_BULL"
        desc = f"Mild Bull | ADX {adx:.0f} | BB {bb_width:.1f}% | VIX {vix:.1f} | Breadth {breadth:.0f}%"
        strategy = "Balanced All Strategies"
        weights = {"trend":20,"bala_wma":20,"breakout":20,"sniper":20,"dip":20}
        min_win = 68

    nifty_score = 0
    if price>ema20: nifty_score+=30
    if ema20>ema50: nifty_score+=30
    if adx>20: nifty_score+=20
    if breadth>60: nifty_score+=20

    return regime, nifty_score, price, breadth, desc, strategy, weights, min_win, vix, vix_trend, pcr_proxy, pcr_signal, adx, bb_width, ema20, ema50, ema200

def get_indices():
    indices_map = {"NIFTY":"^NSEI", "BANKNIFTY":"^NSEBANK", "FINNIFTY":"^CNXFIN", "IT":"^CNXIT", "VIX":"^INDIAVIX"}
    result = {}
    for name, ticker in indices_map.items():
        try:
            df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
            df = clean_df(df)
            if len(df)==0: continue
            last = df.iloc[-1]
            h = float(last['High']); l = float(last['Low']); c = float(last['Close'])
            pp = (h+l+c)/3; r1 = 2*pp - l; s1 = 2*pp - h; r2 = pp + (h-l); s2 = pp - (h-l)
            result[name] = {"price":c, "pp":pp, "s1":s1, "s2":s2, "r1":r1, "r2":r2}
        except: pass
    return result

def analyze(df, weights):
    df = clean_df(df)
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
    
    low_idx_20 = df['Low'].tail(20).idxmin()
    low_idx_50 = df['Low'].tail(50).idxmin()
    high_idx_20 = df['High'].tail(20).idxmax()
    avwap_low = calc_avwap(df, low_idx_20)
    avwap_50 = calc_avwap(df, low_idx_50)
    avwap_high = calc_avwap(df, high_idx_20)
    avwap = avwap_low
    
    delta = df['Close'].diff(); gain = delta.where(delta>0,0).rolling(14).mean(); loss = -delta.where(delta<0,0).rolling(14).mean(); rs = gain/loss
    rsi = float(100 - (100/(1+rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) and rs.iloc[-1]!=0 else 50

    vr = vol_now/vol20 if vol20>0 else 1
    trend_score = 50 if price>ema20 else 0
    if ema20>ema50: trend_score+=50
    bala_wma_score = 100 if (wma8 > wma20 > wma50 and price > wma8) else (50 if wma8>wma20 else 0)
    dip_score = 100 if abs(price-ema8)/price*100<=1 else 80 if abs(price-ema8)/price*100<=2.5 else 50 if abs(price-ema8)/price*100<=4 else 0
    if 35 <= rsi <= 55: dip_score = min(100, dip_score+20)

    if price > avwap_high and price > avwap_low and vr>1.2: sniper_score = 100
    elif price > avwap_low and price > ema20 and vr>1.0: sniper_score = 80
    elif price > avwap_low * 0.99: sniper_score = 60
    elif price > avwap_low: sniper_score = 50
    else: sniper_score = 0

    if price>=high20*0.995 and vr>1.5: breakout_score=100
    elif price>=high20*0.98 and vr>1.2: breakout_score=70
    elif price>=high20*0.97: breakout_score=40
    else: breakout_score=0

    composite = (trend_score*weights['trend'] + bala_wma_score*weights['bala_wma'] + breakout_score*weights['breakout'] + sniper_score*weights['sniper'] + dip_score*weights['dip'])/100

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
    zone = "🟢 DEEP DIP" if price <= s1*1.01 else "🟡 NEAR SUPPORT" if price <= pp else "🔵 ABOVE PP" if price <= r1 else "🔴 NEAR R1/R2"
    return {"price":price,"entry":entry,"entry_low":entry_low,"entry_high":entry_high,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"pp":pp,"r1":r1,"r2":r2,"s1":s1,"s2":s2,"risk":risk,"rr1":rr1,"rr2":rr2,"win":winp,"avwap":avwap,"avwap_low":avwap_low,"avwap_50":avwap_50,"avwap_high":avwap_high,"rsi":rsi,"sniper":sniper_score>=70,"breakout":breakout_score>=70,"trend":trend_score>=50,"weight":weight,"bala_wma":bala_wma_score>=100,"wma8":wma8,"wma20":wma20,"wma50":wma50,"ema8":ema8,"composite":composite,"zone":zone,"scores":{"trend":trend_score,"bala":bala_wma_score,"dip":dip_score,"sniper":sniper_score,"break":breakout_score}}

def main():
    symbols = load_nifty500()
    symbols_ns = [s+".NS" for s in symbols]
    # FIX: ignore failed downloads, use threads but don't crash
    all_data = yf.download(symbols_ns, period="3mo", interval="1d", progress=False, auto_adjust=True, group_by='ticker', threads=True, ignore_tz=True)
    regime, nscore, nprice, breadth, desc, strategy, weights, min_win, vix, vix_trend, pcr_proxy, pcr_signal, adx, bb_width, ema20, ema50, ema200 = detect_market_regime(all_data, symbols)
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

    top_hybrid = sorted(all_picks, key=lambda x:(x['composite'], x['win']), reverse=True)[:10]
    top3 = sorted(all_picks, key=lambda x:x['weight'], reverse=True)[:3]
    for idx, p in enumerate(top3):
        allocs = [40,35,25] if regime=="TRENDING_BULL" else [33,33,34]
        p['alloc_pct'] = allocs[idx] if idx<3 else 33
        p['alloc_value'] = CAPITAL * p['alloc_pct']/100
        p['qty'] = max(1, min(int(CAPITAL*0.015/p['risk']) if p['risk']>0 else 1, int(p['alloc_value']/p['price'])))

    msg = f"🤖 MASTER BOT V12.1 FIXED MARKET REGIME - {date.today()}\n"
    msg += f"📈 MARKET TYPE: {regime}\n{desc}\n🎯 {strategy}\n"
    msg += f"NIFTY {nprice:.0f} Score:{nscore} EMA20 {ema20:.0f} 50 {ema50:.0f} 200 {ema200:.0f}\n"
    msg += f"ADX {adx:.0f} BB {bb_width:.1f}% Breadth {breadth:.0f}% VIX {vix:.1f} ({vix_trend}) PCR {pcr_proxy} {pcr_signal}\n"
    msg += f"⚖️ W:T{weights['trend']}% B{weights['bala_wma']}% Br{weights['breakout']}% S{weights['sniper']}% D{weights['dip']}% MinWin {min_win}% | {len(all_picks)} stocks\n\n"
    for name, d in indices.items():
        msg += f"{name} {d['price']:.0f} S2:{d['s2']:.0f} S1:{d['s1']:.0f} PP:{d['pp']:.0f} R1:{d['r1']:.0f} R2:{d['r2']:.0f}\n"
    msg += f"\n🏆 TOP 10:\n"
    for i,p in enumerate(top_hybrid,1):
        msg += f"{i}. {p['sym']} Comp:{p['composite']:.0f} Win:{p['win']}% RSI:{p['rsi']:.0f} E:{p['entry']:.0f} {p['zone']} AVWAP {p['avwap_low']:.0f}\n"
    msg += f"\n💎 TOP 3 TRADE:\n"
    for i,p in enumerate(top3,1):
        tags = []
        if p['bala_wma']: tags.append("BALA")
        if p['sniper']: tags.append("SNIPER")
        if p['breakout']: tags.append("BREAK")
        tag_str = f"[{','.join(tags)}]" if tags else ""
        msg += f"\n{i}. {p['sym']} {tag_str} Comp:{p['composite']:.0f} Win:{p['win']}% RSI:{p['rsi']:.0f} QTY:{p['qty']} ({p['alloc_pct']:.0f}%) {p['zone']}\n"
        msg += f"   ENTRY: {p['entry_low']:.0f}-{p['entry_high']:.0f} CMP:{p['entry']:.0f} T1:{p['t1']:.0f} RR{ p['rr1']:.1f} T2:{p['t2']:.0f} RR{ p['rr2']:.1f} SL:{p['sl']:.0f}\n"
        msg += f"   S/R: S2:{p['s2']:.0f} S1:{p['s1']:.0f} PP:{p['pp']:.0f} R1:{p['r1']:.0f} R2:{p['r2']:.0f} AVWAP 20D:{p['avwap_low']:.0f} 50D:{p['avwap_50']:.0f}\n"
    print(msg)
    send_telegram(msg)

if __name__=="__main__":
    main()
