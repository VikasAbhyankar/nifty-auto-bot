import requests
from datetime import datetime

def ema(data, period):
    if len(data)<period: return None
    k=2/(period+1)
    e=sum(data[:period])/period
    for p in data[period:]:
        e=p*k+e*(1-k)
    return e

def rsi_calc(data, period=14):
    if len(data)<period+1: return 50
    gains=losses=0
    for i in range(len(data)-period,len(data)):
        if i<=0: continue
        diff=data[i]-data[i-1]
        if diff>0: gains+=diff
        else: losses+=abs(diff)
    if losses==0: return 75
    rs=gains/losses if losses else 0
    return 100-(100/(1+rs))

def macd_calc(data):
    if len(data)<35: return 0,0,0
    e12=ema(data,12); e26=ema(data,26)
    if not e12 or not e26: return 0,0,0
    macd_line=e12-e26
    hist=[]
    for i in range(9):
        sl=data[:len(data)-i if i>0 else None]
        if len(sl)<26: break
        ee12=ema(sl,12); ee26=ema(sl,26)
        if ee12 and ee26: hist.append(ee12-ee26)
    signal=sum(hist)/len(hist) if hist else 0
    return macd_line,signal,macd_line-signal

def supertrend_trend(closes):
    e50=ema(closes,50)
    if not e50: return "BULLISH"
    return "BULLISH" if closes[-1]>e50 else "BEARISH"

# Fetch 1 year daily data
print("Fetching Nifty data...")
headers={"User-Agent":"Mozilla/5.0"}
url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1y"
try:
    data=requests.get(url,headers=headers,timeout=15).json()
    result=data['chart']['result'][0]
    q=result['indicators']['quote'][0]
    rows=[]
    for i in range(len(q['close'])):
        if q['close'][i]:
            rows.append({'o':q['open'][i],'h':q['high'][i],'l':q['low'][i],'c':q['close'][i]})
    print(f"Total days fetched: {len(rows)}")
except Exception as e:
    print(f"Data fetch failed: {e}")
    exit(1)

trades=[]
wins=losses=0
total_pnl=0

for idx in range(30, len(rows)-1):
    prev=rows[idx-1]
    curr_day=rows[idx]
    next_day=rows[idx+1]
    
    H,L,C=prev['h'],prev['l'],prev['c']
    P=(H+L+C)/3
    BC=(H+L)/2
    TC=2*P-BC
    R1=2*P-L; S1=2*P-H; R2=P+(H-L); S2=P-(H-L)
    
    closes=[r['c'] for r in rows[:idx]]
    
    ema9=ema(closes,9) or closes[-1]
    ema21=ema(closes,21) or closes[-1]
    rsi_val=rsi_calc(closes,14)
    macd_line,sig,hist=macd_calc(closes)
    st_trend=supertrend_trend(closes)
    
    curr= curr_day['o']
    
    buy=sell=0
    if curr>TC: buy+=2
    elif curr<BC: sell+=2
    
    if st_trend=="BULLISH": buy+=2
    else: sell+=2
    
    if macd_line>sig and hist>0: buy+=2
    elif macd_line<sig and hist<0: sell+=2
    
    if ema9>ema21 and curr>ema9: buy+=1
    elif ema9<ema21 and curr<ema9: sell+=1
    
    if curr>P: buy+=1
    else: sell+=1
    
    if rsi_val>=60: buy+=1
    elif rsi_val<=40: sell+=1
    
    signal="NONE"
    entry=curr
    sl=tgt=0
    
    if buy>=6:
        signal="BUY"
        sl=S1
        tgt=R1
    elif sell>=6:
        signal="SELL"
        sl=R1
        tgt=S1
    
    if signal!="NONE":
        high=next_day['h']; low=next_day['l']
        pnl=0
        result="LOSS"
        if signal=="BUY":
            if high>=tgt:
                pnl=tgt-entry
                result="WIN"
                wins+=1
            elif low<=sl:
                pnl=sl-entry
                result="LOSS"
                losses+=1
            else:
                pnl=next_day['c']-entry
                result="WIN" if pnl>0 else "LOSS"
                if pnl>0: wins+=1
                else: losses+=1
        else:
            if low<=tgt:
                pnl=entry-tgt
                result="WIN"
                wins+=1
            elif high>=sl:
                pnl=entry-sl
                result="LOSS"
                losses+=1
            else:
                pnl=entry-next_day['c']
                result="WIN" if pnl>0 else "LOSS"
                if pnl>0: wins+=1
                else: losses+=1
        
        total_pnl+=pnl
        trades.append({'signal':signal,'entry':int(entry),'sl':int(sl),'tgt':int(tgt),'pnl':int(pnl),'result':result,'score':f"{buy if signal=='BUY' else sell}/10"})

print("\n======== BACKTEST RESULT (Same Bot Logic) ========")
print(f"Total Trades (Score >=6): {len(trades)}")
print(f"Wins: {wins} | Losses: {losses}")
if len(trades)>0:
    wr=wins/len(trades)*100
    print(f"Win Rate: {wr:.1f}%")
    print(f"Total Points P&L: {int(total_pnl)} pts")
    print(f"Avg P&L per trade: {total_pnl/len(trades):.1f} pts")
    
    print("\nLast 20 Trades:")
    for t in trades[-20:]:
        print(f"{t['signal']} {t['score']} Entry {t['entry']} TGT {t['tgt']} SL {t['sl']} -> {t['result']} {t['pnl']}")

    win_pnl=sum([t['pnl'] for t in trades if t['result']=="WIN"])
    loss_pnl=abs(sum([t['pnl'] for t in trades if t['result']=="LOSS"]))
    pf=win_pnl/loss_pnl if loss_pnl else 0
    print(f"\nProfit Factor: {pf:.2f} ( >1.5 is Good)")
    if wr>=60 and pf>=1.5:
        print("VERDICT: STRATEGY IS PROFITABLE ✅")
    else:
        print("VERDICT: NEEDS IMPROVEMENT - I will optimize")
