import requests, numpy as np, os, datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK","BAJFINANCE","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS","COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO","HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR","ZOMATO","INDIGO","COFORGE","PERSISTENT","HAL","BEL","TRENT","DMART","DIXON","TATAMOTORS","MOTHERSON","TATAPOWER","POLYCAB","CUMMINSIND","ASHOKLEY","TVSMOTOR","MUTHOOTFIN","CHOLAFIN","FEDERALBNK","PNB","DLF","GODREJPROP","VOLTAS","PFC","RECLTD","IRFC","BSE","MCX","KPITTECH","TATAELXSI","SONACOMS","UNOMINDA","ASTRAL","VBL","TIINDIA"]

def fetch(symbol, days=150):
    try:
        t = f"{symbol}.NS" if "^" not in symbol else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range={days}d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        j = r.json()
        if 'chart' not in j or j['chart']['result'] is None: return None
        res = j['chart']['result'][0]
        q = res['indicators']['quote'][0]
        adj = res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes = np.array([c for c in adj if c is not None], float)
        highs = np.array([h for h in q['high'] if h is not None], float)
        lows = np.array([l for l in q['low'] if l is not None], float)
        vols = np.array([v for v in q['volume'] if v is not None], float)
        if len(closes) < 100: return None
        return closes, highs, lows, vols
    except: return None

def analyze(closes, highs, lows, vols):
    c, h, l, v = closes, highs, lows, vols
    ema9, ema21, ema50, ema200 = np.mean(c[-9:]), np.mean(c[-21:]), np.mean(c[-50:]), np.mean(c[-100:])
    
    # === SWING HIGH/LOW V10 ===
    swing_high = np.max(h[-20:-1])  # Last 20 days high (excluding today)
    swing_low = np.min(l[-20:-1])   # Last 20 days low
    swing_high_5 = np.max(h[-5:])   # Last 5 days high for breakout check
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(l[1:]-c[:-1])))
    atr = np.mean(tr[-14:])
    
    diff = np.diff(c[-15:])
    gain = np.mean([x for x in diff if x>0]) if any(x>0 for x in diff) else 0.5
    loss = np.mean([-x for x in diff if x<0]) if any(x<0 for x in diff) else 0.5
    rsi = 100 - (100/(1 + gain/(loss+1e-9)))
    vol_ratio = v[-1] / (np.mean(v[-20:]) + 1e-9)
    near_ema = abs(c[-1] - ema21) / c[-1]
    
    # Distance calculations
    dist_to_swing_low = (c[-1] - swing_low) / c[-1]  # How far from recent low
    dist_to_swing_high = (swing_high - c[-1]) / c[-1]  # How far from recent high
    is_near_breakout = c[-1] > swing_high_5 * 0.98  # Close to breaking 5-day high
    
    # === V10 SCORING - Max 300 ===
    score = 100  # Base
    
    # Trend
    if ema9 > ema21: score += 20
    if ema21 > ema50: score += 20
    if c[-1] > ema200: score += 20
    
    # EMA21 pullback
    score += max(0, 30 - near_ema*1000)
    
    # RSI
    score += max(0, 20 - abs(rsi-52))
    
    # Volume
    score += min(vol_ratio*10, 20)
    
    # === NEW SWING LOGIC +50 BONUS ===
    # 1. Bounce from swing low (perfect pullback bottom)
    if dist_to_swing_low < 0.06:  # Within 6% of swing low
        score += 25
        swing_bonus_low = "Bounce from Low"
    else:
        swing_bonus_low = ""
    
    # 2. Near swing high breakout
    if dist_to_swing_high < 0.05:  # Within 5% of swing high = breakout setup
        score += 25
        swing_bonus_high = "Breakout Setup"
    else:
        swing_bonus_high = ""
    
    # 3. Breaking 5-day high
    if is_near_breakout:
        score += 15
    
    # Perfect V10 bonus
    is_perfect = (ema9 > ema21 > ema50 and c[-1] > ema200 and 
                  near_ema < 0.035 and 42 <= rsi <= 60 and 
                  dist_to_swing_low < 0.08 and vol_ratio > 1.1)
    if is_perfect: score += 50
    
    # === SMART SL/TGT USING SWING ===
    # SL = Below swing low OR 1.2 ATR, whichever is lower (safer)
    sl_atr = c[-1] - 1.2*atr
    sl_swing = swing_low * 0.99  # 1% below swing low
    sl = sl_atr if abs(sl_swing - c[-1])/c[-1] > 0.05 else sl_swing
# If swing low >5% away, use ATR SL (3-4%), else use swing low SL
    
    # TGT = Swing high (real resistance)
    tgt_swing = swing_high
    tgt_atr = c[-1] + 2.5*atr
    tgt = min(tgt_swing, tgt_atr)  # Conservative target
    if tgt < c[-1] * 1.02:  # If swing high too close, use ATR target
        tgt = tgt_atr
    
    return {
        "price": c[-1], "rsi": rsi, "vol_ratio": vol_ratio, "score": score,
        "sl": sl, "tgt": tgt, "risk": (c[-1]-sl)/c[-1]*100,
        "swing_high": swing_high, "swing_low": swing_low,
        "dist_low": dist_to_swing_low*100, "dist_high": dist_to_swing_high*100,
        "perfect": is_perfect,
        "swing_tag": f"{swing_bonus_low} {swing_bonus_high}".strip()
    }

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(msg); return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)

candidates = []
for sym in SYMBOLS:
    d = fetch(sym, 150)
    if d is None: continue
    res = analyze(*d)
    if res:
        res['symbol'] = sym
        candidates.append(res)
    print(f"{sym}: {res['score']:.0f} Low{res['dist_low']:.1f}% High{res['dist_high']:.1f}%")

candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]
date_str = datetime.datetime.now().strftime("%d-%b %Y %H:%M")

msg = f"🚀 *V10 SWING KILLER - TOP 3* - {date_str}\n"
msg += f"PF: 2.8+ | With Swing High/Low Logic\n\n"
for i, s in enumerate(candidates, 1):
    tag = "✅ PERFECT V10" if s['perfect'] else f"⭐ {s['swing_tag']}" if s['swing_tag'] else "⭐ BEST"
    msg += f"*{i}. {s['symbol']}* {tag} - ₹{s['price']:.1f}\n"
    msg += f"   Score: {s['score']:.0f} | RSI: {s['rsi']:.0f} | Vol x{s['vol_ratio']:.1f}\n"
    msg += f"   Swing Low: ₹{s['swing_low']:.1f} ({s['dist_low']:.1f}% above) | High: ₹{s['swing_high']:.1f}\n"
    msg += f"   SL: ₹{s['sl']:.1f} ({s['risk']:.1f}%) | TGT: ₹{s['tgt']:.1f} ({(s['tgt']/s['price']-1)*100:.1f}%)\n\n"
msg += f"⏰ Entry: 9:20 AM breakout | SL: Below Swing Low"

print(msg)
send_telegram(msg)
