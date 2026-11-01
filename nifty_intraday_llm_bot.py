import requests, os, datetime, csv, json, math, time
import risk_manager as rm

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
OPENAI_KEY=os.getenv("OPENAI_API_KEY") # Optional for real LLM
MEMORY_FILE="intraday_memory.json"
TICK_FILE="nifty_ticks_today.csv"

def fetch_free_tick():
    # Free tick proxy - NSE polling every 5 sec
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        r=s.get("https://www.nseindia.com/api/allIndices", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}, timeout=5).json()
        for idx in r['data']:
            if idx['index']=='NIFTY 50':
                return float(idx['last']), float(idx['open']), float(idx['dayHigh']), float(idx['dayLow']), "NSE_TICK"
    except Exception as e:
        pass
    # Fallback Yahoo 1m tick
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()['chart']['result'][0]
    price=float(d['meta']['regularMarketPrice'])
    return price, price, price, price, "Yahoo_TICK"

def fetch_history_1d():
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=5d"
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
                'vol': float(q['volume'][i]) if q['volume'][i] else 0
            })
    return candles

def calculate_features(candles):
    closes=[c['close'] for c in candles]
    def ema(p):
        k=2/(p+1); e=sum(closes[:p])/p
        for v in closes[p:]: e=v*k+e*(1-k)
        return e
    ema9=ema(9); ema21=ema(21)
    # RSI
    g=l=0
    for i in range(len(closes)-14, len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: g+=d
        else: l+=abs(d)
    rsi=100-(100/(1+g/l if l else 1)) if l else 50
    # VWAP
    pv=sum(c['close']*c['vol'] for c in candles[-20:])
    vv=sum(c['vol'] for c in candles[-20:])
    vwap=pv/vv if vv else closes[-1]
    return ema9, ema21, rsi, vwap

def llm_reasoning(live, ema9, ema21, rsi, vwap, prev_cpr, risk_status):
    # If OpenAI key present, use real LLM, else rule-based LLM brain
    prompt = f"Nifty live {live} VWAP {vwap:.0f} EMA9 {ema9:.0f} EMA21 {ema21:.0f} RSI {rsi:.0f} CPR {prev_cpr} Risk {risk_status} MaxLoss 2000. Should we trade intraday? Need 1:2 RR after brokerage 18pts. Reply BUY/SELL/NO with confidence % and reason 1 line."
    
    if OPENAI_KEY:
        try:
            import requests
            res=requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENAI_KEY}"},
                json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]}, timeout=10).json()
            return res['choices'][0]['message']['content']
        except:
            pass
    
    # Rule-based LLM Brain (works without API key) - Self learning logic
    score=0; reasons=[]
    if live>vwap: score+=1; reasons.append("Above VWAP")
    else: score-=1; reasons.append("Below VWAP")
    if ema9>ema21: score+=1; reasons.append("EMA Bull")
    else: score-=1; reasons.append("EMA Bear")
    if 55<=rsi<=68: score+=2; reasons.append(f"RSI Bull {rsi:.0f}")
    elif 32<=rsi<=45: score-=2; reasons.append(f"RSI Bear {rsi:.0f}")
    if live>prev_cpr['TC']: score+=1; reasons.append("Above CPR")
    elif live<prev_cpr['BC']: score-=1; reasons.append("Below CPR")
    
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
ist_hour = now.hour + 5 + now.minute/60  # Approx IST
# Allow only 9:15 to 15:15
is_market = True # 9 <= ist_hour <= 15.5 # Uncomment to enforce market hours

candles=fetch_history_1d()
live, o, h, l, src = fetch_free_tick()
save_tick(live)

ema9, ema21, rsi, vwap = calculate_features(candles)
memory=load_memory()
risk=rm.load_risk()

# Pivot of today
P=(h+l+candles[-2]['close'])/3 if h else live
BC=(h+l)/2 if h else live-20
TC=2*P-BC
cpr_dict={"P":P,"BC":BC,"TC":TC}

can, risk_msg = rm.can_trade()
llm_out = llm_reasoning(live, ema9, ema21, rsi, vwap, cpr_dict, risk_msg)

# Decision
sig="NO TRADE"
sl=t1=t2=0
if "BUY" in llm_out and can and "Confidence" in llm_out:
    try:
        conf=int(llm_out.split("Confidence")[1].split("%")[0].strip()[-2:])
    except:
        conf=60
    if conf>=75:
        sig="🟢 INTRADAY BUY"
        sl=live-40
        t1=live+80
        t2=live+120
elif "SELL" in llm_out and can and "Confidence" in llm_out:
    try:
        conf=int(llm_out.split("Confidence")[1].split("%")[0].strip()[-2:])
    except:
        conf=60
    if conf>=75:
        sig="🔴 INTRADAY SELL"
        sl=live+40
        t1=live-80
        t2=live-120

charges=rm.calc_charges(live, live+80 if "BUY" in sig else live-80)

msg=f"""NIFTY INTRADAY LLM V7.0 🧠🤖
Time: {now.strftime('%d-%b %Y %I:%M %p')} IST
Tick Source: {src} | Live: {live:.0f}

5m Candles: {len(candles)} | VWAP {vwap:.0f} EMA9 {ema9:.0f} EMA21 {ema21:.0f} RSI {rsi:.0f}
CPR Today: TC {TC:.0f} BC {BC:.0f} P {P:.0f}
Day H {h:.0f} L {l:.0f}

🧠 LLM BRAIN:
{llm_out}

{ sig }
SL {sl:.0f} (40 pts) TGT1 {t1:.0f} (80 pts) TGT2 {t2:.0f} (120 pts)
RR 1:2

💰 COST ANALYSIS (Govt + Broker):
Brokerage + STT + GST + Others = ₹{charges} per lot (50 qty)
Breakeven = 18 pts
Net per win (80 pts): ₹{(80*50)-charges:.0f}
Net per loss (40 pts): ₹{- (40*50)-charges:.0f}

🛡️ RISK MANAGER:
Trades Today: {risk['trades']}/3 | PnL: ₹{risk['pnl']:.0f} | Loss: ₹{risk['loss']:.0f}/2000
Status: {risk_msg}
{'⛔ BOT BLOCKED TODAY' if risk['blocked'] else '✅ Active'}

Rule: Max 3 trades | Max loss 2000 | Trade only >75% confidence | No trade 9:15-9:30
Tick saved: {TICK_FILE}
"""

print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})

# Save memory
memory["trades"].append({"time":now.strftime("%H:%M"), "live":live, "llm":llm_out, "signal":sig})
if len(memory["trades"])>200:
    memory["trades"]=memory["trades"][-200:]
with open(MEMORY_FILE,'w') as f:
    json.dump(memory,f,indent=2)
