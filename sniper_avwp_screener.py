# V11 FINAL - FORCE TELEGRAM EVERY 15 MINS - NO ANTI-SPAM BLOCK + PAPER TRADING
# V11.1 Force Enable Scheduled Runs - 06-Nov 2026
import yfinance as yf, pandas as pd, time, os, requests, json
from datetime import datetime, timedelta
from paper_trading import add_paper_trade, update_open_trades, generate_summary

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("SNIPER_BOT_TOKEN") or ""
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("SNIPER_CHAT_ID") or ""
EVENT = os.getenv("GITHUB_EVENT_NAME") or "manual"
print(f"=== V11 START Event={EVENT} ===")

try:
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
except:
    now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
print(f"IST Now: {now_ist.strftime('%d-%b %H:%M %A')}")

is_manual = EVENT == "workflow_dispatch"
if not is_manual:
    if now_ist.weekday() >= 5:
        print("Weekend - Skip"); exit(0)
    mins = now_ist.hour*60 + now_ist.minute
    if mins < 555 or mins > 940:
        print(f"Outside 9:15-15:40 - mins {mins} - Skip"); exit(0)

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("NO TOKEN"); print(msg); return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        for i in range(0, len(msg), 4000):
            r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg[i:i+4000], "parse_mode": "Markdown"}, timeout=30)
            print(f"TG {r.status_code}")
        return True
    except Exception as e:
        print(f"TG err {e}"); return False

SYMBOLS = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS","ADANIGREEN.NS","AMBUJACEM.NS","APOLLOTYRE.NS","ASHOKLEY.NS","ASTRAL.NS","AUBANK.NS","AUROPHARMA.NS","BANKBARODA.NS","BATAINDIA.NS","BERGEPAINT.NS","BHARATFORG.NS","BHEL.NS","BIOCON.NS","BOSCHLTD.NS","CANBK.NS","CHOLAFIN.NS","CUMMINSIND.NS","DABUR.NS","DALBHARAT.NS","DLF.NS","ESCORTS.NS","EXIDEIND.NS","FEDERALBNK.NS","GAIL.NS","GLENMARK.NS","GODREJCP.NS","GODREJPROP.NS","HAVELLS.NS","HEROMOTOCO.NS","HINDPETRO.NS","ICICIGI.NS","ICICIPRULI.NS","IDFCFIRSTB.NS","IGL.NS","INDHOTEL.NS","INDIAMART.NS","INDIGO.NS","IOC.NS","IPCALAB.NS","IRCTC.NS","JINDALSTEL.NS","JUBLFOOD.NS","LALPATHLAB.NS","LAURUSLABS.NS","LICI.NS","LTIM.NS","LTTS.NS","LUPIN.NS","M&MFIN.NS","MARICO.NS","MCDOWELL-N.NS","MFSL.NS","MGL.NS","MOTHERSON.NS","MPHASIS.NS","MUTHOOTFIN.NS","NAUKRI.NS","NAVINFLUOR.NS","NESTLEIND.NS","NMDC.NS","OBEROIRLTY.NS","OFSS.NS","PAGEIND.NS","PETRONET.NS","PIDILITIND.NS","PIIND.NS","PNB.NS","POLYCAB.NS","PVRINOX.NS","RAMCOCEM.NS","RBLBANK.NS","SAIL.NS","SBICARD.NS","SHREECEM.NS","SIEMENS.NS","SRF.NS","SUNTV.NS","TATACHEM.NS","TATACOMM.NS","TATACONSUM.NS","TATAMOTORS.NS","TORNTPHARM.NS","TORNTPOWER.NS","TVSMOTOR.NS","UBL.NS","UPL.NS","VOLTAS.NS","ZEEL.NS","ZYDUSLIFE.NS","ZOMATO.NS","PAYTM.NS","NYKAA.NS","POLICYBZR.NS"]

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
        time.sleep(0.15)
        wk=yf.download(sym,period="2y",interval="1wk",progress=False,auto_adjust=False)
        dy=yf.download(sym,period="1y",interval="1d",progress=False,auto_adjust=False)
        hr=yf.download(sym,period="6mo",interval="1h",progress=False,auto_adjust=False)
        if len(hr)<100 or len(dy)<60: return None
        for df in [wk,dy,hr]:
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        w8=ema(wk['Close'],8).iloc[-1]; w20=ema(wk['Close'],20).iloc[-1]
        d8=ema(dy['Close'],8).iloc[-1]; d20=ema(dy['Close'],20).iloc[-1]
        h200=ema(hr['Close'],200).iloc[-1] if len(hr)>=200 else ema(hr['Close'],100).iloc[-1]
        h400=ema(hr['Close'],400).iloc[-1] if len(hr)>=400 else ema(hr['Close'],200).iloc[-1]
        if not (h200>h400 and w8>w20 and d8>d20): return None
        low_av=[]; high_av=[]
        for df,_,win in [(hr,"H",12),(dy,"D",5),(wk,"W",3)]:
            for anc,sl in find_lows(df,win):
                av=avwap(df,anc)
                if av and av>sl*0.80 and av<sl*1.30: low_av.append((av,anc,sl))
            for anc,_ in find_highs(df,win):
                av=avwap(df,anc)
                if av: high_av.append((av,anc))
        if len(low_av)<2: return None
        curr=float(hr['Close'].iloc[-1])
        for av_h,_ in high_av:
            if av_h>curr and (av_h-curr)/curr*100<5.0:
                return {"skip":True,"symbol":sym.replace(".NS",""),"price":round(curr,2),"high_avwp":round(av_h,2)}
        above=[x for x in low_av if x[0]<=curr]
        near=[x for x in above if abs(x[0]-curr)/curr*100<6.0]
        if len(near)<2: return None
        near=sorted(near, key=lambda x:x[0])
        cluster=[near[-1]]
        for a in reversed(near[:-1]):
            if abs(a[0]-cluster[0][0])/cluster[0][0]*100<1.5: cluster.append(a)
        if len(cluster)<2: return None
        c_avg=sum(c[0] for c in cluster)/len(cluster); c_low=min(c[0] for c in cluster); s_low=min(c[2] for c in cluster)
        dist_c=abs(curr-c_avg)/curr*100; dist_200=abs(curr-h200)/curr*100
        if dist_c<4.0 and dist_200<6.0 and curr>c_avg:
            small_sl=round(c_low*0.992,2); big_sl=round(s_low*0.99,2); risk=round((curr-small_sl)/curr*100,2)
            if risk>4.0: return None
            return {"skip":False,"symbol":sym.replace(".NS",""),"price":round(curr,2),"cluster_avg":round(c_avg,2),"cluster_count":len(cluster),"dist_cluster":round(dist_c,2),"ema200":round(float(h200),2),"dist_200":round(dist_200,2),"small_sl":small_sl,"big_sl":big_sl,"risk":risk,"anchors":", ".join([c[1].strftime('%d-%b') for c in cluster[:3]])}
    except Exception as e:
        print(f"{sym} err {e}"); return None

