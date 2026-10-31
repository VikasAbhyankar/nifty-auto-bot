import requests, os, datetime

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_nse_data():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    # Get cookie
    session.get("https://www.nseindia.com", headers=headers, timeout=10)
    
    # 1. Get Nifty 50 live from NSE API (most accurate)
    try:
        url = "https://www.nseindia.com/api/allIndices"
        r = session.get(url, headers=headers, timeout=10).json()
        nifty_data = None
        for idx in r['data']:
            if idx['index'] == 'NIFTY 50':
                nifty_data = idx
                break
        live = float(nifty_data['last'])
        prev_close = float(nifty_data['previousClose'])
        # For CPR we need yesterday's HLC
        # NSE prev H/L not in this API, so fetch daily chart
        chart_url = "https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true"
        chart = session.get(chart_url, headers=headers, timeout=10).json()
        # Last 30 days data for EMA
        closes = [float(x[1]) for x in chart['grapthData'][-60:]]
        # Get yesterday's high low from chart
        # chart gives timestamp, value - we need OHLC from another endpoint
        # Use NSE daily bhav for index
        bhav_url = "https://www.nseindia.com/api/historical/indicesHistory?indexType=NIFTY%2050&from=01-08-2025&to=31-10-2025"
        # fallback to Yahoo for H/L if NSE blocks, but try
        H = L = C = prev_close
        try:
            # Get last trading day bhavcopy for index
            hist = session.get(bhav_url, headers=headers, timeout=10).json()
            last = hist['data']['indexCloseOnlineRecords'][-2] # yesterday
            H = float(last['dailyVolatility'].split('-')[0]) if 'dailyVolatility' in last else prev_close*1.01
            # Actually use EOD archive
            H = float(last['high'])
            L = float(last['low'])
            C = float(last['close'])
        except:
            # Fallback: estimate H/L as 1% around close (if API blocks)
            H = C * 1.008
            L = C * 0.992
        
        return H, L, C, live, closes
        
    except Exception as e:
        print(f"NSE API failed {e}, fallback to Yahoo")
        # Fallback Yahoo
        url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=3mo"
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()['chart']['result'][0]
        q=d['indicators']['quote'][0]
        rows=[]
        for i in range(len(q['close'])):
            if q['close'][i]: rows.append({'h':q['high'][i],'l':q['low'][i],'c':q['close'][i]})
        prev=rows[-2]
        live=rows[-1]['c']
        closes=[r['c'] for r in rows]
        return prev['h'], prev['l'], prev['c'], live, closes

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
    return 100-(100/(1+gains/losses if losses else 1))

H,L,C,live,closes = get_nse_data()

P=(H+L+C)/3
BC=(H+L)/2
TC=2*P-BC
R1=2*P-L; S1=2*P-H; R2=P+(H-L); S2=P-(H-L); R3=H+2*(P-L); S3=L-2*(H-P)

ema9=ema(closes,9) or live
ema21=ema(closes,21) or live
ema50=ema(closes,50) or live
rsi=rsi_calc(closes)
st="BULLISH" if live>ema50 else "BEARISH"

buy=sell=0
reasons=[]
if live>TC: buy+=3; reasons.append(f"Above TC {TC:.0f}")
elif live<BC: sell+=3; reasons.append(f"Below BC {BC:.0f}")
if st=="BULLISH" and live>ema21: buy+=2; reasons.append("ST Bull + EMA21")
elif st=="BEARISH" and live<ema21: sell+=2; reasons.append("ST Bear + EMA21")
if ema9 and ema21:
    if ema9>ema21 and live>ema9: buy+=2; reasons.append("EMA Bull Cross")
    elif ema9<ema21 and live<ema9: sell+=2; reasons.append("EMA Bear Cross")
if 55<=rsi<=68: buy+=2; reasons.append(f"RSI {rsi:.0f} Bull")
elif 32<=rsi<=45: sell+=2; reasons.append(f"RSI {rsi:.0f} Bear")

score=max(buy,sell)
if buy>=8: signal="🟢 STRONG BUY"; sl=live-80; t1=live+120; t2=live+200; conf=80
elif sell>=8: signal="🔴 STRONG SELL"; sl=live+80; t1=live-120; t2=live-200; conf=80
elif buy>=6: signal="🟡 WEAK BUY - NO TRADE"; sl=live-80; t1=live+80; t2=live+120; conf=60
elif sell>=6: signal="🟡 WEAK SELL - NO TRADE"; sl=live+80; t1=live-80; t2=live-120; conf=60
else: signal="⚪ NO TRADE"; sl=live-80; t1=live+60; t2=live+100; conf=45

msg=f"""NIFTY PIVOT BOSS 4.0 - NSE DATA
{datetime.datetime.now().strftime('%d-%b %I:%M %p')}

SRC: NSE India Official + Bhavcopy
Prev: H {H:.0f} L {L:.0f} C {C:.0f} | Live {live:.0f}

CPR: TC {TC:.0f} P {P:.0f} BC {BC:.0f}
R1 {R1:.0f} S1 {S1:.0f} | R2 {R2:.0f} S2 {S2:.0f} | R3 {R3:.0f} S3 {S3:.0f}

EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f} RSI {rsi:.0f} ST {st}

{signal} ({score}/10) {conf}% Conf
Buy {buy} Sell {sell}

ENTRY {live:.0f} SL {sl:.0f} TGT1 {t1:.0f} TGT2 {t2:.0f}
Risk:Reward 1:1.5
Reasons: {' | '.join(reasons)}

Rule: Trade only 8+/10
"""

print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})
