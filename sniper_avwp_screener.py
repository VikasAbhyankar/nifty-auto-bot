# V9 FINAL - NIFTY 200 + KOTAK IDEAL WTH + 15 MIN - Complete Code
import yfinance as yf, pandas as pd, time, os, requests, json
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("SNIPER_BOT_TOKEN") or ""
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("SNIPER_CHAT_ID") or ""

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("No BOT/CHAT"); print(msg); return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        for i in range(0, len(msg), 4000):
            chunk = msg[i:i+4000]
            r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk, "parse_mode": "Markdown"}, timeout=20)
            print(f"TG {r.status_code}")
        return True
    except Exception as e:
        print(f"TG Error {e}"); return False

# NIFTY 200 FULL LIST - No LTIM issue
SYMBOLS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS",
    "BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS",
    "ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS",
    "ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS",
    "BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS",
    "ADANIGREEN.NS","ADANIPOWER.NS","AMBUJACEM.NS","APOLLOTYRE.NS","ASHOKLEY.NS","ASTRAL.NS","ATUL.NS","AUBANK.NS","AUROPHARMA.NS","BAJAJHLDNG.NS",
    "BANKBARODA.NS","BATAINDIA.NS","BERGEPAINT.NS","BHARATFORG.NS","BHEL.NS","BIOCON.NS","BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS","CUMMINSIND.NS",
    "DABUR.NS","DALBHARAT.NS","DEEPAKNTR.NS","DIVISLAB.NS","DLF.NS","DRREDDY.NS","EICHERMOT.NS","ESCORTS.NS","EXIDEIND.NS","FEDERALBNK.NS",
    "GAIL.NS","GLENMARK.NS","GODREJCP.NS","GODREJPROP.NS","GRASIM.NS","HAVELLS.NS","HEROMOTOCO.NS","HINDALCO.NS","HINDCOPPER.NS","HINDPETRO.NS",
    "ICICIGI.NS","ICICIPRULI.NS","IDFCFIRSTB.NS","IGL.NS","INDHOTEL.NS","INDIAMART.NS","INDIGO.NS","INDUSINDBK.NS","INFIBEAM.NS","IOC.NS",
    "IPCALAB.NS","IRCTC.NS","JINDALSTEL.NS","JUBLFOOD.NS","KOTAKBANK.NS","LALPATHLAB.NS","LAURUSLABS.NS","LICI.NS","LTIM.NS","LTTS.NS",
    "LUPIN.NS","M&MFIN.NS","MANAPPURAM.NS","MARICO.NS","MCDOWELL-N.NS","MFSL.NS","MGL.NS","MOTHERSON.NS","MPHASIS.NS","MRF.NS","MUTHOOTFIN.NS",
    "NATIONALUM.NS","NAUKRI.NS","NAVINFLUOR.NS","NESTLEIND.NS","NMDC.NS","OBEROIRLTY.NS","OFSS.NS","PAGEIND.NS","PEL.NS","PETRONET.NS",
    "PFIZER.NS","PIDILITIND.NS","PIIND.NS","PNB.NS","POLYCAB.NS","PVRINOX.NS","RAMCOCEM.NS","RBLBANK.NS","RELIANCE.NS","SAIL.NS","SBICARD.NS",
    "SBILIFE.NS","SHREECEM.NS","SIEMENS.NS","SRF.NS","SUNPHARMA.NS","SUNTV.NS","SYNGENE.NS","TATACHEM.NS","TATACOMM.NS","TATACONSUM.NS",
    "TATAMOTORS.NS","TATAPOWER.NS","TATASTEEL.NS","TCS.NS","TECHM.NS","TITAN.NS","TORNTPHARM.NS","TORNTPOWER.NS","TRENT.NS","TVSMOTOR.NS",
    "UBL.NS","ULTRACEMCO.NS","UPL.NS","VEDL.NS","VOLTAS.NS","WIPRO.NS","ZEEL.NS","ZYDUSLIFE.NS","ZOMATO.NS","PAYTM.NS","NYKAA.NS","POLICYBZR.NS"
]

def ema(s,p): return s.ewm(span=p, adjust=False).mean()
def find_lows(df,w=5):
    r=[]
    try:
        for i in range(w,len(df)-w):
            if df['Low'].iloc[i]==df['Low'].iloc[i-w:i+w+1].min(): r.append((df.index[i], float(df['Low'].iloc[i])))
    except: pass
    return r[-10:]
