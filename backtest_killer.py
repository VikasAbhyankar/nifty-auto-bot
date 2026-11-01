import requests, numpy as np, time, datetime

def get_symbols():
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK",
    "BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO",
    "ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS",
    "COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO",
    "HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR",
    "ZOMATO","INDIGO","COFORGE","PERSISTENT","NHPC","BLUESTARCO","HAL","BEL","BDL","SIEMENS","ABB","TRENT","DMART","DIXON","TATAMOTORS","MOTHERSON","TATAPOWER","ADANIGREEN","POLYCAB","CUMMINSIND","ASHOKLEY","TVSMOTOR","MUTHOOTFIN","CHOLAFIN","FEDERALBNK","PNB","DLF","GODREJPROP","VOLTAS","PFC","RECLTD","IRFC","BSE","MCX","KPITTECH","TATAELXSI","SONACOMS","UNOMINDA","PETRONET","GAIL","IGL","ASTRAL","PAGEIND","VBL","TIINDIA","ESCORTS"]

def fetch(symbol):
    try:
        s=symbol.replace(" ","")
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.NS?interval=1d&range=400d"
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
        res=d['chart']['result'][0]
        q=res['indicators']['quote'][0]
        adj=res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes=np.array([c for c in adj if c],float)
        highs=np.array([h for h in q['high'] if h],float)
        lows=np.array([l for l in q['low'] if l],float)
        vols=np.array([v for v in q['volume'] if v],float)
        if len(closes)<150: return None
        return closes,highs,lows,vols
    except: return None

trades=[]
for sym in get_symbols():
    data=fetch(sym)
    if data is None: continue
    closes,highs,lows,vols=data
    # Backtest last 200 days, check signal each day
    for i in range(100, len(closes)-20):
        c_hist=closes[:i]; h_hist=highs[:i]; l_hist=lows[:i]; v_hist=vols[:i]
        tr=np.maximum(h_hist[1:]-l_hist[1:], np.maximum(np.abs(h_hist[1:]-c_hist[:-1]), np.abs(l_hist[1:]-c_hist[:-1])))
        atr=np.mean(tr[-14:])
        diff=np.diff(c_hist[-15:])
        gain=np.mean([d for d in diff if d>0]) if any(d>0 for d in diff) else 0.5
        loss=np.mean([-d for d in diff if d<0]) if any(d<0 for d in diff) else 0.5
        rsi=100-(100/(1+(gain/(loss+1e-9))))
        ema9=np.mean(c_hist[-9:]); ema21=np.mean(c_hist[-21:]); ema50=np.mean(c_hist[-50:])
        vol_avg=np.mean(v_hist[-20:]); vol_ratio=v_hist[-1]/(vol_avg+1e-9)
        swing_high=np.max(h_hist[-11:-1]); swing_low=np.min(l_hist[-11:-1])
        st_bull=c_hist[-1]>( (h_hist[-1]+l_hist[-1])/2 -3*atr)
        breakout=c_hist[-1]>swing_high
        
        if breakout and vol_ratio>=1.5 and 45<=rsi<=68 and st_bull and ema9>ema21>ema50:
            entry=c_hist[-1]
            sl=entry-1.5*atr
            tgt=entry+3*atr
            # Simulate next 15 days
            future_closes=closes[i:i+15]
            future_lows=lows[i:i+15]
            future_highs=highs[i:i+15]
            result="OPEN"
            pnl=0
            for j in range(len(future_closes)):
                if future_lows[j]<=sl:
                    result="SL"; pnl=(sl-entry)/entry*100; break
                if future_highs[j]>=tgt:
                    result="TGT"; pnl=(tgt-entry)/entry*100; break
            if result=="OPEN":
                pnl=(future_closes[-1]-entry)/entry*100
                result="TIME_EXIT"
            trades.append({"sym":sym,"date":i,"entry":entry,"sl":sl,"tgt":tgt,"result":result,"pnl":pnl,"vol":vol_ratio,"rsi":rsi})
    time.sleep(0.2)

wins=len([t for t in trades if t['pnl']>0])
loss=len([t for t in trades if t['pnl']<=0])
win_rate=wins/len(trades)*100 if trades else 0
avg_win=np.mean([t['pnl'] for t in trades if t['pnl']>0]) if wins else 0
avg_loss=np.mean([t['pnl'] for t in trades if t['pnl']<=0]) if loss else 0
total_pnl=sum([t['pnl'] for t in trades])

print(f"\n=== BACKTEST KILLER TOP 3 ===")
print(f"Period: Last 200 days | Stocks: {len(get_symbols())}")
print(f"Total Trades: {len(trades)}")
print(f"Wins: {wins} | Loss: {loss} | Win Rate: {win_rate:.1f}%")
print(f"Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
print(f"Total PnL (sum %): {total_pnl:.1f}%")
print(f"Profit Factor: {abs(avg_win*wins/(avg_loss*loss+1e-9)):.2f}")
print(f"\nLast 10 trades:")
for t in trades[-10:]:
    print(f"{t['sym']} {t['result']} PnL {t['pnl']:.1f}% Vol {t['vol']:.1f}x RSI {t['rsi']:.0f}")

# Save best
best=sorted(trades, key=lambda x: x['pnl'], reverse=True)[:5]
print(f"\nTop 5 Best Trades:")
for b in best:
    print(f"{b['sym']} +{b['pnl']:.1f}%")
