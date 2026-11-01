import requests, os, datetime, csv, json, math
import risk_manager as rm

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
OPENAI_KEY=os.getenv("OPENAI_API_KEY")
MEMORY_FILE="intraday_memory.json"
TICK_FILE="nifty_ticks_today.csv"

def fetch_free_tick():
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        r=s.get("https://www.nseindia.com/api/allIndices", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}, timeout=5).json()
        for idx in r['data']:
            if idx['index']=='NIFTY 50':
                return float(idx['last']), float(idx['open']), float(idx['dayHigh']), float(idx['dayLow']), "NSE_TICK"
    except:
        pass
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d"
    try:
        d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()['chart']['result'][0]
        price=float(d['meta']['regularMarketPrice'])
        # Use previous close for H/L if market closed
        prev=float(d['meta']['previousClose']) if d['meta'].get('previousClose') else price
        return price, prev, price, price, "Yahoo_TICK"
    except:
        return 23000, 23000, 23000, 23000, "Fallback"

def fetch_history_1d():
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=7d"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15).json()['chart']['result'][0]
    q=d['indicators']['quote'][0]
    ts=d['timestamp']
    candles=[]
    for i in range(len(q['close'])):
        if q['close'][i]:
            candles.append({
                'time': ts[i],
                'open': float(q['open'][i]),
                'high': float(q['high'][i]),
                'low': float(q['low'][i]),
                'close': float(q['close'][i]),
                'vol': float(q['volume'][i]) if q['volume'][i] else 0,
                'date': datetime.datetime.fromtimestamp(ts[i]).strftime("%Y-%m-%d")
            })
    return candles

def calculate_features(candles):
    closes=[c['close'] for c in candles]
    def ema(p):
        k=2/(p+1); e=sum(closes[:p])/p
        for v in closes[p:]: e=v*k+e*(1-k)
        return e
    ema9=ema(9); ema21=ema(21)
    g=l=0
    for i in range(len(closes)-14, len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: g+=d
        else: l+=abs(d)
    rsi=100-(100/(1+g/l if l else 1)) if l else 50
    pv=sum(c['close']*c['vol'] for c in candles[-20:])
    vv=sum(c['vol'] for c in candles[-20:])
    vwap=pv/vv if vv else closes[-1]
    return ema9, ema21, rsi, vwap

def get_prev_day_cpr(candles):
    # Group by date and get last trading day before today
    from collections import defaultdict
    by_date=defaultdict(list)
    for c in candles:
        by_date[c['date']].append(c)
    dates=sorted(by_date.keys())
    if len(dates)>=2:
        prev_day=dates[-2]  # Yesterday trading day
        day_c=by_date[prev_day]
        h=max(x['high'] for x in day_c)
        l=min(x['low'] for x in day_c)
        cl=day_c[-1]['close']
    else:
        # Fallback to last 78 candles (1 day)
        last_day=candles[-78:] if len(candles)>=78 else candles
        h=max(x['high'] for x in last_day)
        l=min(x['low'] for x in last_day)
        cl=last_day[-1]['close']
        prev_day=last_day[0]['date']
    P=(h+l+cl)/3
    BC=(h+l)/2
    TC=2*P-BC
    return {"P":P,"BC":BC,"TC":TC,"H":h,"L":l,"C":cl,"date":prev_day}

def llm_reasoning(live, ema9, ema21, rsi, vwap, cpr, risk_status):
    prompt = f"Nifty live {live} VWAP {vwap:.0f} EMA9 {ema9:.0f} EMA21 {ema21:.0f} RSI {rsi:.0f} CPR {cpr['TC']:.0f}/{cpr['P']:.0f}/{cpr['BC']:.0f} Risk {risk_status} MaxLoss 2000. Should we trade intraday? Need 1:2 RR after brokerage 18pts. Reply BUY/SELL/NO with confidence % and reason 1 line."
    if OPENAI_KEY:
        try:
            res=requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENAI_KEY}"},
                json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]}, timeout=10).json()
            return res['choices'][0]['message']['content']
        except:
            pass
    score=0; reasons=[]
    if live>vwap: score+=1; reasons.append("Above VWAP")
    else: score-=1; reasons.append("Below VWAP")
    if ema9>ema21: score+=1; reasons.append("EMA Bull")
    else: score-=1; reasons.append("EMA Bear")
    if 55<=rsi<=70: score+=2; reasons.append(f"RSI Bull {rsi:.0f}")
    elif 30<=rsi<=44: score-=2; reasons.append(f"RSI Bear {rsi:.0f}")
    if live>cpr['TC']: score+=1; reasons.append("Above CPR")
    elif live<cpr['BC']: score-=1; reasons.append("Below CPR")
    # Gap
    if live>cpr['H']: score+=1; reasons.append("BO High")
    elif live<cpr['L']: score-=1; reasons.append("BO Low")
    
    conf = min(95, 50+abs(score)*15)
    if score>=3: return f"BUY - Confidence {conf}% - {' | '.join(reasons)}"
    elif score<=-3: return f"SELL - Confidence {conf}% - {' | '.join(reasons)}"
    else: return f"NO TRADE - Confidence {conf}% - Weak signal {' | '.join(reasons)}"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE,'r') as f:
                return json.load(f)
        except:
            pass
    return {"trades": [], "weights": {"vwap":1.0,"ema":1.0,"rsi":1.0,"cpr":1.0}, "accuracy":0}

