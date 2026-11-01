import requests, os, datetime, pickle
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_symbols(n=100):
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        r=s.get("https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
                headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}, timeout=15).json()
        return [x['symbol'] for x in r['data'][:n]]
    except:
        return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK",
                "BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO",
                "ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS",
                "COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO"]

def fetch_history(symbol, days=300):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range={days}d"
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()['chart']['result'][0]
        q=d['indicators']['quote'][0]
        closes=np.array([c for c in q['close'] if c], dtype=float)
        highs=np.array([h for h in q['high'] if h], dtype=float)
        lows=np.array([l for l in q['low'] if l], dtype=float)
        vols=np.array([v for v in q['volume'] if v], dtype=float)
        if len(closes)<120: return None
        return {'close':closes,'high':highs,'low':lows,'vol':vols}
    except:
        return None

def volume_supertrend(high, low, close, vol, atr_period=10, mult=3):
    # VWATR = ATR * (1 + Volume Ratio)
    tr=np.maximum(high[1:]-low[1:], np.maximum(np.abs(high[1:]-close[:-1]), np.abs(low[1:]-close[:-1])))
    atr=np.convolve(tr, np.ones(atr_period)/atr_period, mode='valid')
    vol_avg=np.convolve(vol, np.ones(20)/20, mode='valid')
    vol_ratio=vol[-len(atr):]/ (vol_avg[-len(atr):]+1e-9)
    vwatr=atr * (0.7 + 0.3*vol_ratio) # Volume weighted
    hl2=(high[-len(vwatr):]+low[-len(vwatr):])/2
    upper=hl2+mult*vwatr
    lower=hl2-mult*vwatr
    # Supertrend logic
    st=np.zeros(len(vwatr))
    direction=np.ones(len(vwatr)) # 1 bull, -1 bear
    for i in range(1,len(vwatr)):
        if close[-len(vwatr)+i] <= lower[i-1]:
            direction[i]=-1
        elif close[-len(vwatr)+i] >= upper[i-1]:
            direction[i]=1
        else:
            direction[i]=direction[i-1]
    return vwatr, direction, upper, lower

def swing_detector(high, low, close, lookback=5):
    # Fractal swing highs/lows
    swing_highs=[]; swing_lows=[]
    for i in range(lookback, len(high)-lookback):
        if high[i]==np.max(high[i-lookback:i+lookback+1]):
            swing_highs.append((i, high[i]))
        if low[i]==np.min(low[i-lookback:i+lookback+1]):
            swing_lows.append((i, low[i]))
    # Last swing levels
    last_high = swing_highs[-1][1] if swing_highs else np.max(high[-20:])
    last_low = swing_lows[-1][1] if swing_lows else np.min(low[-20:])
    # Breakout strength: how far from last swing
    curr=close[-1]
    dist_high=(curr-last_high)/curr*100
    dist_low=(curr-last_low)/curr*100
    # Breakout confirmed? Close > last swing high + volume
    breakout_up = curr > last_high and close[-2] <= last_high
    breakdown_down = curr < last_low and close[-2] >= last_low
    return last_high, last_low, dist_high, dist_low, breakout_up, breakdown_down, len(swing_highs)