def find_highs(df,w=5):
    r=[]
    try:
        for i in range(w,len(df)-w):
            if df['High'].iloc[i]==df['High'].iloc[i-w:i+w+1].max(): r.append((df.index[i], float(df['High'].iloc[i])))
    except: pass
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
        time.sleep(0.25)
        wk=yf.download(sym,period="2y",interval="1wk",progress=False,auto_adjust=False)
        dy=yf.download(sym,period="1y",interval="1d",progress=False,auto_adjust=False)
        hr=yf.download(sym,period="6mo",interval="1h",progress=False,auto_adjust=False)
        if len(hr)<120 or len(dy)<80: return None
        for df in [wk,dy,hr]:
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        w8=ema(wk['Close'],8).iloc[-1]; w20=ema(wk['Close'],20).iloc[-1]
        d8=ema(dy['Close'],8).iloc[-1]; d20=ema(dy['Close'],20).iloc[-1]
        h200=ema(hr['Close'],200).iloc[-1] if len(hr)>=200 else ema(hr['Close'],120).iloc[-1]
        h400=ema(hr['Close'],400).iloc[-1] if len(hr)>=400 else ema(hr['Close'],200).iloc[-1]
        if not (h200>h400 and w8>w20 and d8>d20): return None
        low_av=[]; high_av=[]
        for df,tf,win in [(hr,"H",12),(dy,"D",5),(wk,"W",3)]:
            for anc,sl in find_lows(df,win):
                av=avwap(df,anc)
                if av and av>sl*0.80 and av<sl*1.30: low_av.append((av,anc,tf,sl))
            for anc,sh in find_highs(df,win):
                av=avwap(df,anc)
                if av: high_av.append((av,anc,tf,sh))
        if len(low_av)<2: return None
        curr=float(hr['Close'].iloc[-1]); open_=float(hr['Open'].iloc[-1])
        for av_h,_,_,_ in high_av:
            if av_h>curr and (av_h-curr)/curr*100<5.0:
                return {"symbol":sym.replace(".NS",""),"skip":True,"price":round(curr,2),"high_avwp":round(av_h,2)}
        above=[x for x in low_av if x[0]<=curr]
        near=[x for x in above if abs(x[0]-curr)/curr*100<6.0]
        if len(near)<2: return None
        near=sorted(near, key=lambda x:x[0])
        cluster=[near[-1]]
        for a in reversed(near[:-1]):
            if abs(a[0]-cluster[0][0])/cluster[0][0]*100<1.5: cluster.append(a)
        if len(cluster)<2: return None
        c_avg=sum(c[0] for c in cluster)/len(cluster); c_low=min(c[0] for c in cluster); s_low=min(c[3] for c in cluster)
        dist_c=abs(curr-c_avg)/curr*100; dist_200=abs(curr-h200)/curr*100
        if dist_c<4.0 and dist_200<6.0 and curr>c_avg:
            small_sl=round(c_low*0.992,2); big_sl=round(s_low*0.99,2); risk=round((curr-small_sl)/curr*100,2)
            if risk>4.0: return None
            return {"symbol":sym.replace(".NS",""),"skip":False,"price":round(curr,2),"cluster_avg":round(c_avg,2),"cluster_count":len(cluster),"dist_cluster":round(dist_c,2),"ema200":round(float(h200),2),"dist_200":round(dist_200,2),"small_sl":small_sl,"big_sl":big_sl,"risk":risk,"signal":"BUY" if curr>open_ else "WATCH","anchors":", ".join([c[1].strftime('%d-%b %H:%M') for c in cluster[:3]])}
    except Exception as e:
        return None

buy=[]; skip=[]
print(f"Scanning {len(SYMBOLS)} symbols...")
for i,s in enumerate(SYMBOLS):
    if i%20==0: print(f"{i}/{len(SYMBOLS)}")
    r=scan(s)
    if r:
        if r.get("skip"): skip.append(r)
        else: buy.append(r)

ist=datetime.now().strftime('%d-%b %H:%M')
msg=f"🎯 *V9 NIFTY 200 - {ist} IST*\n*WTH + Above AVWP Cluster + Near 200EMA*\n*Scanned {len(SYMBOLS)} stocks*\n\n*BUY {len(buy)} - Kotak Model*\n"
# Top 15 best
for r in sorted(buy, key=lambda x: x['dist_cluster'])[:15]:
    msg+=f"\n✅ *{r['symbol']}* @ {r['price']} | {r['cluster_count']} AVWP {r['cluster_avg']} {r['dist_cluster']}% | 200 {r['ema200']} {r['dist_200']}% | SL {r['small_sl']}({r['risk']}%) Big {r['big_sl']}\n"

msg+=f"\n*SKIPPED {len(skip)} - Below HIGH AVWP Resistance*\n"
for s in skip[:8]: msg+=f"❌ {s['symbol']} @ {s['price']} < HIGH {s['high_avwp']}\n"
msg+=f"\n_15min auto refresh - Top 15 closest to AVWP cluster_"

print(msg)
# Force send on manual, anti-spam on auto
is_manual = os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch'
last_file="last_sniper.json"
curr_prices={r['symbol']:r['price'] for r in buy}
should=True
if not is_manual and os.path.exists(last_file):
    try:
        import json as js
        with open(last_file) as f: last=js.load(f)
        if len(last)==len(curr_prices):
            same=True
            for sym,price in curr_prices.items():
                if sym not in last or abs(price-last[sym])/last[sym]*100>0.4: same=False; break
            if same: should=False; print("No change - Skip TG")
    except: pass

if should or is_manual:
    send_telegram(msg)
    try:
        with open(last_file,'w') as f: json.dump(curr_prices,f)
    except: pass

if buy: pd.DataFrame(buy).to_csv("sniper_avwp_results.csv", index=False)
