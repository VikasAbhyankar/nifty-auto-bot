import requests, os, datetime, csv, json, math

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
MEMORY_FILE = "nifty_memory.json"

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
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d"
    d=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()['chart']['result'][0]
    return float(d['meta']['regularMarketPrice']), "Yahoo"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE,'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "weights": {"cpr":1.0, "ema":1.0, "trend":1.0, "rsi":1.0},
        "stats": {"cpr_wins":0,"cpr_total":0,"ema_wins":0,"ema_total":0,"rsi_wins":0,"rsi_total":0,"total_trades":0,"wins":0},
        "history": []
    }

def save_memory(mem):
    with open(MEMORY_FILE,'w') as f:
        json.dump(mem, f, indent=2)

def self_learn_weights(history, mem):
    closes=[x['close'] for x in history]
    def ema(data,p):
        k=2/(p+1); e=sum(data[:p])/p
        for v in data[p:]: e=v*k+e*(1-k)
        return e
    
    stats = {"cpr_w":0,"cpr_t":0,"ema_w":0,"ema_t":0,"rsi_w":0,"rsi_t":0}
    
    for i in range(len(history)-91, len(history)-1):
        if i < 50: continue
        H=history[i]['high']; L=history[i]['low']; C=history[i]['close']
        P=(H+L+C)/3; BC=(H+L)/2; TC=2*P-BC
        next_close=history[i+1]['close']
        today_close=history[i]['close']
        
        cpr_sig = 1 if today_close>TC else -1 if today_close<BC else 0
        if cpr_sig!=0:
            stats["cpr_t"]+=1
            if (cpr_sig==1 and next_close>today_close) or (cpr_sig==-1 and next_close<today_close):
                stats["cpr_w"]+=1
        
        e9=ema(closes[:i+1],9); e21=ema(closes[:i+1],21)
        ema_sig = 1 if e9>e21 else -1
        stats["ema_t"]+=1
        if (ema_sig==1 and next_close>today_close) or (ema_sig==-1 and next_close<today_close):
            stats["ema_w"]+=1

        g=l=0
        for k in range(i-13,i+1):
            d=closes[k]-closes[k-1]
            if d>0: g+=d
            else: l+=abs(d)
        rsi=100-(100/(1+g/l if l else 1)) if l else 50
        rsi_sig = 1 if rsi>55 else -1 if rsi<45 else 0
        if rsi_sig!=0:
            stats["rsi_t"]+=1
            if (rsi_sig==1 and next_close>today_close) or (rsi_sig==-1 and next_close<today_close):
                stats["rsi_w"]+=1

    def calc_w(wins,total):
        if total<10: return 1.0
        acc=wins/total
        return 0.5 + acc*1.5
    
    new_weights={
        "cpr": round(calc_w(stats["cpr_w"],stats["cpr_t"]),2),
        "ema": round(calc_w(stats["ema_w"],stats["ema_t"]),2),
        "rsi": round(calc_w(stats["rsi_w"],stats["rsi_t"]),2),
        "trend": 1.0
    }
    
    mem["stats"]["cpr_wins"]=stats["cpr_w"]; mem["stats"]["cpr_total"]=stats["cpr_t"]
    mem["stats"]["ema_wins"]=stats["ema_w"]; mem["stats"]["ema_total"]=stats["ema_t"]
    mem["stats"]["rsi_wins"]=stats["rsi_w"]; mem["stats"]["rsi_total"]=stats["rsi_t"]
    mem["weights"]=new_weights
    mem["last_learn"]=datetime.datetime.now().strftime("%d-%b-%Y")
    mem["learn_detail"]=stats
    return new_weights, stats

history = fetch_yahoo_1y()
live_price, src = fetch_live()
memory = load_memory()
weights, learn_stats = self_learn_weights(history, memory)

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
cpr_w=weights['cpr']; ema_w=weights['ema']; rsi_w=weights['rsi']

if live_price>TC: buy+=3*cpr_w; reasons.append(f"Above TC {TC:.0f} x{cpr_w}")
elif live_price<BC: sell+=3*cpr_w; reasons.append(f"Below BC {BC:.0f} x{cpr_w}")
else: reasons.append(f"Inside CPR {BC:.0f}-{TC:.0f}")

