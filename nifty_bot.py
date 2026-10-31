import requests, os, datetime, csv, json

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_nse_session():
    s=requests.Session()
    h={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":"*/*",
        "Referer":"https://www.nseindia.com/"
    }
    s.get("https://www.nseindia.com", headers=h, timeout=10)
    return s,h

def fetch_history_oct25_to_today():
    """Fetch 01-Oct-2025 to Today from NSE"""
    session, headers = get_nse_session()
    all_data=[]
    
    # NSE API format: DD-MM-YYYY
    # Split into 2 calls: Oct 2025 - Mar 2026, Apr 2026 - Oct 2026
    ranges=[
        ("01-10-2025","31-03-2026"),
        ("01-04-2026","31-10-2026")
    ]
    
    for start,end in ranges:
        try:
            url=f"https://www.nseindia.com/api/historical/indicesHistory?indexType=NIFTY%2050&from={start}&to={end}"
            print(f"Fetching {start} to {end}...")
            r=session.get(url, headers=headers, timeout=15).json()
            records=r['data']['indexCloseOnlineRecords']
            for rec in records:
                # rec has: EOD_TIMESTAMP, EOD_OPEN_INDEX_VAL, EOD_HIGH_INDEX_VAL, EOD_LOW_INDEX_VAL, EOD_CLOSE_INDEX_VAL
                all_data.append({
                    'date': rec['EOD_TIMESTAMP'],
                    'open': float(rec['EOD_OPEN_INDEX_VAL']),
                    'high': float(rec['EOD_HIGH_INDEX_VAL']),
                    'low': float(rec['EOD_LOW_INDEX_VAL']),
                    'close': float(rec['EOD_CLOSE_INDEX_VAL']),
                })
            print(f"Got {len(records)} days")
        except Exception as e:
            print(f"Failed {start}-{end}: {e}")
    
    # Sort by date
    all_data=sorted(all_data, key=lambda x: datetime.datetime.strptime(x['date'], "%d-%b-%Y"))
    return all_data

def fetch_live():
    session, headers = get_nse_session()
    try:
        url="https://www.nseindia.com/api/allIndices"
        r=session.get(url, headers=headers, timeout=10).json()
        for idx in r['data']:
            if idx['index']=='NIFTY 50':
                return float(idx['last'])
    except:
        pass
    return None

# ========== MAIN ==========
print("=== NSE OCT 2025 to OCT 2026 FETCH ===")
history = fetch_history_oct25_to_today()

# If NSE blocks, fallback to Yahoo
if len(history)<10:
    print("NSE blocked, using Yahoo fallback")
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1y"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()['chart']['result'][0]
    q=d['indicators']['quote'][0]
    history=[]
    ts=d['timestamp']
    for i in range(len(q['close'])):
        if q['close'][i]:
            dt=datetime.datetime.fromtimestamp(ts[i]).strftime("%d-%b-%Y")
            history.append({'date':dt,'open':q['open'][i],'high':q['high'][i],'low':q['low'][i],'close':q['close'][i]})

# Save to CSV for backtest
with open('nifty_oct25_oct26.csv','w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['date','open','high','low','close'])
    w.writeheader()
    w.writerows(history)

print(f"Total days saved: {len(history)} in nifty_oct25_oct26.csv")
print(f"From {history[0]['date']} to {history[-1]['date']}")

# Calculate for TODAY's bot signal
prev=history[-2]
curr_live=fetch_live() or history[-1]['close']
H,L,C=prev['high'],prev['low'],prev['close']
P=(H+L+C)/3; BC=(H+L)/2; TC=2*P-BC
R1=2*P-L; S1=2*P-H; R2=P+(H-L); S2=P-(H-L)

# EMA RSI from history
closes=[x['close'] for x in history]
def ema(data,p):
    if len(data)<p: return data[-1]
    k=2/(p+1); e=sum(data[:p])/p
    for v in data[p:]: e=v*k+e*(1-k)
    return e

ema9=ema(closes,9); ema21=ema(closes,21); ema50=ema(closes,50)
# RSI
g=l=0
for i in range(len(closes)-14,len(closes)):
    if i<=0: continue
    d=closes[i]-closes[i-1]
    if d>0: g+=d
    else: l+=abs(d)
rsi=100-(100/(1+g/l)) if l else 70

st="BULLISH" if curr_live>ema50 else "BEARISH"
buy=sell=0
if curr_live>TC: buy+=3
elif curr_live<BC: sell+=3
if st=="BULLISH": buy+=2
else: sell+=2
if ema9>ema21: buy+=2
else: sell+=2
if 55<=rsi<=68: buy+=2
elif 32<=rsi<=45: sell+=2
if curr_live>P: buy+=1
else: sell+=1

score=max(buy,sell)
if buy>=8: sig="🟢 STRONG BUY"
elif sell>=8: sig="🔴 STRONG SELL"
elif buy>=6 or sell>=6: sig="🟡 WEAK - NO TRADE"
else: sig="⚪ NO TRADE"

msg=f"""NIFTY PIVOT BOSS 5.0 - NSE AUTO
Date: {datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}

DATA: Oct 2025 to Today ({len(history)} days)
File: nifty_oct25_oct26.csv saved
From {history[0]['date']} to {history[-1]['date']}

Yesterday: H {H:.0f} L {L:.0f} C {C:.0f}
Live: {curr_live:.0f}
CPR: TC {TC:.0f} P {P:.0f} BC {BC:.0f}
R1 {R1:.0f} S1 {S1:.0f} R2 {R2:.0f} S2 {S2:.0f}

EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f} RSI {rsi:.0f} ST {st}

{sig} ({score}/10) Buy {buy} Sell {sell}
ENTRY {curr_live:.0f} SL {curr_live-80:.0f}/{curr_live+80:.0f} TGT {curr_live+120:.0f}/{curr_live-120:.0f}

Auto-update: Daily 9:15 AM IST via GitHub Actions
Next update: Monday 9:15 AM
"""
print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})
