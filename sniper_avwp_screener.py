# V8 FINAL - KOTAK IDEAL WTH + 15 MIN AUTO REFRESH + ANTI-SPAM - COMPLETE CODE
import yfinance as yf
import pandas as pd
import time, os, requests, json
from datetime import datetime

# Telegram - Supports both bots
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("SNIPER_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("SNIPER_CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("No BOT_TOKEN/CHAT_ID found, printing only")
        print(msg)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        # Split into 3500 char chunks
        for i in range(0, len(msg), 3500):
            chunk = msg[i:i+3500]
            resp = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"}, timeout=20)
            print(f"TG Sent chunk {i//3500+1}: {resp.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")
        print(msg)

# Nifty 50 + Next 50 - No LTIM
SYMBOLS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS",
    "LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS",
    "M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS",
    "ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS",
    "JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS",
    "BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS",
    "APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"
]

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def find_swing_lows(df, window=5):
    lows = []
    try:
        for i in range(window, len(df)-window):
            if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
                lows.append((df.index[i], float(df['Low'].iloc[i])))
    except Exception as e:
        pass
    return lows[-10:]  # Last 10

def find_swing_highs(df, window=5):
    highs = []
    try:
        for i in range(window, len(df)-window):
            if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
                highs.append((df.index[i], float(df['High'].iloc[i])))
    except:
        pass
    return highs[-8:]

def calc_avwap(df, anchor_date):
    try:
        df_after = df[df.index >= anchor_date]
        if len(df_after) < 5:
            return None
        typical = (df_after['High'] + df_after['Low'] + df_after['Close']) / 3
        avwap = (typical * df_after['Volume']).cumsum() / df_after['Volume'].cumsum()
        return float(avwap.iloc[-1])
    except:
        return None

def scan_stock(symbol):
    try:
        time.sleep(0.35)  # Avoid yfinance block
        weekly = yf.download(symbol, period="2y", interval="1wk", progress=False, auto_adjust=False)
        daily = yf.download(symbol, period="1y", interval="1d", progress=False, auto_adjust=False)
        hourly = yf.download(symbol, period="3mo", interval="1h", progress=False, auto_adjust=False)

        if len(hourly) < 120 or len(daily) < 80 or len(weekly) < 30:
            return None

        for df in [weekly, daily, hourly]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        # WTH Filter: Weekly Timeframe - Kotak Ideal
        w8 = ema(weekly['Close'], 8).iloc[-1]
        w20 = ema(weekly['Close'], 20).iloc[-1]
        d8 = ema(daily['Close'], 8).iloc[-1]
        d20 = ema(daily['Close'], 20).iloc[-1]
        h200 = ema(hourly['Close'], 200).iloc[-1] if len(hourly) >= 200 else ema(hourly['Close'], 120).iloc[-1]
        h400 = ema(hourly['Close'], 400).iloc[-1] if len(hourly) >= 400 else ema(hourly['Close'], 200).iloc[-1]

        # Must be bullish WTH: 200 > 400 crossed + 8 > 20
        if not (h200 > h400 and w8 > w20 and d8 > d20):
            return None

        # Find all AVWPs
        low_avwps = []
        high_avwps = []

        for df, tf, win in [(hourly, "H", 12), (daily, "D", 5), (weekly, "W", 3)]:
            for anchor, swing_low in find_swing_lows(df, win):
                av = calc_avwap(df, anchor)
                if av and av > swing_low * 0.80 and av < swing_low * 1.30:
                    low_avwps.append((av, anchor, tf, swing_low))
            for anchor, swing_high in find_swing_highs(df, win):
                av = calc_avwap(df, anchor)
                if av and av > swing_high * 0.70 and av < swing_high * 1.30:
                    high_avwps.append((av, anchor, tf, swing_high))

        if len(low_avwps) < 2:
            return None

        curr_price = float(hourly['Close'].iloc[-1])
        open_price = float(hourly['Open'].iloc[-1])

        # SCREENSHOT 1 FIX: Skip if Below HIGH AVWP Resistance (SBILIFE)
        for av_high, anchor_h, tf_h, sh in high_avwps:
            if av_high > curr_price and (av_high - curr_price) / curr_price * 100 < 5.0:
                return {
                    "symbol": symbol.replace(".NS", ""),
                    "skip": True,
                    "reason": "BELOW HIGH AVWP RESISTANCE",
                    "price": round(curr_price, 2),
                    "high_avwp": round(av_high, 2)
                }

        # Must be ABOVE Low AVWP Cluster
        above_low = [x for x in low_avwps if x[0] <= curr_price]
        near_low = [x for x in above_low if abs(x[0] - curr_price) / curr_price * 100 < 6.0]

        if len(near_low) < 2:
            return None

        # Cluster detection - Tight 1.5% cluster like Kotak 450-457
        near_low_sorted = sorted(near_low, key=lambda x: x[0])
        cluster = [near_low_sorted[-1]]  # Highest AVWP
        for av in reversed(near_low_sorted[:-1]):
            if abs(av[0] - cluster[0][0]) / cluster[0][0] * 100 < 1.5:  # Tight cluster for small SL
                cluster.append(av)

        if len(cluster) < 2:
            return None

        cluster_avg = sum(c[0] for c in cluster) / len(cluster)
        cluster_low = min(c[0] for c in cluster)
        swing_low = min(c[3] for c in cluster)

        dist_cluster = abs(curr_price - cluster_avg) / curr_price * 100
        dist_200ema = abs(curr_price - h200) / curr_price * 100

        # Kotak Condition: Near 200 EMA + Near AVWP Cluster + Above Cluster
        if dist_cluster < 4.0 and dist_200ema < 6.0 and curr_price > cluster_avg:
            small_sl = round(cluster_low * 0.992, 2)  # Your 450 model
            big_sl = round(swing_low * 0.99, 2)       # Your 436 model
            risk = round((curr_price - small_sl) / curr_price * 100, 2)

            if risk > 4.0:  # Skip high risk
                return None

            anchors_str = ", ".join([c[1].strftime('%d-%b %H:%M') for c in cluster[:3]])
            signal = "BUY" if curr_price > open_price else "WATCH"

            return {
                "symbol": symbol.replace(".NS", ""),
                "skip": False,
                "price": round(curr_price, 2),
                "cluster_avg": round(cluster_avg, 2),
                "cluster_count": len(cluster),
                "dist_cluster": round(dist_cluster, 2),
                "ema200": round(float(h200), 2),
                "ema400": round(float(h400), 2),
                "dist_200": round(dist_200ema, 2),
                "small_sl": small_sl,
                "big_sl": big_sl,
                "risk": risk,
                "signal": signal,
                "anchors": anchors_str
            }
        return None
    except Exception as e:
        # print(f"Error {symbol}: {e}")
        return None