def save_tick(live):
    with open(TICK_FILE,'a',newline='') as f:
        w=csv.writer(f)
        if f.tell()==0:
            w.writerow(["time","price"])
        w.writerow([datetime.datetime.now().strftime("%H:%M:%S"), live])

# === MAIN ===
now=datetime.datetime.now()
candles=fetch_history_1d()
live, o, h, l, src = fetch_free_tick()
save_tick(live)

ema9, ema21, rsi, vwap = calculate_features(candles)
cpr_dict=get_prev_day_cpr(candles)
memory=load_memory()
risk=rm.load_risk()

can, risk_msg = rm.can_trade()
llm_out = llm_reasoning(live, ema9, ema21, rsi, vwap, cpr_dict, risk_msg)

sig="NO TRADE"
sl=t1=t2=0
if "BUY" in llm_out and can:
    try: conf=int(llm_out.split("Confidence")[1].split("%")[0].strip()[-2:])
    except: conf=60
    if conf>=75:
        sig="🟢 INTRADAY BUY"
        sl=live-40
        t1=live+80
        t2=live+120
elif "SELL" in llm_out and can:
    try: conf=int(llm_out.split("Confidence")[1].split("%")[0].strip()[-2:])
    except: conf=60
    if conf>=75:
        sig="🔴 INTRADAY SELL"
        sl=live+40
        t1=live-80
        t2=live-120

charges=rm.calc_charges(live, live+80 if "BUY" in sig else live-80)

msg=f"""NIFTY INTRADAY LLM V7.1 🧠🤖
Time: {now.strftime('%d-%b %Y %I:%M %p')} IST | {src} Live: {live:.0f}

5m Candles: {len(candles)} | VWAP {vwap:.0f} EMA9 {ema9:.0f} EMA21 {ema21:.0f} RSI {rsi:.0f}
Prev Day {cpr_dict['date']}: H {cpr_dict['H']:.0f} L {cpr_dict['L']:.0f} C {cpr_dict['C']:.0f}
CPR: TC {cpr_dict['TC']:.0f} P {cpr_dict['P']:.0f} BC {cpr_dict['BC']:.0f}

🧠 LLM BRAIN:
{llm_out}

{ sig }
SL {sl:.0f} (40 pts) TGT1 {t1:.0f} (80 pts) TGT2 {t2:.0f} (120 pts)
RR 1:2

💰 COST: ₹{charges}/lot (50 qty) | Breakeven 18 pts
Net Win 80 pts: ₹{(80*50)-charges:.0f} | Net Loss 40 pts: ₹{-(40*50)-charges:.0f}

🛡️ RISK:
Trades: {risk['trades']}/3 | PnL: ₹{risk['pnl']:.0f} | Loss: ₹{risk['loss']:.0f}/2000
Status: {risk_msg}
{'⛔ BLOCKED TODAY' if risk['blocked'] else '✅ Active'}
"""

print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})

memory["trades"].append({"time":now.strftime("%H:%M"), "live":live, "llm":llm_out, "signal":sig, "cpr":cpr_dict})
if len(memory["trades"])>200:
    memory["trades"]=memory["trades"][-200:]
with open(MEMORY_FILE,'w') as f:
    json.dump(memory,f,indent=2)
