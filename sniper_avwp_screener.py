# V10 FINAL - ERROR FREE - NIFTY 200 KOTAK MODEL - 15 MIN AUTO
import yfinance as yf
import pandas as pd
import time
import os
import requests
import json
from datetime import datetime

# ---- CONFIG ----
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("SNIPER_BOT_TOKEN") or ""
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("SNIPER_CHAT_ID") or ""
GITHUB_EVENT = os.getenv("GITHUB_EVENT_NAME") or "manual"

print(f"=== V10 START ===")
print(f"Event: {GITHUB_EVENT}")
print(f"BOT exists: {len(BOT_TOKEN) > 20} CHAT exists: {len(CHAT_ID) > 2}")

# Market hours check - Only for auto runs
try:
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
except Exception:
    # Fallback if pytz fails
    now_ist = datetime.utcnow()
    # Add 5:30 for IST rough
    from datetime import timedelta
    now_ist = now_ist + timedelta(hours=5, minutes=30)

print(f"IST Time Now: {now_ist.strftime('%d-%b-%Y %H:%M:%S %A')}")

is_manual = GITHUB_EVENT == "workflow_dispatch"

if not is_manual:
    # Auto run - Check market hours
    if now_ist.weekday() >= 5:
        print("Weekend - No Telegram, exit")
        exit(0)
    total_mins = now_ist.hour * 60 + now_ist.minute
    if total_mins < 555 or total_mins > 935:  # 9:15 = 555, 15:35 = 935
        print(f"Outside market 9:15-15:35 IST - No Telegram, exit. Mins={total_mins}")
        exit(0)
    print("Market hours OK - Continue scan")
else:
    print("Manual run - Force continue even outside market")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID missing!")
        print(msg)
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        # Split into 4000 char chunks
        for i in range(0, len(msg), 4000):
            chunk = msg[i:i+4000]
            resp = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"}, timeout=30)
            print(f"Telegram status: {resp.status_code} - {resp.text[:150]}")
            time.sleep(1)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

# NIFTY 200 LIST - Cleaned, no duplicates
SYMBOLS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS",
    "BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS",
    "ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS",
    "ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS",
    "BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS",
    "TATAPOWER.NS","ADANIGREEN.NS","AMBUJACEM.NS","APOLLOTYRE.NS","ASHOKLEY.NS","ASTRAL.NS","AUBANK.NS","AUROPHARMA.NS","BANKBARODA.NS","BATAINDIA.NS",
    "BERGEPAINT.NS","BHARATFORG.NS","BHEL.NS","BIOCON.NS","BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS","CUMMINSIND.NS","DABUR.NS","DALBHARAT.NS",
    "DEEPAKNTR.NS","DLF.NS","ESCORTS.NS","EXIDEIND.NS","FEDERALBNK.NS","GAIL.NS","GLENMARK.NS","GODREJCP.NS","GODREJPROP.NS","HAVELLS.NS",
    "HEROMOTOCO.NS","HINDPETRO.NS","ICICIGI.NS","ICICIPRULI.NS","IDFCFIRSTB.NS","IGL.NS","INDHOTEL.NS","INDIAMART.NS","INDIGO.NS","IOC.NS",
    "IPCALAB.NS","IRCTC.NS","JINDALSTEL.NS","JUBLFOOD.NS","LALPATHLAB.NS","LAURUSLABS.NS","LICI.NS","LTIM.NS","LTTS.NS","LUPIN.NS",
    "M&MFIN.NS","MARICO.NS","MCDOWELL-N.NS","MFSL.NS","MGL.NS","MOTHERSON.NS","MPHASIS.NS","MUTHOOTFIN.NS","NAUKRI.NS","NAVINFLUOR.NS",
    "NESTLEIND.NS","NMDC.NS","OBEROIRLTY.NS","OFSS.NS","PAGEIND.NS","PETRONET.NS","PIDILITIND.NS","PIIND.NS","PNB.NS","POLYCAB.NS",
    "PVRINOX.NS","RAMCOCEM.NS","RBLBANK.NS","SAIL.NS","SBICARD.NS","SHREECEM.NS","SIEMENS.NS","SRF.NS","SUNTV.NS","TATACHEM.NS",
    "TATACOMM.NS","TATACONSUM.NS","TATAMOTORS.NS","TORNTPHARM.NS","TORNTPOWER.NS","TVSMOTOR.NS","UBL.NS","UPL.NS","VOLTAS.NS","ZEEL.NS",
    "ZYDUSLIFE.NS","ZOMATO.NS","PAYTM.NS","NYKAA.NS","POLICYBZR.NS"
]

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def find_lows(df, window=5):
    res = []
    try:
        for i in range(window, len(df)-window):
            if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
                res.append((df.index[i], float(df['Low'].iloc[i])))
    except Exception:
        pass
    return res[-10:]

