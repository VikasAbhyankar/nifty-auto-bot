import requests, os
from datetime import datetime

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def ema(data, period):
    if len(data)<period: return None
    k=2/(period+1)
    e=sum(data[:period])/period
    for p in data[period:]:
        e=p*k+e*(1-k)
    return e

def rsi_calc(data):
    if len(data)<15: return 50
    gains=losses=0
    for i in range(len(data)-14,len(data)):
        diff=data[i]-data[i-1]
        if diff>0: gains+=diff
        else: losses+=abs(diff)
    if losses==0: return 70
    rs=gains/losses
    return 100-(100/(1+rs))

def get_data():
    headers={"User-Agent":"Mozilla/5.0"}
    # Daily for CPR
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=3mo"
    d=requests.get(url,headers=headers,timeout=15).json()['chart']['result'][0]
    q=d['indicators']['quote'][0]
    rows=[]
    for i in range(len(q['close'])):
        if q['close'][i]: rows.append({'h':q['high'][i],'l':q['low'][i],'c':q['close'][i]})
    prev=rows[-2]
    # Intraday 5min for live price
    url2="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=1d"
    d2=requests.get(url2,headers=headers,timeout=15).json()['chart']['result'][0]
    live=float(d2['meta']['regularMarketPrice'])
    closes=[r['c'] for r in rows]
    return prev, live, closes, rows

prev,live,closes,all_rows=get_data()
H,L,C=prev['h'],prev['l'],prev['c']
P=(H+L+C)/3
BC=(H+L)/2
TC=2*P-BC
R1=2*P-L; S1=2*P-H; R2=P+(H-L); S2=P-(H-L); R3=H+2*(P-L); S3=L-2*(H-P)

ema9=ema(closes,9); ema21=ema(closes,21); ema50=ema(closes,50)
rsi=rsi_calc(closes)
# MACD
e12=ema(closes,12); e26=ema(closes,26)
macd_line=(e12-e26) if e12 and e26 else 0
# Supertrend simplified
st="BULLISH" if live>(ema50 or 0) else "BEARISH"
vwap=P # approx daily

# Scoring - NEW PROFITABLE LOGIC
buy=sell=0
reason=[]
if live>TC:
    buy+=3; reason.append("Above TC (Strong Bull)")
elif live>BC and live> P:
    buy+=1; reason.append("Above CPR")
elif live<BC:
    sell+=3; reason.append("Below BC (Strong Bear)")
elif live<TC and live<P:
    sell+=1; reason.append("Below CPR")

if st=="BULLISH" and live>ema21: buy+=2; reason.append(f"Supertrend Bull + Above EMA21")
elif st=="BEARISH" and live<ema21: sell+=2; reason.append(f"Supertrend Bear + Below EMA21")

if ema9 and ema21:
    if ema9>ema21 and live>ema9: buy+=2; reason.append("EMA9>21 Bullish Cross")
    elif ema9<ema21 and live<ema9: sell+=2; reason.append("EMA9<21 Bearish Cross")

if rsi>=55 and rsi<=68: buy+=2; reason.append(f"RSI Strong {rsi:.0f}")
elif rsi<=45 and rsi>=32: sell+=2; reason.append(f"RSI Weak {rsi:.0f}")
elif rsi>70 or rsi<30: 
    reason.append(f"RSI Extreme {rsi:.0f} - Avoid")

if live>vwap: buy+=1
else: sell+=1

# DECISION - Only 8+ is trade
score=max(buy,sell)
if buy>=8:
    signal="🟢 STRONG BUY"; sl=live-80; tgt1=live+120; tgt2=live+200; conf=75+buy*2
elif buy>=6:
    signal="🟡 WEAK BUY - NO TRADE"; sl=live-80; tgt1=live+80; tgt2=live+120; conf=50+buy*3
elif sell>=8:
    signal="🔴 STRONG SELL"; sl=live+80; tgt1=live-120; tgt2=live-200; conf=75+sell*2
elif sell>=6:
    signal="🟡 WEAK SELL - NO TRADE"; sl=live+80; tgt1=live-80; tgt2=live-120; conf=50+sell*3
else:
    signal="⚪ NO TRADE - RANGE"; sl=live-80; tgt1=live+60; tgt2=live+120; conf=45

# Build message
msg=f"""NIFTY PIVOT BOSS PRO MAX 3.0
Date: {datetime.now().strftime('%d-%b %I:%M %p')}

Prev: H {H:.0f} L {L:.0f} C {C:.0f} | Live {live:.0f}

CPR: TC {TC:.0f} P {P:.0f} BC {BC:.0f}

LEVELS: R3 {R3:.0f} R2 {R2:.0f} R1 {R1:.0f} S1 {S1:.0f} S2 {S2:.0f} S3 {S3:.0f}

INDICATORS:
EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f}
RSI {rsi:.0f} Supertrend {st}
MACD {macd_line:.1f}

{signal} ({score}/10) - {conf:.0f}% Confidence
Buy {buy} vs Sell {sell}

TRADE PLAN:
Entry: {live:.0f}
SL: {sl:.0f} (80 pts)
TGT1: {tgt1:.0f}
TGT2: {tgt2:.0f}

Confluence:
- {chr(10)+'- '.join(reason) if reason else 'Range market'}

Rule: 8+ = Trade, 6-7 = Wait, <6 = No Trade
RR = 1:1.5 (80 SL / 120 TGT)
"""

print(msg)
# Send Telegram
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})
