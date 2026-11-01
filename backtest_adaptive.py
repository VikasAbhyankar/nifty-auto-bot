import requests, numpy as np, time

def fetch(symbol, days=400):
    try:
        if "^" in symbol:
    ticker = symbol
else:
    ticker = f"{symbol}.NS"
url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={days}d"
        d = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
        res = d['chart']['result'][0]; q = res['indicators']['quote'][0]
        adj = res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes = np.array([c for c in adj if c], float)
        highs = np.array([h for h in q['high'] if h], float)
        lows = np.array([l for l in q['low'] if l], float)
        vols = np.array([v for v in q['volume'] if v], float)
        if len(closes) < 200: return None
        return closes, highs, lows, vols
    except Exception as e:
        print(f"Fetch fail {symbol}: {e}")
        return None

def get_regime_on_day(nifty_closes, nifty_highs, nifty_lows, idx):
    c_hist = nifty_closes[:idx]
    if len(c_hist) < 100: return "BULL_PULLBACK"
    ema50 = np.mean(c_hist[-50:]); ema200 = np.mean(c_hist[-200:])
    tr = np.maximum(nifty_highs[1:idx]-nifty_lows[1:idx], np.abs(nifty_highs[1:idx]-nifty_closes[:idx-1]))
    atr = np.mean(tr[-14:]); atr_pct = atr/c_hist[-1]*100
    up_days = np.sum(np.diff(c_hist[-20:])>0)
    if c_hist[-1] > ema200 and c_hist[-1] > ema50 and up_days >= 12 and atr_pct < 2.5: return "STRONG_BULL_BREAKOUT"
    elif c_hist[-1] > ema50 and atr_pct < 3.0: return "BULL_PULLBACK"
    elif atr_pct > 3.5: return "VOLATILE"
    elif c_hist[-1] < ema50: return "BEAR_DEFENSIVE"
    else: return "SIDEWAYS"

SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK","BAJFINANCE","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","ONGC","BAJAJFINSV"]

print("Fetching Nifty...")
nifty_data = fetch("^NSEI", 500)
if not nifty_data:
    print("Nifty fetch failed, using RELIANCE as proxy for market")
    nifty_data = fetch("RELIANCE", 500)
if not nifty_data:
    print("Total fail - exit"); exit(1)
n_close, n_high, n_low, n_vol = nifty_data
trades = []; regime_stats = {}

for sym in SYMBOLS:
    print(f"Testing {sym}...")
    data = fetch(sym, 500)
    if not data: continue
    closes, highs, lows, vols = data
    min_len = min(len(closes), len(n_close))
    closes = closes[-min_len:]; highs = highs[-min_len:]; lows = lows[-min_len:]; vols = vols[-min_len:]
    nc = n_close[-min_len:]; nh = n_high[-min_len:]; nl = n_low[-min_len:]
    for i in range(200, len(closes)-20):
        regime = get_regime_on_day(nc, nh, nl, i)
        c_hist = closes[:i]; h_hist = highs[:i]; l_hist = lows[:i]; v_hist = vols[:i]
        ema9 = np.mean(c_hist[-9:]); ema21 = np.mean(c_hist[-21:]); ema50 = np.mean(c_hist[-50:])
        ema200 = np.mean(c_hist[-100:])
        tr_s = np.maximum(h_hist[1:]-l_hist[1:], np.maximum(np.abs(h_hist[1:]-c_hist[:-1]), np.abs(l_hist[1:]-c_hist[:-1])))
        atr = np.mean(tr_s[-14:])
        diff = np.diff(c_hist[-15:]); gain = np.mean([d for d in diff if d>0]) if any(d>0 for d in diff) else 0.5
        loss = np.mean([-d for d in diff if d<0]) if any(d<0 for d in diff) else 0.5
        rsi = 100-(100/(1+(gain/(loss+1e-9))))
        vol_ratio = v_hist[-1]/(np.mean(v_hist[-20:])+1e-9)
        swing_high = np.max(h_hist[-11:-1])
        signal=False; sl=0; tgt=0
        if regime == "STRONG_BULL_BREAKOUT":
            if c_hist[-1] > swing_high and vol_ratio>=2.0 and 50<=rsi<=65 and ema9>ema21>ema50:
                signal=True; sl=c_hist[-1]-1.5*atr; tgt=c_hist[-1]+3*atr
        elif regime == "BULL_PULLBACK":
            near_ema = abs(c_hist[-1]-ema21)/c_hist[-1] < 0.025
            if ema9>ema21>ema50 and c_hist[-1]>ema200 and near_ema and 45<=rsi<=58 and vol_ratio>1.2:
                signal=True; sl=c_hist[-1]-1.2*atr; tgt=c_hist[-1]+2.5*atr
        elif regime == "VOLATILE":
            near_ema = abs(c_hist[-1]-ema21)/c_hist[-1] < 0.015
            if ema9>ema21 and near_ema and 40<=rsi<=55 and 1.5<=vol_ratio<=3.5:
                signal=True; sl=c_hist[-1]-0.9*atr; tgt=c_hist[-1]+2.0*atr
        else:
            if c_hist[-1]>ema50 and c_hist[-1]>ema200 and vol_ratio>=2.5 and 50<=rsi<=60 and c_hist[-1]>swing_high:
                signal=True; sl=c_hist[-1]-1.0*atr; tgt=c_hist[-1]+1.8*atr
        if signal:
            entry=c_hist[-1]
            future_lows=lows[i:i+15]; future_highs=highs[i:i+15]; future_closes=closes[i:i+15]
            pnl=0; result="TIME"
            for j in range(len(future_lows)):
                if future_lows[j] <= sl: pnl=(sl-entry)/entry*100; result="SL"; break
                if future_highs[j] >= tgt: pnl=(tgt-entry)/entry*100; result="TGT"; break
            else: pnl=(future_closes[-1]-entry)/entry*100
            trades.append({"sym":sym,"regime":regime,"pnl":pnl})
            regime_stats[regime]=regime_stats.get(regime,0)+1
    time.sleep(0.6)

if trades:
    wins=len([t for t in trades if t['pnl']>0]); total=len(trades); wr=wins/total*100
    avgW=np.mean([t['pnl'] for t in trades if t['pnl']>0]) if wins else 0
    avgL=np.mean([t['pnl'] for t in trades if t['pnl']<=0]) if total-wins else 0
    total_pnl=sum([t['pnl'] for t in trades]); pf=abs(avgW*wins/(avgL*(total-wins)+1e-9))
    print(f"\n=== ADAPTIVE V10 RESULT ==="); print(f"Total: {total} | Wins: {wins} | WR: {wr:.1f}%"); print(f"AvgW {avgW:.2f}% AvgL {avgL:.2f}% PF {pf:.2f} Total {total_pnl:.1f}%")
    for k,v in regime_stats.items():
        rt=[t for t in trades if t['regime']==k]; wrr=len([t for t in rt if t['pnl']>0])/len(rt)*100 if rt else 0
        print(f"{k}: {len(rt)} trades WR {wrr:.1f}%")
else:
    print("No trades")
