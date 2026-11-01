import requests, os, datetime, time
import numpy as np

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def get_symbols():
    return [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","BHARTIARTL","SBIN","LT","ITC","KOTAKBANK",
    "BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","AXISBANK","HCLTECH","SUNPHARMA","TITAN","ULTRACEMCO",
    "ONGC","BAJAJFINSV","NTPC","POWERGRID","M&M","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS",
    "COALINDIA","GRASIM","TECHM","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","BPCL","BRITANNIA","HEROMOTOCO",
    "HDFCLIFE","SBILIFE","INDUSINDBK","SHREECEM","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","VEDL","UPL","HINDUNILVR",
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
    "KPITTECH","TATAELXSI","SONACOMS","UNOMINDA","MOTHERSON","MRF","BALKRISIND","APOLLOTYRE","EXIDEIND","AMARAJA",
    "PETRONET","GAIL","IGL","MGL","GUJGASLTD","OIL","MRPL","CHENNPETRO","FACT","GNFC",
    "GODREJIND","KANSAINER","AKZOINDIA","COROMANDEL","CHAMBLFERT","PIIND","UPL","SUMICHEM","SOLARINDS","ASTRAL",
    "PAGEIND","TRENT","DMART","VBL","TIINDIA","ESCORTS","SCHAEFFLER","SKFINDIA","TIMKEN","ABCAPITAL","ABFRL","PEL","AARTIPHARM","LAURUSLABS"
    ]

def fetch_history(symbol):
    try:
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
    except: return None

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
    st_bull=close[-1]>( (high[-1]+low[-1])/2 -3*atr14)
    score=50
    if st_bull and close[-1]>ema21: score+=15
    if ema9>ema21>ema50: score+=15
    if 50<=rsi<=68: score+=15
    if vol_ratio>1.5: score+=20
    if -0.8<=dist_high<=0.5: score+=20
    score=max(0,min(100,score))
    return {'score':score,'rsi':rsi,'vol_ratio':vol_ratio,'atr':atr14,'ema_ok':ema9>ema21>ema50,'st_bull':st_bull,'breakout':close[-1]>swing_high,'close':close[-1],'swing_high':swing_high,'swing_low':swing_low}

symbols=get_symbols()
results=[]
for sym in symbols:
    data=fetch_history(sym)
    if not data: continue
    info=calc_score(data)
    # KILLER FILTER: Only real monsters
    if info['breakout'] and info['vol_ratio']>=1.5 and 45<=info['rsi']<=68 and info['st_bull'] and info['ema_ok'] and info['score']>=85:
        results.append({'symbol':sym, **info})

results=sorted(results, key=lambda x: (x['vol_ratio']*0.6 + x['score']*0.4), reverse=True)
top3=results[:3]

msg=f"""🎯 NIFTY 250 - TOP 3 KILLER PICKS
{datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Scanned: {len(symbols)} | Killer Filter: BREAKOUT+Vol1.5x+RSI45-68+EMA

"""
if top3:
    for i,b in enumerate(top3,1):
        sl=b['close']-1.5*b['atr']  # Tight SL
        tgt=b['close']+3*b['atr']    # Big TGT
        rr=(tgt-b['close'])/(b['close']-sl+1e-9)
        msg+=f"{i}. {b['symbol']} {b['close']:.0f} 🔥\n   BREAKOUT {b['swing_high']:.0f} | Vol {b['vol_ratio']:.1f}x | RSI {b['rsi']:.0f} | Score {b['score']:.0f}%\n   SL {sl:.0f} | TGT {tgt:.0f} | R:R 1:{rr:.1f}\n   Why Killer: Vol {b['vol_ratio']:.1f}x + EMA Bull + ST Bull\n\n"
else:
    msg+="No Killer today - Market is flat. No trade is also a trade. Wait for Monday live.\n"

msg+=f"Rule: Only buy these 3. No other stocks.\n"
print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg[:4000]}, timeout=10)