if st=="BULLISH" and live_price>ema21: buy+=2*ema_w; reasons.append(f"ST Bull + >EMA21 x{ema_w}")
elif st=="BEARISH" and live_price<ema21: sell+=2*ema_w; reasons.append(f"ST Bear + <EMA21 x{ema_w}")

if ema9>ema21 and live_price>ema9: buy+=2*ema_w; reasons.append(f"EMA9>21 Bull x{ema_w}")
elif ema9<ema21 and live_price<ema9: sell+=2*ema_w; reasons.append(f"EMA9<21 Bear x{ema_w}")

if 55<=rsi<=68: buy+=2*rsi_w; reasons.append(f"RSI Bull {rsi:.0f} x{rsi_w}")
elif 32<=rsi<=45: sell+=2*rsi_w; reasons.append(f"RSI Bear {rsi:.0f} x{rsi_w}")
else: reasons.append(f"RSI {rsi:.0f} Neutral")

score=max(buy,sell)
if buy>=8: sig="🟢 STRONG BUY"; sl=live_price-80; t1=live_price+120; t2=live_price+200
elif sell>=8: sig="🔴 STRONG SELL"; sl=live_price+80; t1=live_price-120; t2=live_price-200
elif buy>=6: sig="🟡 WEAK BUY - NO TRADE"; sl=live_price-80; t1=live_price+80; t2=live_price+120
elif sell>=6: sig="🟡 WEAK SELL - NO TRADE"; sl=live_price+80; t1=live_price-80; t2=live_price-120
else: sig="⚪ NO TRADE - RANGE"; sl=live_price-80; t1=live_price+60; t2=live_price+120

today_pred = {
    "date": datetime.datetime.now().strftime("%d-%b-%Y %H:%M"),
    "live": live_price,
    "signal": sig,
    "buy": round(buy,1),
    "sell": round(sell,1),
    "weights": weights
}
memory["history"].append(today_pred)
if len(memory["history"])>100:
    memory["history"]=memory["history"][-100:]
save_memory(memory)

cpr_acc = learn_stats["cpr_w"]/learn_stats["cpr_t"]*100 if learn_stats["cpr_t"] else 0
ema_acc = learn_stats["ema_w"]/learn_stats["ema_t"]*100 if learn_stats["ema_t"] else 0
rsi_acc = learn_stats["rsi_w"]/learn_stats["rsi_t"]*100 if learn_stats["rsi_t"] else 0

msg=f"""NIFTY PIVOT BOSS 6.0 SELF-LEARNING 🧠
Date: {datetime.datetime.now().strftime('%d-%b %Y %I:%M %p')}
Source: {src} Live

HISTORY: {len(history)} days | Memory: {len(memory['history'])} trades

Yesterday: H {H:.0f} L {L:.0f} C {C:.0f}
Live: {live_price:.0f}

CPR: TC {TC:.0f} P {P:.0f} BC {BC:.0f}
LEVELS: R3 {R3:.0f} R2 {R2:.0f} R1 {R1:.0f} | S1 {S1:.0f} S2 {S2:.0f} S3 {S3:.0f}

EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f}
RSI {rsi:.0f} Supertrend {st}

🧠 SELF-LEARNED WEIGHTS (90d Backtest):
CPR: {weights['cpr']} (Acc {cpr_acc:.0f}% - {learn_stats['cpr_w']}/{learn_stats['cpr_t']})
EMA: {weights['ema']} (Acc {ema_acc:.0f}% - {learn_stats['ema_w']}/{learn_stats['ema_t']})
RSI: {weights['rsi']} (Acc {rsi_acc:.0f}% - {learn_stats['rsi_w']}/{learn_stats['rsi_t']})

{sig} ({score:.1f}/10)
Buy {buy:.1f} vs Sell {sell:.1f}

TRADE: Entry {live_price:.0f} SL {sl:.0f} TGT1 {t1:.0f} TGT2 {t2:.0f}
RR 1:1.5

Reasons: {' | '.join(reasons)}

Memory: {MEMORY_FILE} updated
Rule: Trade only 8+/10
"""
print(msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg})
