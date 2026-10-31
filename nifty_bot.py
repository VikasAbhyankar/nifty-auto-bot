import requests, os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=20)
    except Exception as e:
        print(e)

def get_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    daily_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=30d"
    intraday_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=2d"
    d_json = requests.get(daily_url, headers=headers, timeout=15).json()
    i_json = requests.get(intraday_url, headers=headers, timeout=15).json()
    
    d_result = d_json['chart']['result'][0]
    d_q = d_result['indicators']['quote'][0]
    daily = []
    for i in range(len(d_q['close'])):
        if d_q['close'][i]:
            daily.append({'o':d_q['open'][i],'h':d_q['high'][i],'l':d_q['low'][i],'c':d_q['close'][i]})
    
    prev = daily[-2]
    H,L,C,O = prev['h'],prev['l'],prev['c'],prev['o']
    
    i_result = i_json['chart']['result'][0]
    i_q = i_result['indicators']['quote'][0]
    closes = [c for c in i_q['close'] if c is not None]
    highs = [h for h in i_q['high'] if h is not None]
    lows = [l for l in i_q['low'] if l is not None]
    
    if len(closes)<20:
        closes = [d['c'] for d in daily]
        highs = [d['h'] for d in daily]
        lows = [d['l'] for d in daily]
    
    return H,L,C,O,closes[-1],closes,highs,lows

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
    e12=ema(data,12)
    e26=ema(data,26)
    if not e12 or not e26: return 0,0,0
    macd_line=e12-e26
    macd_hist=[]
    for i in range(9):
        sl = data[:len(data)-i if i>0 else None]
        if len(sl)<26: break
        ee12=ema(sl,12)
        ee26=ema(sl,26)
        if ee12 and ee26: macd_hist.append(ee12-ee26)
    signal=sum(macd_hist)/len(macd_hist) if macd_hist else 0
    hist=macd_line-signal
    return macd_line,signal,hist

def supertrend_calc(closes,highs,lows,period=10,mult=3.0):
    if len(closes)<period+2: return "BULLISH",closes[-1],0
    tr_list=[]
    limit=min(len(closes),len(highs),len(lows))
    for i in range(1,limit):
        h=highs[i]; l=lows[i]; pc=closes[i-1]
        tr=max(h-l,abs(h-pc),abs(l-pc))
        tr_list.append(tr)
    atr=sum(tr_list[-period:])/period if len(tr_list)>=period else (highs[-1]-lows[-1])
    hl2=(highs[-1]+lows[-1])/2 if highs and lows else closes[-1]
    upper=hl2+mult*atr
    lower=hl2-mult*atr
    curr=closes[-1]
    if curr>upper:
        return "BULLISH",lower,atr
    elif curr<lower:
        return "BEARISH",upper,atr
    else:
        trend="BULLISH" if curr>lower else "BEARISH"
        val=lower if trend=="BULLISH" else upper
        return trend,val,atr

