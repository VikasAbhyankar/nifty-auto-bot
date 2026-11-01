import requests, numpy as np, time

def fetch(symbol, days=400):
    try:
        # Fix for Nifty ^NSEI
        if "^" in symbol:
            url_symbol = symbol
        else:
            url_symbol = f"{symbol}.NS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{url_symbol}?interval=1d&range={days}d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        j = r.json()
        if 'chart' not in j or j['chart']['result'] is None:
            print(f"Empty data for {symbol}")
            return None
        res = j['chart']['result'][0]
        q = res['indicators']['quote'][0]
        adj = res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes = np.array([c for c in adj if c is not None], float)
        highs = np.array([h for h in q['high'] if h is not None], float)
        lows = np.array([l for l in q['low'] if l is not None], float)
        vols = np.array([v for v in q['volume'] if v is not None], float)
        if len(closes) < 150:
            return None
        return closes, highs, lows, vols
    except Exception as e:
        print(f"Fetch fail {symbol}: {e}")
        return None

def get_regime(closes, highs, lows, idx):
    c = closes[:idx]
    if len(c) < 100:
        return "BULL_PULLBACK"
    ema50 = np.mean(c[-50:]); ema200 = np.mean(c[-200:])
    tr = np.maximum(highs[1:idx]-lows[1:idx], np.abs(highs[1:idx]-closes[:idx-1]))
    atr = np.mean(tr[-14:]); atr_pct = atr/c[-1]*100
    up = np.sum(np.diff(c[-20:])>0)
    if c[-1] > ema200 and c[-1] > ema50 and up >= 12 and atr_pct < 2.5:
        return "STRONG_BULL_BREAKOUT"
    elif c[-1] > ema50 and atr_pct < 3.0:
        return "BULL_PULLBACK"
    elif atr_pct > 3.5:
        return "VOLATILE"
    elif c[-1] < ema50:
        return "BEAR_DEFENSIVE"
    else:
        return "SIDEWAYS"

SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK","BAJFINANCE","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","ONGC","BAJAJFINSV"]

print("Fetching Nifty...")
n_data = fetch("^NSEI", 500)
if n_data is None:
    print("Nifty ^NSEI blocked, trying NIFTYBEES")
    n_data = fetch("NIFTYBEES", 500)
if n_data is None:
    print("Using RELIANCE as proxy")
    n_data = fetch("RELIANCE", 500)

n_close, n_high, n_low, n_vol = n_data
trades = []

for sym in SYMBOLS:
    print(f"Testing {sym}...")
    d = fetch(sym, 500)
    if d is None:
        continue
    closes, highs, lows, vols = d
    ml = min(len(closes), len(n_close))
    closes = closes[-ml:]; highs = highs[-ml:]; lows = lows[-ml:]; vols = vols[-ml:]
    nc = n_close[-ml:]; nh = n_high[-ml:]; nl = n_low[-ml:]

    for i in range(200, len(closes)-20):
        regime = get_regime(nc, nh, nl, i)
        ch = closes[:i]; hh = highs[:i]; lh = lows[:i]; vh = vols[:i]
        ema9 = np.mean(ch[-9:]); ema21 = np.mean(ch[-21:]); ema50 = np.mean(ch[-50:]); ema200 = np.mean(ch[-100:])
        trs = np.maximum(hh[1:]-lh[1:], np.abs(hh[1:]-ch[:-1]))
        atr = np.mean(trs[-14:])
        diff = np.diff(ch[-15:])
        gain = np.mean([x for x in diff if x>0]) if any(x>0 for x in diff) else 0.5
        loss = np.mean([-x for x in diff if x<0]) if any(x<0 for x in diff) else 0.5
        rsi = 100-(100/(1+gain/(loss+1e-9)))
        vr = vh[-1]/(np.mean(vh[-20:])+1e-9)
        sh = np.max(hh[-11:-1])
        sig=False; sl=0; tg=0
        if regime=="STRONG_BULL_BREAKOUT":
            if ch[-1]>sh and vr>=2.0 and 50<=rsi<=65 and ema9>ema21>ema50:
                sig=True; sl=ch[-1]-1.5*atr; tg=ch[-1]+3*atr
        elif regime=="BULL_PULLBACK":
            near = abs(ch[-1]-ema21)/ch[-1] < 0.025
            if ema9>ema21>ema50 and ch[-1]>ema200 and near and 45<=rsi<=58 and vr>1.2:
                sig=True; sl=ch[-1]-1.2*atr; tg=ch[-1]+2.5*atr
        elif regime=="VOLATILE":
            near = abs(ch[-1]-ema21)/ch[-1] < 0.015
            if ema9>ema21 and near and 40<=rsi<=55 and 1.5<=vr<=3.5:
                sig=True; sl=ch[-1]-0.9*atr; tg=ch[-1]+2.0*atr
        else:
            if ch[-1]>ema50 and ch[-1]>ema200 and vr>=2.5 and 50<=rsi<=60 and ch[-1]>sh:
                sig=True; sl=ch[-1]-1.0*atr; tg=ch[-1]+1.8*atr
        if sig:
            entry=ch[-1]
            fl=lows[i:i+15]; fh=highs[i:i+15]; fc=closes[i:i+15]
            pnl=0
            for j in range(len(fl)):
                if fl[j]<=sl: pnl=(sl-entry)/entry*100; break
                if fh[j]>=tg: pnl=(tg-entry)/entry*100; break
            else: pnl=(fc[-1]-entry)/entry*100
            trades.append(pnl)
    time.sleep(0.5)

if trades:
    wins=len([x for x in trades if x>0]); tot=len(trades); wr=wins/tot*100
    avgW=np.mean([x for x in trades if x>0]) if wins else 0
    avgL=np.mean([x for x in trades if x<=0]) if tot-wins else 0
    pf=abs(avgW*wins/(avgL*(tot-wins)+1e-9)) if avgL!=0 else 0
    totp=sum(trades)
    print(f"\n=== ADAPTIVE V10 RESULT ===")
    print(f"Total: {tot} Wins: {wins} WR: {wr:.1f}%")
    print(f"AvgW {avgW:.2f}% AvgL {avgL:.2f}% PF {pf:.2f} Total {totp:.1f}%")
else:
    print("No trades found - but script OK")