buy=[]; skip=[]
print(f"Scanning {len(SYMBOLS)}...")
update_open_trades()
for i,s in enumerate(SYMBOLS):
    if i%20==0: print(f"{i}/{len(SYMBOLS)}")
    r=scan(s)
    if r:
        (skip if r['skip'] else buy).append(r)

# PAPER TRADING - V11
for r in buy:
    try:
        price = r['price']
        sl = r['small_sl']
        risk = price - sl
        if risk <= 0: continue
        tgt = round(price + (risk * 1.5), 2)
        qty = max(1, int(33333 / risk))
        add_paper_trade(r['symbol'], price, sl, tgt, qty)
    except Exception as e:
        print(f"Paper trade error {r['symbol']} {e}")

paper_summary = generate_summary()

ist_str=now_ist.strftime('%d-%b %H:%M IST')
if len(buy)==0:
    msg=f"🎯 *V11 NIFTY 200 - {ist_str}*\n*WTH + AVWP Cluster + Near 200EMA*\n*Scanned {len(SYMBOLS)}*\n\n*BUY 0 - No setup now*\n_Market open - No Kotak model found in this 15min_\n\nSKIPPED {len(skip)} - Below HIGH AVWP Resistance\n"
    for s in skip[:5]: msg+=f"❌ {s['symbol']} @ {s['price']} < {s['high_avwp']}\n"
else:
    msg=f"🎯 *V11 NIFTY 200 - {ist_str}*\n*WTH + Above AVWP Cluster + Near 200EMA*\n*Scanned {len(SYMBOLS)}*\n\n*BUY {len(buy)} - Kotak Model*\n"
    for r in sorted(buy, key=lambda x:x['dist_cluster'])[:15]:
        msg+=f"\n✅ *{r['symbol']}* @ {r['price']} | {r['cluster_count']} AVWP {r['cluster_avg']} {r['dist_cluster']}% | 200 {r['ema200']} {r['dist_200']}% | SL {r['small_sl']}({r['risk']}%)\n"
    msg+=f"\nSKIPPED {len(skip)}\n"

msg+=f"\n\n{generate_summary()}"

print(msg)
send_tg(msg)
try:
    pd.DataFrame(buy).to_csv("sniper_avwp_results.csv", index=False)
except: pass