# MAIN
print(f"=== V8 KOTAK IDEAL WTH - {datetime.now()} ===")
buy_list = []
skip_list = []

for sym in SYMBOLS:
    result = scan_stock(sym)
    if result:
        if result.get("skip"):
            skip_list.append(result)
        else:
            buy_list.append(result)

# Create Message
ist_time = datetime.now().strftime('%d-%b %H:%M')
msg = f"🎯 *V8 KOTAK IDEAL WTH - {ist_time} IST*\n"
msg += f"*WTH: W8>W20 + D8>D20 + H200>H400 + Above AVWP Cluster + Near 200EMA*\n\n"
msg += f"*BUY {len(buy_list)} - Above AVWP + Near 200EMA*\n"

for r in sorted(buy_list, key=lambda x: x['dist_cluster'])[:12]:
    msg += f"\n✅ *{r['symbol']}* @ {r['price']} | {r['cluster_count']} AVWP {r['cluster_avg']} {r['dist_cluster']}% | 200 {r['ema200']} {r['dist_200']}% | SL {r['small_sl']}({r['risk']}%) Big {r['big_sl']} | {r['anchors']}\n"

msg += f"\n*SKIPPED {len(skip_list)} - Below HIGH AVWP Resistance*\n"
for s in skip_list[:8]:
    msg += f"❌ {s['symbol']} @ {s['price']} < HIGH {s['high_avwp']} - Resistance\n"

msg += f"\n_Kotak 457 Model: Entry near cluster, Small SL=Below cluster, Big SL=Below swing low_"
msg += f"\n_Auto 15min refresh during market hours_"

print(msg)

# Anti-Spam Logic: Send only if price changed >0.3% or new stock
last_file = "last_sniper.json"
curr_prices = {r['symbol']: r['price'] for r in buy_list}
should_send = True

if os.path.exists(last_file):
    try:
        with open(last_file, 'r') as f:
            last_data = json.load(f)
        # If same symbols and all prices within 0.3%, skip
        if len(last_data) == len(curr_prices):
            all_same = True
            for sym, price in curr_prices.items():
                if sym not in last_data:
                    all_same = False
                    break
                if abs(price - last_data[sym]) / last_data[sym] * 100 > 0.35:
                    all_same = False
                    break
            if all_same:
                should_send = False
                print("No significant change >0.35%, skipping Telegram to avoid spam")
    except Exception as e:
        print(f"Last file read error: {e}")

if should_send:
    send_telegram(msg)
    # Save current
    try:
        with open(last_file, 'w') as f:
            json.dump(curr_prices, f)
    except:
        pass
else:
    print("Message not sent (anti-spam), but logged")

# Save CSV
if buy_list:
    df = pd.DataFrame(buy_list)
    df.to_csv("sniper_avwp_results.csv", index=False)
    print(f"Saved {len(buy_list)} results to CSV")
