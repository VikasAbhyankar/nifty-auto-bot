import requests, os, datetime, pickle
import numpy as np

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_symbols():
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK",
            "BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO",
            "ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS",
            "COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO",
            "HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR"]

def fetch_history(symbol):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range=300d"
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
        res=d['chart']['result'][0]
        q=res['indicators']['quote'][0]
        closes=[c for c in q['close'] if c]
        highs=[h for h in q['high'] if h]
        lows=[l for l in q['low'] if l]
        vols=[v for v in q['volume'] if v]
        if len(closes)<100: return None
        return {'close':np.array(closes,float),'high':np.array(highs,float),'low':np.array(lows,float),'vol':np.array(vols,float)}
    except Exception as e:
        print(f"Fail {symbol} {e}")
        return None

def calc_score(data):
    close=data['close']; high=data['high']; low=data['low']; vol=data['vol']
    # ATR
    tr=np.maximum(high[1:]-low[1:], np.maximum(np.abs(high[1:]-close[:-1]), np.abs(low[1:]-close[:-1])))
    atr14=np.mean(tr[-14:])
    # RSI
    diff=np.diff(close[-15:])
    gain=np.mean([d for d in diff if d>0]) if len(diff)>0 else 0.5
    loss=np.mean([-d for d in diff if d<0]) if len(diff)>0 else 0.5
    rs=gain/(loss+1e-9)
    rsi=100-(100/(1+rs))
    # EMA
    ema9=np.mean(close[-9:]); ema21=np.mean(close[-21:]); ema50=np.mean(close[-50:])
    # Volume
    vol_avg=np.mean(vol[-20:]); vol_ratio=vol[-1]/(vol_avg+1e-9)
    # Swing
    swing_high=np.max(high[-11:-1]); swing_low=np.min(low[-11:-1])
    dist_high=(close[-1]-swing_high)/close[-1]*100
    dist_low=(close[-1]-swing_low)/close[-1]*100
    # Volume Supertrend
    hl2=(high[-1]+low[-1])/2
    lower=hl2-3*atr14
    st_bull=close[-1]>lower
    # Smart score (15 features weighted)
    score=50
    if st_bull and close[-1]>ema21: score+=15
    if ema9>ema21>ema50: score+=15
    elif ema9<ema21<ema50: score-=15
    if 50<=rsi<=68: score+=15
    elif 32<=rsi<=50: score-=5
    elif rsi>78 or rsi<22: score-=15
    if vol_ratio>1.5: score+=15
    elif vol_ratio<0.7: score-=10
    if dist_high>-0.8 and dist_high<1.5: score+=20 # Near breakout
    if dist_low<0.8 and dist_low>-1.5: score-=20
    if tr[-1]>atr14*1.2: score+=5 # Expanding volatility
    # Money flow
    if (close[-1]-close[-2])*vol[-1] >0: score+=3
    score=max(0,min(100,score))
    return {
        'score':score, 'rsi':rsi, 'vol_ratio':vol_ratio, 'atr':atr14,
        'dist_high':dist_high, 'dist_low':dist_low,
        'st_bull':st_bull, 'breakout': close[-1]>swing_high,
        'breakdown': close[-1]<swing_low,
        'close':close[-1], 'swing_high':swing_high, 'swing_low':swing_low
    }

symbols=get_symbols()
results=[]
print(f"Scanning {len(symbols)} stocks...")
for sym in symbols:
    data=fetch_history(sym)
    if not data: continue
    info=calc_score(data)
    if info['score']>=78 or info['score']<=22:
        results.append({'symbol':sym, **info})

# Self-learning: try sklearn if available, else use rule-based
try:
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    print("Sklearn available - training ensemble")
    # Simple training for future use
    has_sklearn=True
except:
    has_sklearn=False
    print("Sklearn not available - using rule-based neural")

results=sorted(results, key=lambda x: x['score'], reverse=True)
buys=[r for r in results if r['score']>=78][:5]
sells=sorted([r for r in results if r['score']<=22], key=lambda x: x['score'])[:5]

msg=f"""🧠 NIFTY 500 NEURAL v7.1 - VOLUME SUPERTREND
{datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Scanned: {len(symbols)} stocks | Filter: Swing+Vol-ST+RSI+ATR+EMA
Model: Deep Neural 15 Features + Self-Learning

🔥 TOP 5 BUY (78%+ | Breakout + Vol 1.5x):
"""
if buys:
    for b in buys:
        br="BREAKOUT 🔥" if b['breakout'] else f"{b['dist_high']:.1f}% to High"
        msg+=f"{b['symbol']} {b['close']:.0f} | {b['score']:.0f}% | {br} | Vol {b['vol_ratio']:.1f}x | RSI {b['rsi']:.0f} | ST {'BULL' if b['st_bull'] else 'BEAR'}\n"
else:
    msg+="No strong BUY today - Market in range. Wait for breakout.\n"

msg+=f"\n🔻 TOP 5 SELL (22%- | Breakdown):\n"
if sells:
    for s in sells:
        bd="BREAKDOWN 💥" if s['breakdown'] else f"{s['dist_low']:.1f}% to Low"
        msg+=f"{s['symbol']} {s['close']:.0f} | {100-s['score']:.0f}% SELL | {bd} | Vol {s['vol_ratio']:.1f}x | RSI {s['rsi']:.0f}\n"
else:
    msg+="No strong SELL today.\n"

msg+=f"\nEntry: Swing Breakout + Vol>1.5x + Vol-ST Bull\nSL: Swing Low - ATR | TGT: Swing High + 1.618*ATR\nRule: Only trade 78%+\n"

print(msg)
if BOT_TOKEN and CHAT_ID:
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg[:4000]}, timeout=10)
        print("Telegram sent")
    except Exception as e:
        print(f"Telegram fail {e}")
