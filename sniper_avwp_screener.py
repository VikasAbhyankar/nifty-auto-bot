# V7 - KOTAK IDEAL WTH STRATEGY - Based on 3 Screenshots - SBILIFE + KOTAK BANK
import yfinance as yf, pandas as pd, time, os, requests
from datetime import datetime

BOT=os.getenv("BOT_TOKEN") or os.getenv("SNIPER_BOT_TOKEN"); CHAT=os.getenv("CHAT_ID") or os.getenv("SNIPER_CHAT_ID")
def tg(m):
    if not BOT or not CHAT: print(m); return
    url=f"https://api.telegram.org/bot{BOT}/sendMessage"
    for i in range(0,len(m),3500):
        try: requests.post(url, json={"chat_id":CHAT,"text":m[i:i+3500],"parse_mode":"Markdown"}, timeout=20)
        except: pass

SYMBOLS=["KOTAKBANK.NS","HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS","SBIN.NS","RELIANCE.NS","TCS.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","LT.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","M&M.NS","TITAN.NS","ASIANPAINT.NS","HCLTECH.NS","WIPRO.NS","POWERGRID.NS","NTPC.NS","COALINDIA.NS","JSWSTEEL.NS","TATASTEEL.NS","HINDALCO.NS","ONGC.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","BEL.NS","HAL.NS","RECLTD.NS","PFC.NS","TRENT.NS"]

def ema(s,p): return s.ewm(span=p, adjust=False).mean()
def swing_lows(df,w=5):
    r=[]
    for i in range(w,len(df)-w):
        if df['Low'].iloc[i]==df['Low'].iloc[i-w:i+w+1].min(): r.append((df.index[i], float(df['Low'].iloc[i])))
    return r[-10:]
def swing_highs(df,w=5):
    r=[]
    for i in range(w,len(df)-w):
        if df['High'].iloc[i]==df['High'].iloc[i-w:i+w+1].max(): r.append((df.index[i], float(df['High'].iloc[i])))
    return r[-8:]
def avwap(df, anchor):
    try:
        d=df[df.index>=anchor]
        if len(d)<5: return None
        t=(d['High']+d['Low']+d['Close'])/3
        return float(((t*d['Volume']).cumsum()/d['Volume'].cumsum()).iloc[-1])
    except: return None

def scan(sym):
    try:
        time.sleep(0.35)
        wk=yf.download(sym,period="2y",interval="1wk",progress=False,auto_adjust=False)
        dy=yf.download(sym,period="1y",interval="1d",progress=False,auto_adjust=False)
        hr=yf.download(sym,period="6mo",interval="1h",progress=False,auto_adjust=False)
        if len(hr)<150: return None
        for df in [wk,dy,hr]:
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

        # WTH - Screenshot 3: Weekly Timeframe
        w8=ema(wk['Close'],8).iloc[-1]; w20=ema(wk['Close'],20).iloc[-1]
        d8=ema(dy['Close'],8).iloc[-1]; d20=ema(dy['Close'],20).iloc[-1]
        h200=ema(hr['Close'],200).iloc[-1] if len(hr)>=200 else ema(hr['Close'],120).iloc[-1]
        h400=ema(hr['Close'],400).iloc[-1] if len(hr)>=400 else ema(hr['Close'],200).iloc[-1]

        # SCREENSHOT 2: HTF Pullback should near to 200 EMA crossed 400 EMA
        if not (h200>h400 and w8>w20 and d8>d20): return None

        # SCREENSHOT 1 & 2: AVWP High vs Low
        low_av=[]; high_av=[]
        for df,tf,win in [(hr,"H",12),(dy,"D",5),(wk,"W",3)]:
            for anc,sl in swing_lows(df,win):
                av=avwap(df,anc)
                if av: low_av.append((av,anc,tf,sl))
            for anc,sh in swing_highs(df,win):
                av=avwap(df,anc)
                if av: high_av.append((av,anc,tf,sh))

        curr=float(hr['Close'].iloc[-1]); open_=float(hr['Open'].iloc[-1])
        
        # SCREENSHOT 1 FIX: Skip if Below AVWP HIGH (Resistance) - SBILIFE
        for av_h,_,_,_ in high_av:
            if av_h>curr and (av_h-curr)/curr*100 < 5:
                return {"sym":sym.replace(".NS",""), "skip":"BELOW HIGH AVWP RESISTANCE", "price":curr, "high_av":round(av_h,2)}

        # SCREENSHOT 2 & 3: Must be ABOVE LOW AVWP Cluster - Kotak Ideal
        above_low=[a for a in low_av if a[0]<=curr] # AVWP below price
        near=[a for a in above_low if abs(a[0]-curr)/curr*100<6]
        if len(near)<2: return None

        near=sorted(near, key=lambda x:x[0])
        cluster=[near[-1]]
        for a in reversed(near[:-1]):
            if abs(a[0]-cluster[0][0])/cluster[0][0]*100<2.5: cluster.append(a)
        if len(cluster)<2: return None

        c_avg=sum(c[0] for c in cluster)/len(cluster); c_low=min(c[0] for c in cluster); s_low=min(c[3] for c in cluster)
        dist_c=abs(curr-c_avg)/curr*100; dist_200=abs(curr-h200)/curr*100

        # Near 200 EMA in WTH + Near AVWP Cluster
        if dist_c<4 and dist_200<6 and curr>c_avg:
            small_sl=round(c_low*0.992,2) # Your 450
            big_sl=round(s_low*0.99,2) # Your 436
            return {
                "sym":sym.replace(".NS",""), "price":round(curr,2), "cluster":round(c_avg,2), "cnt":len(cluster),
                "dist_c":round(dist_c,2), "e200":round(float(h200),2), "dist200":round(dist_200,2),
                "small_sl":small_sl, "big_sl":big_sl, "risk":round((curr-small_sl)/curr*100,2),
                "signal":"BUY" if curr>open_ else "WATCH", "anchors":", ".join([str(c[1].strftime('%d-%b %H:%M')) for c in cluster[:3]])
            }
    except: return None

buy=[]; skip=[]
for s in SYMBOLS:
    r=scan(s)
    if r:
        if "skip" in r: skip.append(r)
        else: buy.append(r)

msg=f"🎯 *V7 KOTAK IDEAL WTH - {datetime.now().strftime('%d-%b %H:%M')}*\n*Based on 3 Screenshots: SBILIFE (Avoid Below High AVWP) + KOTAK (Ideal Above Low AVWP + Near 200>400)*\n\n*BUY {len(buy)} - Trading ABOVE AVWP Cluster + Near 200EMA*\n"
for r in sorted(buy, key=lambda x:x['dist_c'])[:12]:
    msg+=f"\n✅ *{r['sym']}* @ {r['price']} | {r['cnt']} AVWP {r['cluster']} {r['dist_c']}% | 200 {r['e200']} {r['dist200']}% | SL {r['small_sl']}({r['risk']}%) Big {r['big_sl']} | {r['anchors']}\n"

msg+=f"\n*SKIPPED {len(skip)} - Below HIGH AVWP Resistance (Like SBILIFE Screenshot 1)*\n"
for s in skip[:8]: msg+=f"❌ {s['sym']} @ {s['price']} < HIGH AVWP {s['high_av']} - Resistance\n"

msg+=f"\n_Kotak 457 Model: 4 AVWPs 08Jul12:15PM,29Sep,23Oct,29Oct cluster @ 450, Entry 457 Small SL 450 Big SL 436_"
print(msg); tg(msg)
pd.DataFrame(buy).to_csv("sniper_avwp_results.csv", index=False)