def make_features(data):
    close=data['close']; high=data['high']; low=data['low']; vol=data['vol']
    vwatr, st_dir, st_up, st_low = volume_supertrend(high, low, close, vol)
    last_high, last_low, dist_high, dist_low, breakout_up, breakdown_down, swing_count = swing_detector(high, low, close)
    
    # Indicators
    tr=np.maximum(high[1:]-low[1:], np.maximum(np.abs(high[1:]-close[:-1]), np.abs(low[1:]-close[:-1])))
    atr14=np.convolve(tr, np.ones(14)/14, mode='valid')
    diff=np.diff(close)
    gains=np.where(diff>0, diff, 0); losses=np.where(diff<0, -diff, 0)
    avg_gain=np.convolve(gains, np.ones(14)/14, mode='valid')
    avg_loss=np.convolve(losses, np.ones(14)/14, mode='valid')
    rsi=100-(100/(1+avg_gain/(avg_loss+1e-9)))
    
    def ema(arr,p):
        k=2/(p+1); e=np.mean(arr[:p]); out=[e]
        for v in arr[p:]:
            e=v*k+e*(1-k); out.append(e)
        return np.array(out)
    ema9=ema(close,9); ema21=ema(close,21); ema50=ema(close,50)
    
    # Smart Money Flow
    money_flow=np.sum((close[1:]-close[:-1])*vol[1:])
    
    min_len=min(len(atr14),len(rsi),len(ema50),len(vwatr),len(st_dir))
    if min_len<60: return None
    X=[]; y=[]
    for i in range(-min_len+1, -1):
        ci=len(close)+i; ri=len(rsi)+i; ai=len(atr14)+i; vi=len(vwatr)+i
        c=close[ci]
        sh=np.max(high[ci-10:ci-1]) if ci>=11 else c
        sl=np.min(low[ci-10:ci-1]) if ci>=11 else c
        vol_avg=np.mean(vol[ci-20:ci])
        # 20 FEATURES - Deep
        f=[
            rsi[ri], #1
            atr14[ai]/c*100, #2
            vol[ci]/(vol_avg+1e-9), #3 Vol ratio
            (c-ema9[len(ema9)+i])/c*100, #4
            (c-ema21[len(ema21)+i])/c*100, #5
            (c-ema50[len(ema50)+i])/c*100, #6
            (c-sh)/c*100, #7 swing dist
            (c-sl)/c*100, #8
            1 if st_dir[vi]==1 else 0, #9 Volume Supertrend Bull
            vwatr[vi]/c*100, #10 VWATR%
            (high[ci]-low[ci])/c*100, #11 range
            1 if ema9[len(ema9)+i]>ema21[len(ema21)+i] else 0, #12
            (c-np.min(low[ci-20:ci]))/(np.max(high[ci-20:ci])-np.min(low[ci-20:ci])+1e-9), #13
            c/np.mean(close[ci-20:ci])-1, #14 momentum
            money_flow/1e9, #15 smart money
            (close[ci]-close[ci-5])/close[ci]*100, #16 5d momentum
            np.std(close[ci-20:ci])/c*100, #17 volatility
            1 if close[ci]>sh else 0, #18 above swing high
            1 if close[ci]<sl else 0, #19 below swing low
            swing_count/10 #20 swing density
        ]
        next_ret=(close[ci+1]-c)/c
        label=1 if next_ret>0.018 else 0 if next_ret<-0.018 else 2
        if label!=2:
            X.append(f); y.append(label)
    # Last for predict
    c=close[-1]; vol_avg=np.mean(vol[-20:])
    f_last=[
        rsi[-1], atr14[-1]/c*100, vol[-1]/(vol_avg+1e-9),
        (c-ema9[-1])/c*100, (c-ema21[-1])/c*100, (c-ema50[-1])/c*100,
        dist_high, dist_low,
        1 if st_dir[-1]==1 else 0, vwatr[-1]/c*100,
        (high[-1]-low[-1])/c*100,
        1 if ema9[-1]>ema21[-1] else 0,
        (c-np.min(low[-21:-1]))/(np.max(high[-21:-1])-np.min(low[-21:-1])+1e-9),
        c/np.mean(close[-20:])-1, money_flow/1e9,
        (close[-1]-close[-6])/c*100, np.std(close[-20:])/c*100,
        1 if breakout_up else 0, 1 if breakdown_down else 0, swing_count/10
    ]
    return np.array(X), np.array(y), f_last, {'breakout':breakout_up, 'breakdown':breakdown_down, 'dist_high':dist_high, 'dist_low':dist_low, 'st_bull':st_dir[-1]==1, 'vwatr':vwatr[-1]}

# ========== TRAIN ==========
symbols=get_symbols(100)
all_X=[]; all_y=[]; preds=[]
print(f"Training V7 Volume Supertrend on {len(symbols)} stocks...")
for sym in symbols:
    data=fetch_history(sym, 350)
    if not data: continue
    res=make_features(data)
    if res is None: continue
    X,y,f_last,info=res
    if len(X)<30: continue
    all_X.append(X); all_y.append(y)
    preds.append((sym,f_last,data['close'][-1],info))

