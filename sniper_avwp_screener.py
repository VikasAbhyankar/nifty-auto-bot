# SNIPER AVWP V4 - WITH TELEGRAM ALERT
import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("No Telegram secrets, skipping")
        print(msg)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        # Split long messages (Telegram limit 4096)
        for i in range(0, len(msg), 4000):
            chunk = msg[i:i+4000]
            r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"}, timeout=20)
            print(f"Telegram sent {r.status_code}")
    except Exception as e:
        print(f"Telegram error {e}")

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
        time.sleep(0.4)
        daily = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
        hourly = yf.download(sym, period="2mo", interval="1h", progress=False, auto_adjust=False)
        if len(hourly)<60 or len(daily)<50: return None
        for df in [daily, hourly]:
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        
        d8 = get_ema(daily['Close'], 8).iloc[-1]; d20 = get_ema(daily['Close'], 20).iloc[-1]
        h200 = get_ema(hourly['Close'], 200).iloc[-1] if len(hourly)>=200 else get_ema(hourly['Close'], 100).iloc[-1]
        h100 = get_ema(hourly['Close'], 100).iloc[-1]
        
        if not (d8 > d20 or d8/d20 > 0.97): return None
        if not (h200 > h100*0.98): return None

        lows = find_swing_lows(daily, 5) + find_swing_lows(hourly, 15)
        if not lows: return None
        
        avwps=[]
        for anchor, swing in lows:
            av = calc_avwap(daily, anchor)
            if av and av > swing*0.7 and av < swing*1.3: # Valid AVWP near swing
                avwps.append((av, anchor, "D", swing))
            av2 = calc_avwap(hourly, anchor)
            if av2 and av2 > swing*0.7 and av2 < swing*1.3:
                avwps.append((av2, anchor, "H", swing))
        
        if not avwps: return None
        
        curr = float(hourly['Close'].iloc[-1])
        open_ = float(hourly['Open'].iloc[-1])
        is_green = curr > open_
        
        closest = min(avwps, key=lambda x: abs(x[0]-curr))
        avwap_val, anchor_date, tf, swing_low = closest
        dist = abs(curr-avwap_val)/avwap_val*100
        dist_ema = abs(curr-h200)/h200*100
        
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
                "tgt1": round(curr*1.02,2),
                "tgt2": round(curr*1.035,2),
                "anchor": str(anchor_date.date()),
                "green": is_green
            }
        return None
    except: return None

print(f"=== SNIPER AVWP V4 TELEGRAM - {datetime.now()} ===")
res_buy=[]; res_watch=[]
for s in SYMBOLS:
    r=check(s)
    if r:
        if r['signal']=="SNIPER BUY": res_buy.append(r)
        else: res_watch.append(r)

# Build Telegram Message
msg = f"""🎯 *SNIPER AVWP SCREENER - {datetime.now().strftime('%d-%b %Y %H:%M')}*
Trend: Daily 8>20 + Hourly 200>100 + Swing Low AVWP

*--- SNIPER BUY (Green Close > AVWP) - {len(res_buy)} ---*
"""
if res_buy:
    for r in sorted(res_buy, key=lambda x: x['dist_avwp']):
        msg += f"\n✅ *{r['symbol']}* @ {r['price']} | AVWP({r['tf']}) {r['avwp']} ({r['dist_avwp']}%)\n   EMA200 {r['ema200']} ({r['dist_ema']}%) | SL {r['sl']} TGT {r['tgt1']}/{r['tgt2']}\n   Anchor {r['anchor']}\n"
else:
    msg += "\nNo BUY today - Waiting for Green close above AVWP\n"

msg += f"\n*--- WATCHLIST (Near AVWP) - {len(res_watch)} ---*\n"
for r in sorted(res_watch, key=lambda x: x['dist_avwp'])[:12]:
    msg += f"👀 {r['symbol']} @ {r['price']} near AVWP({r['tf']}) {r['avwp']} {r['dist_avwp']}% | SL {r['sl']}\n"

msg += f"\n_Sniper Rule: Entry=Green candle close ABOVE Low AVWP | SL=Hourly close BELOW AVWP_\n_Hourly 200EMA>{r['ema200'] if res_buy else 'check'} = Bull Trend_"

print(msg)
send_telegram(msg)

if res_buy+res_watch:
    pd.DataFrame(res_buy+res_watch).to_csv("sniper_avwp_results.csv", index=False)