def find_highs(df, window=5):
    res = []
    try:
        for i in range(window, len(df)-window):
            if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
                res.append((df.index[i], float(df['High'].iloc[i])))
    except Exception:
        pass
    return res[-8:]

def avwap(df, anchor):
    try:
        d = df[df.index >= anchor]
        if len(d) < 5:
            return None
        typical = (d['High'] + d['Low'] + d['Close']) / 3
        vol = d['Volume']
        if vol.sum() == 0:
            return None
        return float(((typical * vol).cumsum() / vol.cumsum()).iloc[-1])
    except Exception:
        return None

def scan_stock(sym):
    try:
        time.sleep(0.2)
        wk = yf.download(sym, period="2y", interval="1wk", progress=False, auto_adjust=False)
        dy = yf.download(sym, period="1y", interval="1d", progress=False, auto_adjust=False)
        hr = yf.download(sym, period="6mo", interval="1h", progress=False, auto_adjust=False)
        if len(hr) < 100 or len(dy) < 60 or len(wk) < 20:
            return None
        for df in [wk, dy, hr]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        # Indicators
        w8 = ema(wk['Close'], 8).iloc[-1]
        w20 = ema(wk['Close'], 20).iloc[-1]
        d8 = ema(dy['Close'], 8).iloc[-1]
        d20 = ema(dy['Close'], 20).iloc[-1]
        h200 = ema(hr['Close'], 200).iloc[-1] if len(hr) >= 200 else ema(hr['Close'], 100).iloc[-1]
        h400 = ema(hr['Close'], 400).iloc[-1] if len(hr) >= 400 else ema(hr['Close'], 200).iloc[-1]
        if not (h200 > h400 and w8 > w20 and d8 > d20):
            return None
        low_av = []
        high_av = []
        for df, tf, win in [(hr, "H", 12), (dy, "D", 5), (wk, "W", 3)]:
            for anc, sl in find_lows(df, win):
                av = avwap(df, anc)
                if av and av > sl * 0.80 and av < sl * 1.30:
                    low_av.append((av, anc, tf, sl))
            for anc, sh in find_highs(df, win):
                av = avwap(df, anc)
                if av:
                    high_av.append((av, anc, tf, sh))
        if len(low_av) < 2:
            return None
        curr = float(hr['Close'].iloc[-1])
        open_ = float(hr['Open'].iloc[-1])
        # Check HIGH AVWP resistance
        for av_h, _, _, _ in high_av:
            if av_h > curr and (av_h - curr) / curr * 100 < 5.0:
                return {"symbol": sym.replace(".NS",""), "skip": True, "price": round(curr,2), "high_avwp": round(av_h,2)}
        above = [x for x in low_av if x[0] <= curr]
        near = [x for x in above if abs(x[0]-curr)/curr*100 < 6.0]
        if len(near) < 2:
            return None
        near = sorted(near, key=lambda x: x[0])
        cluster = [near[-1]]
        for a in reversed(near[:-1]):
            if abs(a[0]-cluster[0][0])/cluster[0][0]*100 < 1.5:
                cluster.append(a)
        if len(cluster) < 2:
            return None
        c_avg = sum(c[0] for c in cluster) / len(cluster)
        c_low = min(c[0] for c in cluster)
        s_low = min(c[3] for c in cluster)
        dist_c = abs(curr - c_avg) / curr * 100
        dist_200 = abs(curr - h200) / curr * 100
        if dist_c < 4.0 and dist_200 < 6.0 and curr > c_avg:
            small_sl = round(c_low * 0.992, 2)
            big_sl = round(s_low * 0.99, 2)
            risk = round((curr - small_sl) / curr * 100, 2)
            if risk > 4.0:
                return None
            return {
                "symbol": sym.replace(".NS",""), "skip": False, "price": round(curr,2),
                "cluster_avg": round(c_avg,2), "cluster_count": len(cluster),
                "dist_cluster": round(dist_c,2), "ema200": round(float(h200),2),
                "dist_200": round(dist_200,2), "small_sl": small_sl, "big_sl": big_sl,
                "risk": risk, "signal": "BUY" if curr > open_ else "WATCH",
                "anchors": ", ".join([c[1].strftime('%d-%b') for c in cluster[:3]])
            }
    except Exception as e:
        print(f"Error {sym}: {e}")
        return None

