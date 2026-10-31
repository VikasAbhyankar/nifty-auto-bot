import requests

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
    if losses==0: return 70
    rs=gains/losses if losses else 0
    return 100-(100/(1+rs))

def macd_calc(data):
    if len(data)<35: return 0,0,0
    e12=ema(data,12); e26=ema(data,26)
    if not e12 or not e26: return 0,0,0
    ml=e12-e26
    hist=[]
    for i in range(9):
        sl=data[:len(data)-i if i>0 else None]
        if len(sl)<26: break
        ee12=ema(sl,12); ee26=ema(sl,26)
        if ee12 and ee26: hist.append(ee12-ee26)
    sig=sum(hist)/len(hist) if hist else 0
    return ml,sig,ml-sig

def atr_calc(highs,lows,closes,period=14):
    if len(closes)<period+1: return 100
    trs=[]
    for i in range(1,len(closes)):
        if i>=len(highs) or i>=len(lows): continue
        h=highs[i]; l=lows[i]; pc=closes[i-1]
        tr=max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    return sum(trs[-period:])/period if trs else 100

print("Fetching...")
headers={"User-Agent":"Mozilla/5.0"}
url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1y"
data=requests.get(url,headers=headers,timeout=15).json()
result=data['chart']['result'][0]
q=result['indicators']['quote'][0]
rows=[]
for i in range(len(q['close'])):
    if q['close'][i]:
        rows.append({'o':q['open'][i],'h':q['high'][i],'l':q['low'][i],'c':q['close'][i]})
print(f"Days: {len(rows)}")

trades=[]; wins=losses=0; total_pnl=0

for idx in range(50, len(rows)-1):
    prev=rows[idx-1]; curr_day=rows[idx]; next_day=rows[idx+1]
    H,L,C=prev['h'],prev['l'],prev['c']
    P=(H+L+C)/3; BC=(H+L)/2; TC=2*P-BC
    
    closes=[r['c'] for r in rows[:idx]]
    highs=[r['h'] for r in rows[:idx]]
    lows=[r['l'] for r in rows[:idx]]
    
    ema9=ema(closes,9) or closes[-1]
    ema21=ema(closes,21) or closes[-1]
    rsi_val=rsi_calc(closes,14)
    ml,sig,hist=macd_calc(closes)
    atr=atr_calc(highs,lows,closes,14)
    st="BULLISH" if closes[-1]>(ema(closes,50) or 0) else "BEARISH"
    
    curr=curr_day['o']
    buy=sell=0
    if curr>TC: buy+=2
    elif curr<BC: sell+=2
    if st=="BULLISH": buy+=2
    else: sell+=2
    if ml>sig and hist>0: buy+=2
    elif ml<sig and hist<0: sell+=2
    if ema9>ema21 and curr>ema9: buy+=1
    elif ema9<ema21 and curr<ema9: sell+=1
    if curr>P: buy+=1
    else: sell+=1
    if rsi_val>=55 and rsi_val<=68: buy+=1
    elif rsi_val<=45 and rsi_val>=32: sell+=1
    
    # NEW FILTER: Only 8+ score and RSI not extreme
    if rsi_val>70 or rsi_val<30:
        continue
    
    signal="NONE"
    if buy>=8:
        signal="BUY"
        sl=curr-atr*1.2
        tgt=curr+atr*2.4
    elif sell>=8:
        signal="SELL"
        sl=curr+atr*1.2
        tgt=curr-atr*2.4
    else:
        continue
    
    # Check result
    h=next_day['h']; l=next_day['l']
    pnl=0
    if signal=="BUY":
        if l<=sl:
            pnl=sl-curr; losses+=1; res="LOSS"
        elif h>=tgt:
            pnl=tgt-curr; wins+=1; res="WIN"
        else:
            pnl=next_day['c']-curr
            if pnl>0: wins+=1; res="WIN"
            else: losses+=1; res="LOSS"
    else:
        if h>=sl:
            pnl=curr-sl; losses+=1; res="LOSS"
        elif l<=tgt:
            pnl=curr-tgt; wins+=1; res="WIN"
        else:
            pnl=curr-next_day['c']
            if pnl>0: wins+=1; res="WIN"
            else: losses+=1; res="LOSS"
    
    total_pnl+=pnl
    trades.append({'signal':signal,'score':f"{buy if signal=='BUY' else sell}/10",'entry':int(curr),'pnl':int(pnl),'result':res,'rsi':int(rsi_val),'atr':int(atr)})

print("\n======== BACKTEST PRO MAX 2.0 ========")
print(f"Total Trades (Score >=8): {len(trades)}")
print(f"Wins: {wins} | Losses: {losses}")
if trades:
    wr=wins/len(trades)*100
    print(f"Win Rate: {wr:.1f}%")
    print(f"Total P&L: {int(total_pnl)} pts")
    print(f"Avg per trade: {total_pnl/len(trades):.1f} pts")
    wp=sum([t['pnl'] for t in trades if t['result']=="WIN"])
    lp=abs(sum([t['pnl'] for t in trades if t['result']=="LOSS"]))
    pf=wp/lp if lp else 0
    print(f"Profit Factor: {pf:.2f}")
    print("\nLast 15 Trades:")
    for t in trades[-15:]:
        print(f"{t['signal']} {t['score']} RSI {t['rsi']} ATR {t['atr']} PnL {t['pnl']} {t['result']}")
    if wr>=55 and pf>=1.3:
        print("\nVERDICT: PROFITABLE ✅ Ready for Live")
    else:
        print("\nVERDICT: Still needs filter")
else:
    print("No trades with 8+ filter - Market choppy")
