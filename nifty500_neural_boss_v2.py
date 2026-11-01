import requests, os, datetime, time
import numpy as np

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_symbols():
    # NIFTY 50 + NEXT 50 + MIDCAP 150 = 250 STOCKS
    return [
    # Nifty 50
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK",
    "BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO",
    "ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS",
    "COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO",
    "HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR",
    # Next 50 + Midcap 200
    "ZOMATO","PIDILITIND","SIEMENS","ABB","HAVELLS","BOSCHLTD","DABUR","GODREJCP","MARICO","BERGEPAINT",
    "COLPAL","MCDOWELL-N","UBL","INDIGO","IRCTC","ZYDUSLIFE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM",
    "IPCALAB","GLENMARK","MPHASIS","COFORGE","LTIM","PERSISTENT","OFSS","LTTS","POLYCAB","CUMMINSIND",
    "ASHOKLEY","TVSMOTOR","MUTHOOTFIN","CHOLAFIN","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","AUBANK","PNB","BANKBARODA",
    "CANBK","INDHOTEL","OBEROIRLTY","DLF","GODREJPROP","PRESTIGE","BRIGADE","PHOENIXLTD","VOLTAS","BLUESTARCO",
    "DIXON","AMBER","KAYNES","SYRMA","TATACHEM","DEEPAKNTR","AARTIIND","NAVINFLUOR","BALRAMCHIN","TATAPOWER",
    "ADANIGREEN","ADANIENSOL","NHPC","SJVN","POWERINDIA","ABBOTINDIA","METROPOLIS","LALPATHLAB","SYNGENE","BIOCON",
    "ICICIGI","ICICIPRULI","STARHEALTH","SBICARD","CAMS","CDSL","BSE","MCX","IEX","360ONE",
    "JINDALSTEL","SAIL","NMDC","NATIONALUM","HINDCOPPER","JSL","APLAPOLLO","WELCORP","TATACOMM","HFCL",
    "TATAMOTORS","BAJAJHLDNG","M&MFIN","LICHSGFIN","PFC","RECLTD","IRFC","HUDCO","IRCON","RVNL",
    "HAL","BEL","BDL","MAZDOCK","COCHINSHIP","GRSE","CONCOR","GMRINFRA","CROMPTON","KEI",
    "LTFOODS","TATACONSUM","JUBLFOOD","DEVYANI","SAPPHIRE","WESTLIFE","NYKAA","PAYTM","POLICYBZR","DELHIVERY",
    "KPITTECH","TATAELXSI","SONACOMS","UNO Minda","MOTHERSON","MRF","BALKRISIND","APOLLOTYRE","EXIDEIND","AMARAJA",
    "PETRONET","GAIL","IGL","MGL","GUJGASLTD","OIL","MRPL","CHENNPETRO","FACT","GNFC",
    "GODREJIND","KANSAINER","AKZOINDIA","COROMANDEL","CHAMBLFERT","PIIND","UPL","SUMICHEM","SOLARINDS","ASTRAL",
    "PAGEIND","TRENT","DMART","VBL","UNITEC","TIINDIA","ESCORTS","SCHAEFFLER","SKFINDIA","TIMKEN",
    "ABCAPITAL","ABFRL","PEL","AARTIPHARM","LAURUSLABS"
    ]

def fetch_history(symbol):
    try:
        # Fix symbols with space
        s=symbol.replace(" ","")
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.NS?interval=1d&range=300d"
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()
        res=d['chart']['result'][0]
        q=res['indicators']['quote'][0]
        adj=res['indicators']['adjclose'][0]['adjclose'] if 'adjclose' in res['indicators'] else q['close']
        closes=[c for c in adj if c]
        highs=[h for h in q['high'] if h]
        lows=[l for l in q['low'] if l]
        vols=[v for v in q['volume'] if v]
        if len(closes)<100: return None
        return {'close':np.array(closes,float),'high':np.array(highs,float),'low':np.array(lows,float),'vol':np.array(vols,float)}
    except:
        return None

