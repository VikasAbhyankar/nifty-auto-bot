# SNIPER AVWP SCREENER V1.0 - Monthly/Weekly/Daily/Hourly Swing Low AVWP + EMA
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

SYMBOLS=["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","LTIM.NS","PIDILITIND.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"]

def get_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def find_swing_lows(df, window=5):
    """Find swing lows - pivot low"""
    lows=[]
    for i in range(window, len(df)-window):
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            lows.append((df.index[i], float(df['Low'].iloc[i])))
    return lows[-5:]  # last 5 swing lows

def find_swing_highs(df, window=5):
    highs=[]
    for i in range(window, len(df)-window):
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            highs.append((df.index[i], float(df['High'].iloc[i])))
    return highs[-5:]

def calc_avwap(df, anchor_date):
    """Anchored VWAP from anchor date"""
    try:
        df_anchor = df[df.index >= anchor_date]
        if len(df_anchor) < 5: return None
        typical = (df_anchor['High']+df_anchor['Low']+df_anchor['Close'])/3
        pv = typical * df_anchor['Volume']
        avwap = pv.cumsum() / df_anchor['Volume'].cumsum()
        return float(avwap.iloc[-1]), anchor_date
    except: return None

def check_sniper(symbol):
    try:
        # Download multi timeframe
        monthly = yf.download(symbol, period="3y", interval="1mo", progress=False, auto_adjust=False)
        weekly = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=False)
        daily = yf.download(symbol, period="1y", interval="1d", progress=False, auto_adjust=False)
        hourly = yf.download(symbol, period="3mo", interval="1h", progress=False, auto_adjust=False)

        if len(monthly)<10 or len(weekly)<30 or len(daily)<100 or len(hourly)<200:
            return None
        for df in [monthly, weekly, daily, hourly]:
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)

        # EMA Checks
        w8 = get_ema(weekly['Close'], 8).iloc[-1]; w20 = get_ema(weekly['Close'], 20).iloc[-1]
        d8 = get_ema(daily['Close'], 8).iloc[-1]; d20 = get_ema(daily['Close'], 20).iloc[-1]
        h200 = get_ema(hourly['Close'], 200).iloc[-1]; h400 = get_ema(hourly['Close'], 400).iloc[-1] if len(hourly)>=400 else get_ema(hourly['Close'], 200).iloc[-1]*0.99
        
        # CONDITION 1: Trend Filters
        if not (w8 > w20): return None
        if not (d8 > d20): return None
        if not (h200 > h400): return None

        # Find Swing Lows
        m_lows = find_swing_lows(monthly, 2)
        w_lows = find_swing_lows(weekly, 3)
        d_lows = find_swing_lows(daily, 5)
        h_lows = find_swing_lows(hourly, 10)

        all_lows = []
        for lows, df, tf in [(m_lows, monthly, "M"), (w_lows, weekly, "W"), (d_lows, daily, "D"), (h_lows, hourly, "H")]:
            for anchor_date, swing_price in lows:
                avwap_res = calc_avwap(df if tf!="H" else hourly, anchor_date)
                if avwap_res:
                    avwap_val, _ = avwap_res
                    all_lows.append({"tf":tf, "anchor":anchor_date, "swing":swing_price, "avwap":avwap_val})

        if not all_lows: return None

        # Current hourly price
        last_hour = hourly.iloc[-1]
        curr_price = float(last_hour['Close'])
        curr_open = float(last_hour['Open'])
        curr_low = float(last_hour['Low'])
        is_green = curr_price > curr_open

        # Check near Hourly 200/400 EMA (within 2.5%)
        near_ema200 = abs(curr_price - h200)/h200*100 < 2.5
        near_ema400 = abs(curr_price - h400)/h400*100 < 3.5
        near_ema = near_ema200 or near_ema400

        # Find closest AVWP
        closest = min(all_lows, key=lambda x: abs(x['avwap']-curr_price))
        dist_avwp = abs(curr_price - closest['avwap'])/closest['avwap']*100

        # SNIPER CONDITIONS
        # 1. Price near AVWP (<1.5%)
        # 2. Price near 200/400 EMA
        # 3. Green candle closing above AVWP
        if dist_avwp < 1.5 and near_ema:
            # Entry trigger: green candle close above low avwp
            if is_green and curr_price > closest['avwap'] and curr_low <= closest['avwap']:
                return {
                    "symbol": symbol.replace(".NS",""),
                    "price": round(curr_price,2),
                    "entry_avwp": round(closest['avwap'],2),
                    "avwp_tf": closest['tf'],
                    "anchor": str(closest['anchor'].date()),
                    "swing_low": round(closest['swing'],2),
                    "dist_avwp": round(dist_avwp,2),
                    "h200": round(float(h200),2),
                    "h400": round(float(h400),2),
                    "dist_ema200": round(abs(curr_price-h200)/h200*100,2),
                    "d8>d20": f"{float(d8):.0f}>{float(d20):.0f}",
                    "w8>w20": f"{float(w8):.0f}>{float(w20):.0f}",
                    "signal": "SNIPER BUY",
                    "sl": round(closest['avwap']*0.995,2), # Close below AVWP = SL
                    "is_green": is_green
                }
            # Watchlist - near AVWP but not yet green close
            elif dist_avwp < 1.5:
                return {
                    "symbol": symbol.replace(".NS",""),
                    "price": round(curr_price,2),
                    "entry_avwp": round(closest['avwap'],2),
                    "avwp_tf": closest['tf'],
                    "dist_avwp": round(dist_avwp,2),
                    "h200": round(float(h200),2),
                    "signal": "WATCHLIST - Wait Green Close",
                    "sl": round(closest['avwap']*0.995,2),
                }
        return None
    except Exception as e:
        # print(f"{symbol} error {e}")
        return None

print("=== SNIPER AVWP SCREENER - Scanning 54 stocks ===")
print(f"Time: {datetime.now()}")
print("Conditions: Weekly 8>20 + Daily 8>20 + Hourly 200>400 + Price near Swing Low AVWP + Near 200/400 EMA\n")

results=[]
watchlist=[]
for sym in SYMBOLS:
    res = check_sniper(sym)
    if res:
        if "BUY" in res['signal']:
            results.append(res)
        else:
            watchlist.append(res)

print(f"\n--- SNIPER BUY SIGNALS (Green Candle Closed Above Low AVWP) --- {len(results)} found")
for r in sorted(results, key=lambda x: x['dist_avwp']):
    print(f"{r['symbol']} @ {r['price']} | AVWP({r['avwp_tf']}) {r['entry_avwp']} dist {r['dist_avwp']}% | 200EMA {r['h200']} dist {r['dist_ema200']}% | SL {r['sl']} | Anchor {r['anchor']}")

print(f"\n--- WATCHLIST (Near AVWP, wait for Green close) --- {len(watchlist)} found")
for r in sorted(watchlist, key=lambda x: x['dist_avwp'])[:10]:
    print(f"{r['symbol']} @ {r['price']} near AVWP({r['avwp_tf']}) {r['entry_avwp']} dist {r['dist_avwp']}% | SL {r['sl']}")

# Save
df_all = pd.DataFrame(results+watchlist)
if len(df_all)>0:
    df_all.to_csv("sniper_avwp_results.csv", index=False)
    print(f"\nSaved to sniper_avwp_results.csv - Total {len(df_all)}")
else:
    print("\nNo Sniper setups today - Market in pullback wait?")