# ---- MAIN SCAN ----
buy_list = []
skip_list = []
print(f"Scanning {len(SYMBOLS)} stocks...")
for idx, s in enumerate(SYMBOLS):
    if idx % 25 == 0:
        print(f"Progress {idx}/{len(SYMBOLS)}")
    r = scan_stock(s)
    if r:
        if r.get("skip"):
            skip_list.append(r)
        else:
            buy_list.append(r)

ist_str = now_ist.strftime('%d-%b %H:%M IST')
msg = f"🎯 *V10 NIFTY 200 - {ist_str}*\n*WTH + Above AVWP Cluster + Near 200EMA*\n*Scanned {len(SYMBOLS)} stocks*\n\n*BUY {len(buy_list)} - Kotak Model*\n"

for r in sorted(buy_list, key=lambda x: x['dist_cluster'])[:15]:
    msg += f"\n✅ *{r['symbol']}* @ {r['price']} | {r['cluster_count']} AVWP {r['cluster_avg']} {r['dist_cluster']}% | 200 {r['ema200']} {r['dist_200']}% | SL {r['small_sl']}({r['risk']}%) Big {r['big_sl']}\n"

msg += f"\n*SKIPPED {len(skip_list)} - Below HIGH AVWP*\n"
for s in skip_list[:8]:
    msg += f"❌ {s['symbol']} @ {s['price']} < HIGH {s['high_avwp']}\n"

msg += f"\n_15min auto refresh_\n"

print(msg)

# ---- SEND LOGIC ----
last_file = "last_sniper.json"
curr_prices = {r['symbol']: r['price'] for r in buy_list}
should_send = True

if not is_manual:
    # Anti-spam for auto: only send if price moves >0.4%
    if os.path.exists(last_file):
        try:
            with open(last_file, 'r') as f:
                last = json.load(f)
            if len(last) == len(curr_prices) and len(last) > 0:
                same = True
                for sym, price in curr_prices.items():
                    if sym not in last or abs(price - last[sym]) / last[sym] * 100 > 0.4:
                        same = False
                        break
                if same:
                    should_send = False
                    print("No price change >0.4% - Skip Telegram to avoid spam")
        except Exception as e:
            print(f"Last file read error: {e}")

if should_send or is_manual:
    if len(buy_list) == 0 and not is_manual:
        print("No BUY found - Skip Telegram for auto run")
    else:
        send_telegram(msg)
        try:
            with open(last_file, 'w') as f:
                json.dump(curr_prices, f)
            print(f"Saved {last_file}")
        except Exception as e:
            print(f"Save error: {e}")
else:
    print("Anti-spam skip")

# Save CSV
if buy_list:
    try:
        pd.DataFrame(buy_list).to_csv("sniper_avwp_results.csv", index=False)
        print("CSV saved")
    except Exception as e:
        print(f"CSV error: {e}")