try:
    H,L,C,O,curr,closes,highs,lows = get_data()
    P=(H+L+C)/3
    BC=(H+L)/2
    TC=2*P-BC
    R1=2*P-L
    S1=2*P-H
    R2=P+(H-L)
    S2=P-(H-L)
    R3=H+2*(P-L)
    S3=L-2*(H-P)
    rng=H-L
    fR1=P+0.382*rng; fS1=P-0.382*rng
    fR2=P+0.618*rng; fS2=P-0.618*rng
    cam_R4=C+rng*1.1/2; cam_S4=C-rng*1.1/2
    cam_R3=C+rng*1.1/4; cam_S3=C-rng*1.1/4
    
    ema9=ema(closes,9) or curr
    ema21=ema(closes,21) or curr
    ema50=ema(closes,50) or curr
    rsi_val=rsi_calc(closes,14)
    macd_line,signal_line,hist=macd_calc(closes)
    st_trend,st_val,atr=supertrend_calc(closes,highs,lows)
    typical=[(h+l+c)/3 for h,l,c in zip(highs[-50:],lows[-50:],closes[-50:])] if len(highs)>=20 else [P]
    vwap=sum(typical)/len(typical)
    
    cpr_w=abs(TC-BC)
    cpr_pct=cpr_w/P*100
    cpr_status="NARROW (Trend Day)" if cpr_pct<0.2 else "WIDE (Range Day)" if cpr_pct>0.5 else "Normal"
    
    buy=sell=0
    reasons=[]
    
    if curr>TC:
        buy+=2; reasons.append("Above CPR (Bullish)")
    elif curr<BC:
        sell+=2; reasons.append("Below CPR (Bearish)")
    else:
        reasons.append("Inside CPR - Wait")
    
    if st_trend=="BULLISH":
        buy+=2; reasons.append("Supertrend BULLISH "+str(int(st_val)))
    else:
        sell+=2; reasons.append("Supertrend BEARISH "+str(int(st_val)))
    
    if macd_line>signal_line and hist>0:
        buy+=2; reasons.append("MACD Bullish")
    elif macd_line<signal_line and hist<0:
        sell+=2; reasons.append("MACD Bearish")
    else:
        reasons.append("MACD Neutral")
    
    if ema9>ema21 and curr>ema9:
        buy+=1; reasons.append("EMA9 > EMA21 "+str(int(ema9))+" > "+str(int(ema21)))
    elif ema9<ema21 and curr<ema9:
        sell+=1; reasons.append("EMA9 < EMA21 "+str(int(ema9))+" < "+str(int(ema21)))
    
    if curr>vwap:
        buy+=1; reasons.append("Above VWAP "+str(int(vwap)))
    else:
        sell+=1; reasons.append("Below VWAP "+str(int(vwap)))
    
    if rsi_val>=60:
        buy+=1; reasons.append("RSI Strong "+str(int(rsi_val)))
    elif rsi_val<=40:
        sell+=1; reasons.append("RSI Weak "+str(int(rsi_val)))
    else:
        reasons.append("RSI Neutral "+str(int(rsi_val)))
    
    if curr>cam_R4:
        buy+=1; reasons.append("Cam R4 Breakout")
    elif curr<cam_S4:
        sell+=1; reasons.append("Cam S4 Breakdown")
    
    total=buy+sell
    if buy>=6 and buy>sell:
        signal="STRONG BUY ("+str(buy)+"/10)"
        conf=int(buy/total*100) if total else 0
        sl=min(S1,st_val,curr-atr*1.5)
        tgt1=R1; tgt2=R2
        emoji="🟢"
    elif sell>=6 and sell>buy:
        signal="STRONG SELL ("+str(sell)+"/10)"
        conf=int(sell/total*100) if total else 0
        sl=max(R1,st_val,curr+atr*1.5)
        tgt1=S1; tgt2=S2
        emoji="🔴"
    elif buy>sell:
        signal="WEAK BUY ("+str(buy)+"/10)"
        conf=int(buy/total*100) if total else 0
        sl=S1; tgt1=R1; tgt2=R2; emoji="🟡"
    elif sell>buy:
        signal="WEAK SELL ("+str(sell)+"/10)"
        conf=int(sell/total*100) if total else 0
        sl=R1; tgt1=S1; tgt2=S2; emoji="🟠"
    else:
        signal="NO TRADE"; conf=0; sl=S2; tgt1=S1; tgt2=R1; emoji="⚪"
    
    reason_text="\n".join(["- "+r for r in reasons])
    
    msg="""*NIFTY PIVOT BOSS PRO MAX*
Date: """+datetime.now().strftime('%d-%b %I:%M %p')+"""
Prev: H """+str(int(H))+""" L """+str(int(L))+""" C """+str(int(C))+""" | Live """+str(int(curr))+"""

*CPR:* TC """+str(int(TC))+""" P """+str(int(P))+""" BC """+str(int(BC))+""" ("""+cpr_status+""")

*LEVELS:* R3 """+str(int(R3))+""" R2 """+str(int(R2))+""" R1 """+str(int(R1))+""" S1 """+str(int(S1))+""" S2 """+str(int(S2))+""" S3 """+str(int(S3))+"""
Cam R4 """+str(int(cam_R4))+""" S4 """+str(int(cam_S4))+""" Fib R1 """+str(int(fR1))+""" S1 """+str(int(fS1))+"""

*INDICATORS:*
EMA9 """+str(int(ema9))+""" EMA21 """+str(int(ema21))+""" EMA50 """+str(int(ema50))+"""
VWAP """+str(int(vwap))+""" RSI """+str(int(rsi_val))+"""
MACD """+str(round(macd_line,2))+""" Signal """+str(round(signal_line,2))+""" Hist """+str(round(hist,2))+"""
Supertrend """+st_trend+""" """+str(int(st_val))+""" ATR """+str(int(atr))+"""

"""+emoji+""" *"""+signal+"""* - """+str(conf)+"""% Confidence
Buy """+str(buy)+""" vs Sell """+str(sell)+"""

*TRADE PLAN:*
Entry: """+str(int(curr))+"""
SL: """+str(int(sl))+""" ("""+str(int(abs(curr-sl)))+""" pts)
TGT1: """+str(int(tgt1))+""" ("""+str(int(abs(tgt1-curr)))+""" pts)
TGT2: """+str(int(tgt2))+"""

*Confluence:*
"""+reason_text+"""

_Rule: >6 pts = Trade, <4 = No Trade_
"""
    send_telegram(msg)
    print("Sent successfully")

except Exception as e:
    import traceback
    traceback.print_exc()
    send_telegram("Bot Error: "+str(e))