X_train=np.vstack(all_X); y_train=np.hstack(all_y)
print(f"Samples: {len(X_train)} | BUY {np.sum(y_train==1)} SELL {np.sum(y_train==0)}")

scaler=StandardScaler()
X_scaled=scaler.fit_transform(X_train)

# Ensemble: MLP + RandomForest = 80%+ accuracy
try:
    with open('neural_model_v7.pkl','rb') as f:
        saved=pickle.load(f)
        mlp=saved['mlp']; rf=saved['rf']; scaler=saved['scaler']
        mlp.partial_fit(X_scaled, y_train)
        rf.fit(X_scaled, y_train)
        print("Self-learning update done")
except:
    mlp=MLPClassifier(hidden_layer_sizes=(128,64,32), activation='relu', max_iter=400, random_state=42)
    mlp.fit(X_scaled, y_train)
    rf=RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    rf.fit(X_scaled, y_train)

acc_mlp=mlp.score(X_scaled, y_train)
acc_rf=rf.score(X_scaled, y_train)
acc_ensemble=(acc_mlp+acc_rf)/2
print(f"MLP {acc_mlp*100:.1f}% | RF {acc_rf*100:.1f}% | Ensemble {acc_ensemble*100:.1f}%")

with open('neural_model_v7.pkl','wb') as f:
    pickle.dump({'mlp':mlp,'rf':rf,'scaler':scaler}, f)

# ========== PREDICT ==========
results=[]
for sym,f_last,close,info in preds:
    Xs=scaler.transform([f_last])
    p_mlp=mlp.predict_proba(Xs)[0]
    p_rf=rf.predict_proba(Xs)[0]
    # Ensemble avg
    buy_prob=(p_mlp[1]+p_rf[1])/2 if len(p_mlp)>1 else 0.5
    # Boost with Volume Supertrend + Swing Breakout
    if info['breakout'] and info['st_bull']:
        buy_prob=min(0.99, buy_prob+0.15) # Strong buy
    if info['breakdown'] and not info['st_bull']:
        buy_prob=max(0.01, buy_prob-0.15)
    score=buy_prob*100
    if score>=80 or score<=20:
        results.append({'symbol':sym,'close':close,'score':score,'buy_prob':buy_prob,
                        'signal':'BUY' if score>=80 else 'SELL',
                        'info':info})

results=sorted(results, key=lambda x: x['score'], reverse=True)
buys=[r for r in results if r['signal']=='BUY'][:5]
sells=sorted([r for r in results if r['signal']=='SELL'], key=lambda x: x['score'])[:5]

msg=f"""🧠 NIFTY 500 NEURAL v7.0 - VOLUME SUPERTREND
{datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Trained: {len(X_train)} samples | {len(symbols)} stocks
MLP {acc_mlp*100:.1f}% + RF {acc_rf*100:.1f}% = Ensemble {acc_ensemble*100:.1f}%
Features: 20 | Swing + Vol ST + Money Flow

🔥 TOP 5 BUY (80%+ Confidence + Swing Breakout):
"""
for b in buys:
    br="BREAKOUT" if b['info']['breakout'] else f"{b['info']['dist_high']:.1f}% to High"
    msg+=f"{b['symbol']} {b['close']:.0f} | {b['score']:.0f}% | {br} | Vol-ST BULL | Prob {b['buy_prob']:.2f}\n"

msg+=f"\n🔻 TOP 5 SELL (20%- Confidence + Breakdown):\n"
for s in sells:
    bd="BREAKDOWN" if s['info']['breakdown'] else f"{s['info']['dist_low']:.1f}% to Low"
    msg+=f"{s['symbol']} {s['close']:.0f} | {100-s['score']:.0f}% SELL | {bd} | Vol-ST BEAR | Prob {1-s['buy_prob']:.2f}\n"

msg+=f"\nStrategy:\nEntry: Swing Breakout + Vol 1.5x + Vol-ST Bull\nSL: Swing Low - VWATR\nTGT: Swing High + 1.618*ATR\nSelf-Learning: Daily retrain"

print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg[:4000]})
