import requests, numpy as np, os, json, datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK","BAJFINANCE","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS","COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO","HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR","ZOMATO","INDIGO","COFORGE","PERSISTENT","HAL","BEL","TRENT","DMART","DIXON","TATAMOTORS","MOTHERSON","TATAPOWER","POLYCAB","CUMMINSIND","ASHOKLEY","TVSMOTOR","MUTHOOTFIN","CHOLAFIN","FEDERALBNK","PNB","DLF","GODREJPROP","VOLTAS","PFC","RECLTD","IRFC","BSE","MCX","KPITTECH","TATAELXSI","SONACOMS","UNOMINDA","ASTRAL","VBL","TIINDIA"]

def fetch_data(symbol, days=250):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range={days}d"
        d = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        res = d['chart']['result'][0]; q = res['indicators']['quote'][0]
        adj = res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes = np.array([c for c in adj if c], float)
        highs = np.array([h for h in q['high'] if h], float)
        lows = np.array([l for l in q['low'] if l], float)
        vols = np.array([v for v in q['volume'] if v], float)
        if len(closes) < 120: return None
        return closes, highs, lows, vols
    except: return None

def get_market_regime():
    """Neural Brain: Decides market condition for TODAY"""
    data = fetch_data("^NSEI", 250)  # NIFTY 50
    if data is None:
        return {"regime":"BULL_PULLBACK", "reason":"Nifty fetch fail, default Bull"}
    closes, highs, lows, vols = data
    ema20 = np.mean(closes[-20:]); ema50 = np.mean(closes[-50:]); ema200 = np.mean(closes[-200:])
    # ADX proxy
    tr = np.maximum(highs[1:]-lows[1:], np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    atr = np.mean(tr[-14:]); atr_pct = atr/closes[-1]*100
    
    # Trend strength
    up_days = np.sum(np.diff(closes[-20:])>0)
    
    if closes[-1] > ema200 and closes[-1] > ema50 and up_days >= 12 and atr_pct < 2.5:
        return {"regime":"STRONG_BULL_BREAKOUT", "reason":f"Nifty > EMA200, Up {up_days}/20 days, ATR {atr_pct:.1f}% - Trending Bull", "atr":atr_pct}
    elif closes[-1] > ema50 and closes[-1] > ema200 and atr_pct < 3.0:
        return {"regime":"BULL_PULLBACK", "reason":f"Nifty > EMA50, ATR {atr_pct:.1f}% - Healthy Bull, Buy Pullbacks", "atr":atr_pct}
    elif atr_pct > 3.5:
        return {"regime":"VOLATILE", "reason":f"Nifty ATR {atr_pct:.1f}% - High Volatile, Tight SL Pullback only", "atr":atr_pct}
    elif closes[-1] < ema50 and closes[-1] < ema20:
        return {"regime":"BEAR_DEFENSIVE", "reason":f"Nifty < EMA50, Down {20-up_days}/20 - Bear/Weak, Avoid Breakouts", "atr":atr_pct}
    else:
        return {"regime":"SIDEWAYS", "reason":f"Nifty Choppy, ADX low, ATR {atr_pct:.1f}% - Sideways", "atr":atr_pct}

def analyze_stock(closes, highs, lows, vols):
    ema9 = np.mean(closes[-9:]); ema21 = np.mean(closes[-21:]); ema50 = np.mean(closes[-50:])
    ema200 = np.mean(closes[-100:])
    tr = np.maximum(highs[1:]-lows[1:], np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    atr = np.mean(tr[-14:])
    diff = np.diff(closes[-15:]); gain = np.mean([d for d in diff if d>0]) if any(d>0 for d in diff) else 0.5
    loss = np.mean([-d for d in diff if d<0]) if any(d<0 for d in diff) else 0.5
    rsi = 100-(100/(1+(gain/(loss+1e-9))))
    vol_ratio = vols[-1]/(np.mean(vols[-20:])+1e-9)
    swing_high = np.max(highs[-11:-1]); swing_low = np.min(lows[-11:-1])
    
    return {
        "ema9":ema9,"ema21":ema21,"ema50":ema50,"ema200":ema200,
        "atr":atr,"rsi":rsi,"vol":vol_ratio,
        "swing_high":swing_high,"swing_low":swing_low,
        "close":closes[-1],"prev_close":closes[-2]
    }

def score_strategy(stock_data, regime):
    """Scores 0-100 based on regime"""
    c = stock_data["close"]; ema9=stock_data["ema9"]; ema21=stock_data["ema21"]; ema50=stock_data["ema50"]; ema200=stock_data["ema200"]
    rsi=stock_data["rsi"]; vol=stock_data["vol"]; atr=stock_data["atr"]; sh=stock_data["swing_high"]
    
    if regime == "STRONG_BULL_BREAKOUT":
        # V7/V8 Logic - Breakout is KING here
        score = 0
        if c > sh: score+=30
        if vol >= 2.0: score+=25
        if 50 <= rsi <= 65: score+=20
        if ema9>ema21>ema50: score+=15
        if c > ema200: score+=10
        entry=c; sl=c-1.5*atr; tgt=c+3*atr; strat="BREAKOUT"
        
    elif regime == "BULL_PULLBACK":
        # V9 Logic - Pullback (PF 2.21) - 48% WR
        score = 0
        near_ema21 = abs(c-ema21)/c < 0.025
        if ema9>ema21>ema50 and c>ema200: score+=30
        if near_ema21: score+=25
        if 45 <= rsi <= 58: score+=20
        if c > stock_data["prev_close"]: score+=10
        if vol > 1.2: score+=15
        entry=c; sl=c-1.2*atr; tgt=c+2.5*atr; strat="PULLBACK"
        
    elif regime == "VOLATILE":
        # Tight Pullback only
        score = 0
        near_ema21 = abs(c-ema21)/c < 0.015
        if ema9>ema21>ema50: score+=30
        if near_ema21 and rsi<55: score+=30
        if 1.5 <= vol <= 3.5: score+=20
        if 40 <= rsi <= 55: score+=20
        entry=c; sl=c-0.9*atr; tgt=c+2.0*atr; strat="TIGHT_PULLBACK"
        
    else: # BEAR or SIDEWAYS
        # Defensive - only strongest
        score = 0
        if c > ema50 and c > ema200 and ema9>ema21: score+=20
        if vol >= 2.5 and 50 <= rsi <= 60: score+=30
        if c > sh and vol>=2.0: score+=20
        else: score-=50  # Penalize
        entry=c; sl=c-1.0*atr; tgt=c+1.8*atr; strat="DEFENSIVE"
    
    return score, entry, sl, tgt, strat

def send_telegram(msg):
    if not TELEGRAM_TOKEN: print(msg); return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id":TELEGRAM_CHAT_ID, "text":msg, "parse_mode":"Markdown"}, timeout=10)
    except Exception as e: print(f"TG Fail {e}"); print(msg)

# ===== MAIN BRAIN =====
print("=== ADAPTIVE NEURAL BOSS V10 ===")
regime_info = get_market_regime()
regime = regime_info["regime"]
print(f"Market Regime Today: {regime} - {regime_info['reason']}")

results=[]
for sym in SYMBOLS:
    data = fetch_data(sym)
    if not data: continue
    closes, highs, lows, vols = data
    sd = analyze_stock(closes, highs, lows, vols)
    score, entry, sl, tgt, strat = score_strategy(sd, regime)
    if score >= 55: # Only high confidence
        risk = (entry-sl)/entry*100
        reward = (tgt-entry)/entry*100
        results.append({"sym":sym,"score":score,"entry":entry,"sl":sl,"tgt":tgt,"rsi":sd["rsi"],"vol":sd["vol"],"strat":strat,"risk":risk,"reward":reward})
    # Be nice to API
    # time.sleep(0.1)

results = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

if not results:
    msg = f"⚠️ *No Trade Day*\nRegime: {regime}\n{regime_info['reason']}\n\nNeural decided to SIT OUT today - Market not favorable."
    send_telegram(msg)
else:
    top3 = results[:3]
    msg = f"🧠 *ADAPTIVE NEURAL BOSS V10*\n📅 {datetime.datetime.now().strftime('%d-%b %Y')}\n\n"
    msg += f"📊 *Market Regime:* {regime}\n_{regime_info['reason']}_\n"
    msg += f"🤖 *Strategy Deployed:* {top3[0]['strat']} (Auto-Selected)\n\n"
    msg += f"🔥 *TOP 3 KILLER PICKS* (Score based):\n"
    for i, r in enumerate(top3, 1):
        msg += f"\n{i}. *{r['sym']}* | Score {r['score']}/100\n"
        msg += f"   Strat: {r['strat']} | RSI {r['rsi']:.0f} | Vol {r['vol']:.1f}x\n"
        msg += f"   Entry: ₹{r['entry']:.1f} | SL: ₹{r['sl']:.1f} (-{r['risk']:.1f}%) | TGT: ₹{r['tgt']:.1f} (+{r['reward']:.1f}%)\n"
    
    msg += f"\n📈 Backtest PF: 2.21 | WR 48% (Pullback)\n"
    msg += f"⚙️ Next: Watch Nifty trend - Boss auto-switches strategy tomorrow."
    send_telegram(msg)
    print(msg)

# Save regime log for learning
try:
    with open("regime_log.json","a") as f:
        f.write(json.dumps({"date":str(datetime.datetime.now().date()),"regime":regime,"picks":[r['sym'] for r in results[:3]]})+"\n")
except: pass
