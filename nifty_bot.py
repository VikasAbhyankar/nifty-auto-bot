import requests, os, datetime, csv

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def fetch_yahoo_1y():
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1y"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()['chart']['result'][0]
    q=d['indicators']['quote'][0]
    ts=d['timestamp']
    history=[]
    for i in range(len(q['close'])):
        if q['close'][i]:
            dt=datetime.datetime.fromtimestamp(ts[i]).strftime("%d-%b-%Y")
            history.append({
                'date':dt,
                'open':round(float(q['open'][i]),2),
                'high':round(float(q['high'][i]),2),
                'low':round(float(q['low'][i]),2),
                'close':round(float(q['close'][i]),2)
            })
    return history

def fetch_live():
    # Try NSE live, if blocked use Yahoo live
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}, timeout=5)
        url="https://www.nseindia.com/api/allIndices"
        r=s.get(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}, timeout=5).json()
        for idx in r['data']:
            if idx['index']=='NIFTY 50':
                return float(idx['last']), "NSE"
    except:
        pass
    # Yahoo live
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()['chart']['result'][0]
    return float(d['meta']['regularMarketPrice']), "Yahoo"

history = fetch_yahoo_1y()
live_price, src = fetch_live()

# Save CSV
with open('nifty_oct25_oct26.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['date','open','high','low','close'])
    w.writeheader()
    w.writerows(history)

prev=history[-2]
H,L,C=prev['high'],prev['low'],prev['close']
P=(H+L+C)/3; BC=(H+L)/2; TC=2*P-BC
R1=2*P-L; S1=2*P-H; R2=P+(H-L); S2=P-(H-L); R3=H+2*(P-L); S3=L-2*(H-P)

closes=[x['close'] for x in history]
def ema(data,p):
    k=2/(p+1); e=sum(data[:p])/p
    for v in data[p:]: e=v*k+e*(1-k)
    return e
ema9=ema(closes,9); ema21=ema(closes,21); ema50=ema(closes,50)
g=l=0
for i in range(len(closes)-14,len(closes)):
    d=closes[i]-closes[i-1]
    if d>0: g+=d
    else: l+=abs(d)
rsi=100-(100/(1+g/l if l else 1)) if l else 65

st="BULLISH" if live_price>ema50 else "BEARISH"
buy=sell=0; reasons=[]
if live_price>TC: buy+=3; reasons.append(f"Above TC {TC:.0f}")
elif live_price<BC: sell+=3; reasons.append(f"Below BC {BC:.0f}")
else: reasons.append(f"Inside CPR {BC:.0f}-{TC:.0f}")

if st=="BULLISH" and live_price>ema21: buy+=2; reasons.append("ST Bull + >EMA21")
elif st=="BEARISH" and live_price<ema21: sell+=2; reasons.append("ST Bear + <EMA21")

if ema9>ema21 and live_price>ema9: buy+=2; reasons.append("EMA9>21 Bull")
elif ema9<ema21 and live_price<ema9: sell+=2; reasons.append("EMA9<21 Bear")

if 55<=rsi<=68: buy+=2; reasons.append(f"RSI Bull {rsi:.0f}")
elif 32<=rsi<=45: sell+=2; reasons.append(f"RSI Bear {rsi:.0f}")
else: reasons.append(f"RSI {rsi:.0f} Neutral")

score=max(buy,sell)
if buy>=8: sig="🟢 STRONG BUY"; sl=live_price-80; t1=live_price+120; t2=live_price+200
elif sell>=8: sig="🔴 STRONG SELL"; sl=live_price+80; t1=live_price-120; t2=live_price-200
elif buy>=6: sig="🟡 WEAK BUY - NO TRADE"; sl=live_price-80; t1=live_price+80; t2=live_price+120
elif sell>=6: sig="🟡 WEAK SELL - NO TRADE"; sl=live_price+80; t1=live_price-80; t2=live_price-120
else: sig="⚪ NO TRADE - RANGE"; sl=live_price-80; t1=live_price+60; t2=live_price+120

msg=f"""NIFTY PIVOT BOSS 5.1 FINAL
Date: {datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Source: {src} Live

HISTORY: Oct 2025 to Today - {len(history)} days
Saved: nifty_oct25_oct26.csv
From {history[0]['date']} to {history[-1]['date']}

Yesterday: H {H:.0f} L {L:.0f} C {C:.0f}
Live: {live_price:.0f}

CPR: TC {TC:.0f} P {P:.0f} BC {BC:.0f}
LEVELS: R3 {R3:.0f} R2 {R2:.0f} R1 {R1:.0f} | S1 {S1:.0f} S2 {S2:.0f} S3 {S3:.0f}

EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f}
RSI {rsi:.0f} Supertrend {st}

{sig} ({score}/10)
Buy {buy} vs Sell {sell}

TRADE: Entry {live_price:.0f} SL {sl:.0f} TGT1 {t1:.0f} TGT2 {t2:.0f}
RR 1:1.5

Reasons: {' | '.join(reasons)}

Auto-Update: Daily 9:15 AM IST
Rule: Trade only 8+/10
"""
print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})
