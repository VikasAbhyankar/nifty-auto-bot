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

def get_clean_data(ticker, period="3mo"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
        if df.empty: return None
        # Handle MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            # Try to flatten
            try:
                df.columns = df.columns.get_level_values(0)
            except:
                df = df.droplevel(1, axis=1) if len(df.columns.levels)>1 else df
        df = df.loc[:, ~df.columns.duplicated()]
        # Ensure Close exists
        if 'Close' not in df.columns and 'Adj Close' in df.columns:
            df['Close'] = df['Adj Close']
        return df
    except:
        return None

def calc_avwap(df, anchor_idx):
    try:
        ds = df.loc[anchor_idx:]
        return float(((ds['Close']*ds['Volume']).cumsum() / ds['Volume'].cumsum()).iloc[-1])
    except: return float(df['Close'].ewm(span=20).mean().iloc[-1])

def load_nifty500():
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","BAJFINANCE","ITC","BSE","BHARTIHEXA","LTTS","HCLTECH","SHYAMMETL","WIPRO","COFORGE","TECHM","PERSISTENT","TITAN","M&M","HINDALCO","DIVISLAB","INDHOTEL","HAL","BANKBARODA","PNB","CIPLA","FDC","FSL","SYNGENE","TANLA","UNIONBANK","DRREDDY","TATAELXSI","JSWSTEEL","IOC","ULTRACEMCO","ETERNAL","ZENSAR","INDUSINDBK","KALYANKJIL","WABAG"]

def detect_market_regime():
    # SINGLE DOWNLOAD - NO GROUP BY - NO CRASH
    df_n = get_clean_data("^NSEI", "6mo")
    if df_n is None or len(df_n)<50:
        # Fallback defaults
        return "TRENDING_BULL", 80, 25000, 65, "Fallback Bull", "Bala+Trend", {"trend":30,"bala_wma":35,"breakout":20,"sniper":10,"dip":5}, 70, 15, "NORMAL", 1.0, "NEUTRAL", 25, 5, 24500, 24000, 22000
    
    df_n['EMA20'] = df_n['Close'].ewm(span=20).mean()
    df_n['EMA50'] = df_n['Close'].ewm(span=50).mean()
    df_n['EMA200'] = df_n['Close'].ewm(span=200).mean()
    df_n['ATR'] = (df_n['High'] - df_n['Low']).rolling(14).mean()
    df_n['ATR_PCT'] = df_n['ATR']/df_n['Close']*100
    df_n['TR'] = (df_n['High']-df_n['Low']).abs()
    df_n['SMA20'] = df_n['Close'].rolling(20).mean()
    df_n['STD20'] = df_n['Close'].rolling(20).std()
    df_n['BB_WIDTH'] = (df_n['SMA20']+2*df_n['STD20'] - (df_n['SMA20']-2*df_n['STD20']))/df_n['SMA20']*100
    
    # ADX Simplified
    df_n['UpMove'] = df_n['High'] - df_n['High'].shift(1)
    df_n['DownMove'] = df_n['Low'].shift(1) - df_n['Low']
    df_n['DM+'] = np.where((df_n['UpMove']>df_n['DownMove']) & (df_n['UpMove']>0), df_n['UpMove'], 0)
    df_n['DM-'] = np.where((df_n['DownMove']>df_n['UpMove']) & (df_n['DownMove']>0), df_n['DownMove'], 0)
    df_n['DI+'] = 100*(pd.Series(df_n['DM+']).rolling(14).mean() / df_n['ATR'])
    df_n['DI-'] = 100*(pd.Series(df_n['DM-']).rolling(14).mean() / df_n['ATR'])
    df_n['DX'] = 100*((df_n['DI+']-df_n['DI-']).abs()/(df_n['DI+']+df_n['DI-']).replace(0,1))
    df_n['ADX'] = df_n['DX'].rolling(14).mean()

    last = df_n.iloc[-1]
    price = float(last['Close']); ema20 = float(last['EMA20']); ema50 = float(last['EMA50']); ema200 = float(last['EMA200'])
    adx = float(last['ADX']) if not pd.isna(last['ADX']) else 22
    di_plus = float(last['DI+']); di_minus = float(last['DI-'])
    bb_width = float(last['BB_WIDTH'])
    
    # VIX
    try:
        df_vix = get_clean_data("^INDIAVIX", "1mo")
        vix = float(df_vix['Close'].iloc[-1]) if df_vix is not None and len(df_vix)>0 else 15
    except: vix=15
    vix_trend = "HIGH" if vix>20 else "LOW" if vix<14 else "NORMAL"
    
    if vix>20 and price<ema20: pcr_proxy, pcr_signal = 1.3, "OVERSOLD REVERSAL"
    elif vix<14 and price>ema20*1.03: pcr_proxy, pcr_signal = 0.7, "OVERBOUGHT CAUTION"
    else: pcr_proxy, pcr_signal = 1.0, "NEUTRAL"
    
    # Breadth - simple calc from few stocks to avoid heavy download
    breadth = 65  # default, will be updated later if possible

    if ema20>ema50>ema200 and adx>22 and di_plus>di_minus and price>ema20:
        regime, desc, strategy = "TRENDING_BULL", f"Strong Uptrend ADX {adx:.0f} DI+{di_plus:.0f}>DI-{di_minus:.0f} BB {bb_width:.1f}% VIX {vix:.1f}", "Bala WMA + Trend + Breakout + Triple AVWAP"
        weights, min_win = {"trend":30,"bala_wma":35,"breakout":20,"sniper":10,"dip":5}, 70
    elif adx<20 and bb_width<4:
        regime, desc, strategy = "SIDEWAYS", f"Sideways ADX {adx:.0f} Low BB {bb_width:.1f}% VIX {vix:.1f}", "8EMA Dip + Triple AVWAP + RSI"
        weights, min_win = {"trend":10,"bala_wma":10,"breakout":5,"sniper":30,"dip":45}, 75
    elif ema20<ema50 and di_minus>di_plus:
        regime, desc, strategy = "DOWN_TREND", f"Downtrend ADX {adx:.0f} VIX {vix:.1f}", "AVOID LONGS"
        weights, min_win = {"trend":0,"bala_wma":0,"breakout":0,"sniper":0,"dip":0}, 85
    else:
        regime, desc, strategy = "MILD_BULL", f"Mild Bull ADX {adx:.0f} BB {bb_width:.1f}% VIX {vix:.1f}", "Balanced"
        weights, min_win = {"trend":20,"bala_wma":20,"breakout":20,"sniper":20,"dip":20}, 68
    
    nscore = (30 if price>ema20 else 0)+(30 if ema20>ema50 else 0)+(20 if adx>20 else 0)+20
    return regime, nscore, price, breadth, desc, strategy, weights, min_win, vix, vix_trend, pcr_proxy, pcr_signal, adx, bb_width, ema20, ema50, ema200

def get_indices():
    result={}
    for name,ticker in {"NIFTY":"^NSEI","BANKNIFTY":"^NSEBANK","FINNIFTY":"^CNXFIN","IT":"^CNXIT","VIX":"^INDIAVIX"}.items():
        df = get_clean_data(ticker, "5d")
        if df is None or len(df)==0: continue
        last=df.iloc[-1]; h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
        pp=(h+l+c)/3; result[name]={"price":c,"pp":pp,"s1":2*pp-h,"s2":pp-(h-l),"r1":2*pp-l,"r2":pp+(h-l)}
    return result

def analyze(df, weights):
    df['EMA8']=df['Close'].ewm(span=8).mean(); df['EMA20']=df['Close'].ewm(span=20).mean(); df['EMA50']=df['Close'].ewm(span=50).mean()
    df['WMA8']=wma(df['Close'],8); df['WMA20']=wma(df['Close'],20); df['WMA50']=wma(df['Close'],50)
    df['High20']=df['High'].rolling(20).max(); df['Vol20']=df['Volume'].rolling(20).mean(); df['ATR']=(df['High']-df['Low']).rolling(14).mean()
    last=df.iloc[-1]
    if pd.isna(last['EMA20']) or pd.isna(last['Vol20']): return None
    price=float(last['Close']); ema8=float(last['EMA8']); ema20=float(last['EMA20']); ema50=float(last['EMA50'])
    wma8=float(last['WMA8']); wma20=float(last['WMA20']); wma50=float(last['WMA50']); high20=float(last['High20'])
    vol20=float(last['Vol20']); vol_now=float(last['Volume']); atr=float(last['ATR'])
    h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
    pp=(h+l+c)/3; r1=2*pp-l; s1=2*pp-h; r2=pp+(h-l); s2=pp-(h-l)
    low20=df['Low'].tail(20).idxmin(); low50=df['Low'].tail(50).idxmin(); high20_idx=df['High'].tail(20).idxmax()
    avwap_low=calc_avwap(df,low20); avwap_50=calc_avwap(df,low50); avwap_high=calc_avwap(df,high20_idx)
    delta=df['Close'].diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean(); rs=gain/loss
    rsi=float(100-(100/(1+rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) and rs.iloc[-1]!=0 else 50
    vr=vol_now/vol20 if vol20>0 else 1
    trend_score=(50 if price>ema20 else 0)+(50 if ema20>ema50 else 0)
    bala_wma_score=100 if (wma8>wma20>wma50 and price>wma8) else (50 if wma8>wma20 else 0)
    dip_score=100 if abs(price-ema8)/price*100<=1 else 80 if abs(price-ema8)/price*100<=2.5 else 50 if abs(price-ema8)/price*100<=4 else 0
    if 35<=rsi<=55: dip_score=min(100,dip_score+20)
    if price>avwap_high and price>avwap_low and vr>1.2: sniper_score=100
    elif price>avwap_low and price>ema20 and vr>1.0: sniper_score=80
    elif price>avwap_low*0.99: sniper_score=60
    elif price>avwap_low: sniper_score=50
    else: sniper_score=0
    breakout_score=100 if price>=high20*0.995 and vr>1.5 else 70 if price>=high20*0.98 and vr>1.2 else 40 if price>=high20*0.97 else 0
    composite=(trend_score*weights['trend']+bala_wma_score*weights['bala_wma']+breakout_score*weights['breakout']+sniper_score*weights['sniper']+dip_score*weights['dip'])/100
    entry=price; t1=price+1.5*atr; t2=price+3.0*atr; sl=max(ema20,price-1.2*atr)
    entry_low=max(ema20,price-0.4*atr); entry_high=price+0.3*atr; risk=price-sl; rr1=(t1-price)/risk if risk>0 else 0; rr2=(t2-price)/risk if risk>0 else 0
    wins=tot=0
    for i in range(20,len(df)-5):
        if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA20'].iloc[i]>df['EMA50'].iloc[i]:
            tot+=1
            if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i]): wins+=1
    winp=int(wins/tot*100) if tot>0 else 50; winp=min(95,max(45,winp+(composite-50)//2)); weight=winp*composite*(1+rr1)*(1+vr/3)
    zone="🟢 DEEP DIP" if price<=s1*1.01 else "🟡 NEAR SUPPORT" if price<=pp else "🔵 ABOVE PP" if price<=r1 else "🔴 NEAR R1/R2"
    return {"price":price,"entry":entry,"entry_low":entry_low,"entry_high":entry_high,"vr":vr,"t1":t1,"t2":t2,"sl":sl,"pp":pp,"r1":r1,"r2":r2,"s1":s1,"s2":s2,"risk":risk,"rr1":rr1,"rr2":rr2,"win":winp,"avwap":avwap_low,"avwap_low":avwap_low,"avwap_50":avwap_50,"avwap_high":avwap_high,"rsi":rsi,"sniper":sniper_score>=70,"breakout":breakout_score>=70,"trend":trend_score>=50,"weight":weight,"bala_wma":bala_wma_score>=100,"wma8":wma8,"wma20":wma20,"wma50":wma50,"ema8":ema8,"composite":composite,"zone":zone,"scores":{"trend":trend_score,"bala":bala_wma_score,"dip":dip_score,"sniper":sniper_score,"break":breakout_score}}

def main():
    symbols=load_nifty500()
    regime,nscore,nprice,breadth,desc,strategy,weights,min_win,vix,vix_trend,pcr_proxy,pcr_signal,adx,bb_width,ema20,ema50,ema200 = detect_market_regime()
    indices=get_indices()
    
    # Breadth from quick sample
    try:
        sample = symbols[:50]
        above=0; tot=0
        for sym in sample:
            df = get_clean_data(sym+".NS", "1mo")
            if df is None or len(df)<20: continue
            df['EMA20']=df['Close'].ewm(span=20).mean()
            if float(df['Close'].iloc[-1])>float(df['EMA20'].iloc[-1]): above+=1
            tot+=1
        if tot>0: breadth=above/tot*100
    except: pass

    all_picks=[]
    for sym in symbols:
        try:
            df = get_clean_data(sym+".NS", "3mo")
            if df is None or len(df)<30: continue
            res=analyze(df,weights)
            if res and res['composite']>=60 and res['win']>=min_win:
                all_picks.append({"sym":sym,**res})
        except: continue

    top_hybrid=sorted(all_picks,key=lambda x:(x['composite'],x['win']),reverse=True)[:10]
    top3=sorted(all_picks,key=lambda x:x['weight'],reverse=True)[:3]
    for idx,p in enumerate(top3):
        p['alloc_pct']=[40,35,25][idx] if idx<3 else 33
        p['alloc_value']=CAPITAL*p['alloc_pct']/100
        p['qty']=max(1,min(int(CAPITAL*0.015/p['risk']) if p['risk']>0 else 1,int(p['alloc_value']/p['price'])))

    msg=f"🤖 MASTER BOT V12.2 ULTRA FIXED - {date.today()}\n📈 MARKET TYPE: {regime}\n{desc}\n🎯 {strategy}\nNIFTY {nprice:.0f} Score:{nscore} EMA20 {ema20:.0f} 50 {ema50:.0f} 200 {ema200:.0f}\nADX {adx:.0f} BB {bb_width:.1f}% Breadth {breadth:.0f}% VIX {vix:.1f} ({vix_trend}) PCR {pcr_proxy} {pcr_signal}\n⚖️ W:T{weights['trend']}% B{weights['bala_wma']}% Br{weights['breakout']}% S{weights['sniper']}% D{weights['dip']}% MinWin {min_win}% | {len(all_picks)} stocks\n\n"
    for name,d in indices.items(): msg+=f"{name} {d['price']:.0f} S2:{d['s2']:.0f} S1:{d['s1']:.0f} PP:{d['pp']:.0f} R1:{d['r1']:.0f} R2:{d['r2']:.0f}\n"
    msg+=f"\n🏆 TOP 10:\n"
    for i,p in enumerate(top_hybrid,1): msg+=f"{i}. {p['sym']} Comp:{p['composite']:.0f} Win:{p['win']}% RSI:{p['rsi']:.0f} E:{p['entry']:.0f} {p['zone']} AVWAP {p['avwap_low']:.0f}\n"
    msg+=f"\n💎 TOP 3 TRADE:\n"
    for i,p in enumerate(top3,1):
        tags=[]; 
        if p['bala_wma']: tags.append("BALA")
        if p['sniper']: tags.append("SNIPER")
        if p['breakout']: tags.append("BREAK")
        tag_str=f"[{','.join(tags)}]" if tags else ""
        msg+=f"\n{i}. {p['sym']} {tag_str} Comp:{p['composite']:.0f} Win:{p['win']}% RSI:{p['rsi']:.0f} QTY:{p['qty']} ({p['alloc_pct']:.0f}%) {p['zone']}\n   ENTRY: {p['entry_low']:.0f}-{p['entry_high']:.0f} CMP:{p['entry']:.0f} T1:{p['t1']:.0f} RR{ p['rr1']:.1f} T2:{p['t2']:.0f} RR{ p['rr2']:.1f} SL:{p['sl']:.0f}\n   S/R: S2:{p['s2']:.0f} S1:{p['s1']:.0f} PP:{p['pp']:.0f} R1:{p['r1']:.0f} R2:{p['r2']:.0f} AVWAP 20D:{p['avwap_low']:.0f} 50D:{p['avwap_50']:.0f}\n"
    print(msg); send_telegram(msg)

if __name__=="__main__": main()
