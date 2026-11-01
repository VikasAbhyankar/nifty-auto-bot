import requests, numpy as np, time
def get_symbols():
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK","BAJFINANCE","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO","ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS","COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO","HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR","ZOMATO","INDIGO","COFORGE","PERSISTENT","HAL","BEL","TRENT","DMART","DIXON","TATAMOTORS","MOTHERSON","TATAPOWER","POLYCAB","CUMMINSIND","ASHOKLEY","TVSMOTOR","MUTHOOTFIN","CHOLAFIN","FEDERALBNK","PNB","DLF","GODREJPROP","VOLTAS","PFC","RECLTD","IRFC","BSE","MCX","KPITTECH","TATAELXSI","SONACOMS","UNOMINDA","ASTRAL","VBL","TIINDIA"]
def fetch(s):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{s.replace(' ','')}.NS?interval=1d&range=400d"
        d=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()
        res=d['chart']['result'][0]; q=res['indicators']['quote'][0]
        adj=res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes=np.array([c for c in adj if c],float); highs=np.array([h for h in q['high'] if h],float)
        lows=np.array([l for l in q['low'] if l],float); vols=np.array([v for v in q['volume'] if v],float)
        if len(closes)<150: return None
        return closes,highs,lows,vols
    except: return None
trades=[]
for sym in get_symbols():
    data=fetch(sym); 
    if not data: continue
    closes,highs,lows,vols=data
    for i in range(100,len(closes)-20):
        c_hist=closes[:i]; h_hist=highs[:i]; l_hist=lows[:i]; v_hist=vols[:i]
        ema9=np.mean(c_hist[-9:]); ema21=np.mean(c_hist[-21:]); ema50=np.mean(c_hist[-50:])
        ema200=np.mean(c_hist[-100:])
        # PULLBACK LOGIC: Uptrend but price near ema21
        uptrend=ema9>ema21>ema50 and c_hist[-1]>ema200
        near_ema21=abs(c_hist[-1]-ema21)/c_hist[-1] < 0.02  # Within 2% of EMA21
        rsi_diff=np.diff(c_hist[-15:]); gain=np.mean([d for d in rsi_diff if d>0]) if any(d>0 for d in rsi_diff) else 0.5; loss=np.mean([-d for d in rsi_diff if d<0]) if any(d<0 for d in rsi_diff) else 0.5; rsi=100-(100/(1+(gain/(loss+1e-9))))
        vol_ratio=v_hist[-1]/(np.mean(v_hist[-20:])+1e-9)
        # BUY when pullback in uptrend, RSI 45-58, not too high volume
        if uptrend and near_ema21 and 45<=rsi<=58 and c_hist[-1]>c_hist[-2] and vol_ratio>1.2:
            entry=c_hist[-1]
            atr=np.mean([max(h_hist[k]-l_hist[k], abs(h_hist[k]-c_hist[k-1]), abs(l_hist[k]-c_hist[k-1])) for k in range(1,len(h_hist))][-14:])
            sl=entry-1.2*atr; tgt=entry+2.5*atr
            future_closes=closes[i:i+15]; future_lows=lows[i:i+15]; future_highs=highs[i:i+15]
            pnl=0; result="TIME"
            for j in range(len(future_closes)):
                if future_lows[j]<=sl: pnl=(sl-entry)/entry*100; result="SL"; break
                if future_highs[j]>=tgt: pnl=(tgt-entry)/entry*100; result="TGT"; break
            else: pnl=(future_closes[-1]-entry)/entry*100
            trades.append({"sym":sym,"pnl":pnl,"result":result,"rsi":rsi,"vol":vol_ratio})
    time.sleep(0.15)
wins=len([t for t in trades if t['pnl']>0]); total=len(trades)
wr=wins/total*100 if total else 0
avgW=np.mean([t['pnl'] for t in trades if t['pnl']>0]) if wins else 0
avgL=np.mean([t['pnl'] for t in trades if t['pnl']<=0]) if total-wins else 0
print(f"=== BACKTEST V9 PULLBACK ==="); print(f"Period: 200d | Stocks: {len(get_symbols())}"); print(f"Total: {total} | Wins: {wins} | Loss: {total-wins} | WR: {wr:.1f}%"); print(f"Avg Win: {avgW:.2f}% | Avg Loss: {avgL:.2f}% | Total: {sum([t['pnl'] for t in trades]):.1f}%"); print(f"PF: {abs(avgW*wins/(avgL*(total-wins)+1e-9)):.2f}")
for t in trades[-10:]: print(f"{t['sym']} {t['result']} {t['pnl']:.1f}% RSI{t['rsi']:.0f}")