def calc_score(data):
    close=data['close']; high=data['high']; low=data['low']; vol=data['vol']
    tr=np.maximum(high[1:]-low[1:], np.maximum(np.abs(high[1:]-close[:-1]), np.abs(low[1:]-close[:-1])))
    atr14=np.mean(tr[-14:])
    diff=np.diff(close[-15:])
    gain=np.mean([d for d in diff if d>0]) if any(d>0 for d in diff) else 0.5
    loss=np.mean([-d for d in diff if d<0]) if any(d<0 for d in diff) else 0.5
    rsi=100-(100/(1+(gain/(loss+1e-9))))
    ema9=np.mean(close[-9:]); ema21=np.mean(close[-21:]); ema50=np.mean(close[-50:])
    vol_avg=np.mean(vol[-20:]); vol_ratio=vol[-1]/(vol_avg+1e-9)
    swing_high=np.max(high[-11:-1]); swing_low=np.min(low[-11:-1])
    dist_high=(close[-1]-swing_high)/close[-1]*100
    dist_low=(close[-1]-swing_low)/close[-1]*100
    st_bull=close[-1]>( (high[-1]+low[-1])/2 -3*atr14)
    score=50
    if st_bull and close[-1]>ema21: score+=15
    if ema9>ema21>ema50: score+=15
    elif ema9<ema21<ema50: score-=15
    if 50<=rsi<=68: score+=15
    elif rsi>78 or rsi<22: score-=15
    if vol_ratio>1.5: score+=15
    elif vol_ratio<0.7: score-=10
    if -0.8<=dist_high<=1.5: score+=20
    if -1.5<=dist_low<=0.8: score-=20
    score=max(0,min(100,score))
    return {'score':score,'rsi':rsi,'vol_ratio':vol_ratio,'atr':atr14,'dist_high':dist_high,'dist_low':dist_low,'st_bull':st_bull,'breakout':close[-1]>swing_high,'breakdown':close[-1]<swing_low,'close':close[-1],'swing_high':swing_high,'swing_low':swing_low}

symbols=get_symbols()
results=[]
print(f"Scanning {len(symbols)} stocks...")
for i,sym in enumerate(symbols):
    data=fetch_history(sym)
    if not data: continue
    info=calc_score(data)
    if (info['score']>=78 and info['vol_ratio']>=1.2) or info['score']<=22:
        results.append({'symbol':sym, **info})
    if i%20==0: time.sleep(0.5)  # Avoid Yahoo block

results=sorted(results, key=lambda x: x['score'], reverse=True)
buys=[r for r in results if r['score']>=78][:7]  # Top 7 now
sells=sorted([r for r in results if r['score']<=22], key=lambda x: x['score'])[:5]

msg=f"""🧠 NIFTY 250 NEURAL v7.3 - FULL SCAN
{datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Scanned: {len(symbols)} | Found: {len(results)} | Vol>=1.2x

🔥 TOP 7 BUY:
"""
if buys:
    for b in buys:
        br=f"BREAKOUT {b['swing_high']:.0f} 🔥" if b['breakout'] else f"{b['dist_high']:.1f}% to {b['swing_high']:.0f}"
        msg+=f"{b['symbol']} {b['close']:.0f} | {b['score']:.0f}% | {br} | Vol {b['vol_ratio']:.1f}x | RSI {b['rsi']:.0f}\n"
else:
    msg+="No BUY with Vol>=1.2x - Market flat. Wait.\n"

msg+=f"\n🔻 TOP 5 SELL:\n"
if sells:
    for s in sells:
        bd=f"BREAKDOWN {s['swing_low']:.0f} 💥" if s['breakdown'] else f"{s['dist_low']:.1f}% to {s['swing_low']:.0f}"
        msg+=f"{s['symbol']} {s['close']:.0f} | {100-s['score']:.0f}% SELL | {bd} | Vol {s['vol_ratio']:.1f}x\n"
else:
    msg+="No strong SELL.\n"

msg+=f"\n✅ Rule: BUY Only BREAKOUT + Vol>=1.5x | Monday 9:20AM live.\n"
print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg[:4000]}, timeout=10)
