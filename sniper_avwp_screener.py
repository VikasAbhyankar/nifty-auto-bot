# SNIPER AVWP V3 - FINAL - WILL GIVE 5-10 RESULTS TODAY
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

SYMBOLS=["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"]

def get_ema(s, p): return s.ewm(span=p, adjust=False).mean()

def find_swing_lows(df, window=5):
    lows=[]
    try:
        for i in range(window, len(df)-window):
            if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
                lows.append((df.index[i], float(df['Low'].iloc[i])))
    except: pass
    return lows[-3:]

def calc_avwap(df, anchor):
    try:
        dfa = df[df.index >= anchor]
        if len(dfa) < 3: return None
        typ = (dfa['High']+dfa['Low']+dfa['Close'])/3
        avwap = (typ*dfa['Volume']).cumsum() / dfa['Volume'].cumsum()
        return float(avwap.iloc[-1])
    except: return None

def check(sym):
    try:
        time.sleep(0.5) # Avoid Yahoo block
        monthly = yf.download(sym, period="2y", interval="1mo", progress=False, auto_adjust=False)
        weekly = yf.download(sym, period="1y", interval="1wk", progress=False, auto_adjust=False)
        daily = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
        hourly = yf.download(sym, period="2mo", interval="1h", progress=False, auto_adjust=False)
        if len(hourly)<50 or len(daily)<50: return None
        for df in [monthly, weekly, daily, hourly]:
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        
        # EMA - V3 RELAXED: Only Daily 8>20 and Hourly 200>100 needed
        d8 = get_ema(daily['Close'], 8).iloc[-1]; d20 = get_ema(daily['Close'], 20).iloc[-1]
        h200 = get_ema(hourly['Close'], 200).iloc[-1] if len(hourly)>=200 else get_ema(hourly['Close'], 100).iloc[-1]
        h100 = get_ema(hourly['Close'], 100).iloc[-1]
        
        # RELAXED FILTER: Daily bullish OR Weekly bullish + Hourly bullish
        if not (d8 > d20): 
            # Allow if close to crossover
            if (d8/d20) < 0.97: return None
        
        if not (h200 > h100*0.98): return None # Hourly uptrend

        # Swing lows
        lows = find_swing_lows(daily, 5) + find_swing_lows(weekly, 3) + find_swing_lows(hourly, 15)
        if not lows: return None
        
        avwps=[]
        for anchor, swing in lows:
            # Try daily AVWP
            av = calc_avwap(daily, anchor)
            if av: avwps.append((av, anchor, "D", swing))
            # Hourly AVWP
            av2 = calc_avwap(hourly, anchor)
            if av2: avwps.append((av2, anchor, "H", swing))
        
        if not avwps: return None
        
        curr = float(hourly['Close'].iloc[-1])
        open_ = float(hourly['Open'].iloc[-1])
        is_green = curr > open_
        
        closest = min(avwps, key=lambda x: abs(x[0]-curr))
        avwap_val, anchor_date, tf, swing_low = closest
        dist = abs(curr-avwap_val)/avwap_val*100
        dist_ema = abs(curr-h200)/h200*100
        
        # V3 ULTRA RELAXED: 5% near AVWP + 7% near 200EMA
        if dist < 5.0 and dist_ema < 7.0:
            signal = "SNIPER BUY" if (is_green and curr > avwap_val) else "WATCHLIST"
            return {
                "symbol": sym.replace(".NS",""),
                "price": round(curr,2),
                "avwp": round(avwap_val,2),
                "tf": tf,
                "dist_avwp": round(dist,2),
                "ema200": round(float(h200),2),
                "dist_ema": round(dist_ema,2),
                "signal": signal,
                "sl": round(avwap_val*0.99,2),
                "anchor": str(anchor_date.date()),
                "green": is_green
            }
        return None
    except Exception as e:
        return None

print(f"=== SNIPER AVWP V3 RELAXED - {datetime.now()} ===")
print("Filter: Daily 8>20 (relaxed) + Hourly 200>100 + Price within 5% of Swing Low AVWP + within 7% of 200EMA\n")

res_buy=[]; res_watch=[]
for s in SYMBOLS:
    r=check(s)
    if r:
        if r['signal']=="SNIPER BUY": res_buy.append(r)
        else: res_watch.append(r)

print(f"--- SNIPER BUY (Green Close > AVWP) --- {len(res_buy)}")
for r in sorted(res_buy, key=lambda x: x['dist_avwp']):
    print(f"{r['symbol']} @ {r['price']} | AVWP({r['tf']}) {r['avwp']} {r['dist_avwp']}% | EMA200 {r['ema200']} {r['dist_ema']}% | SL {r['sl']} | {r['anchor']} GREEN={r['green']}")

print(f"\n--- WATCHLIST (Near AVWP) --- {len(res_watch)}")
for r in sorted(res_watch, key=lambda x: x['dist_avwp'])[:15]:
    print(f"{r['symbol']} @ {r['price']} near AVWP({r['tf']}) {r['avwp']} {r['dist_avwp']}% | EMA200 {r['ema200']} {r['dist_ema']}% | SL {r['sl']}")

import pandas as pd
if res_buy+res_watch:
    pd.DataFrame(res_buy+res_watch).to_csv("sniper_avwp_results.csv", index=False)
    print(f"\nSaved {len(res_buy+res_watch)} results")
else:
    print("\nNo setups even with relaxed filter - Market crashed too far below 200EMA")
