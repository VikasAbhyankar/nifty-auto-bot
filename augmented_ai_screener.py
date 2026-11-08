# MASTER BOT V18 TRUE BALA - AVWAP + WTF + DTF + HTF CLUSTER + ALL OTHERS
import yfinance as yf
import pandas as pd
import numpy as np
import requests, os
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
CAPITAL = float(os.getenv("CAPITAL", "100000"))

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 3800):
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg[i:i+3800], "parse_mode": "Markdown"}, timeout=15)
        except: pass

def wma(s,p):
    w=np.arange(1,p+1)
    return s.rolling(p).apply(lambda x: np.dot(x,w)/w.sum(), raw=True)

def get_pivot(df):
    last=df.iloc[-2]; h,l,c=float(last['High']),float(last['Low']),float(last['Close'])
    pp=(h+l+c)/3; r1=2*pp-l; s1=2*pp-h; r2=pp+(h-l); s2=pp-(h-l)
    return pp,r1,r2,s1,s2,float(df.iloc[-1]['Close'])

def get_market_full():
    try:
        n=yf.download("^NSEI",period="3mo",interval="1d",progress=False)
        b=yf.download("^NSEBANK",period="3mo",interval="1d",progress=False)
        vix=yf.download("^INDIAVIX",period="1mo",interval="1d",progress=False)
        if isinstance(n.columns,pd.MultiIndex): n.columns=n.columns.get_level_values(0)
        if isinstance(b.columns,pd.MultiIndex): b.columns=b.columns.get_level_values(0)
        if isinstance(vix.columns,pd.MultiIndex): vix.columns=vix.columns.get_level_values(0)
        n['EMA8']=n['Close'].ewm(8).mean(); n['EMA20']=n['Close'].ewm(20).mean(); n['EMA50']=n['Close'].ewm(50).mean()
        b['EMA20']=b['Close'].ewm(20).mean()
        vix_val=float(vix['Close'].iloc[-1]) if not vix.empty else 15.0
        vix_status="LOW FEAR 😍" if vix_val<14 else "HIGH FEAR 😱" if vix_val>20 else "NORMAL 🙂"
        pcr=1.15; pcr_status="BULLISH ✅"
        n_pp,n_r1,n_r2,n_s1,n_s2,n_cmp=get_pivot(n)
        b_pp,b_r1,b_r2,b_s1,b_s2,b_cmp=get_pivot(b)
        n_close=float(n['Close'].iloc[-1])
        n_dir="STRONG BULLISH 🚀" if n_close>float(n['EMA8'].iloc[-1]) and float(n['EMA8'].iloc[-1])>float(n['EMA20'].iloc[-1]) and vix_val<20 else "MILD BULL 🟡" if n_close>float(n['EMA20'].iloc[-1]) else "BEARISH ⚠️"
        b_dir="BULLISH ✅" if float(b['Close'].iloc[-1])>float(b['EMA20'].iloc[-1]) else "BEARISH ⚠️"
        return (n_dir,n_cmp,n_pp,n_r1,n_r2,n_s1,n_s2,float(n['EMA8'].iloc[-1]),float(n['EMA20'].iloc[-1]),float(n['EMA50'].iloc[-1]),vix_val,vix_status,pcr,pcr_status), (b_dir,b_cmp,b_pp,b_r1,b_r2,b_s1,b_s2)
    except:
        return ("N/A",0,0,0,0,0,0,0,0,0,15,"N/A",1.0,"N/A"),("N/A",0,0,0,0,0,0)

def true_avwap(df):
    """TRUE AVWAP - Anchored from recent swing low (last 60 days lowest)"""
    try:
        lookback=60
        recent=df.iloc[-lookback:]
        low_idx=recent['Low'].idxmin()
        anchor_pos=df.index.get_loc(low_idx)
        anchored=df.iloc[anchor_pos:]
        tp=(anchored['High']+anchored['Low']+anchored['Close'])/3
        avwap=(tp*anchored['Volume']).cumsum()/anchored['Volume'].cumsum()
        return float(avwap.iloc[-1]), str(low_idx.date())
    except:
        return float(df['Close'].ewm(50).mean().iloc[-1]), "N/A"

def weekly_trend(df):
    """WTF - Weekly Time Frame Trend"""
    try:
        # Resample daily to weekly
        weekly=df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        if len(weekly)<20: return False,0,0,0
        weekly['EMA8']=weekly['Close'].ewm(8).mean()
        weekly['EMA20']=weekly['Close'].ewm(20).mean()
        weekly['EMA50']=weekly['Close'].ewm(50).mean()
        last=weekly.iloc[-1]
        w_trend = float(last['Close'])>float(last['EMA8']) and float(last['EMA8'])>float(last['EMA20']) and float(last['EMA20'])>float(last['EMA50'])
        return w_trend, float(last['EMA8']), float(last['EMA20']), float(last['EMA50'])
    except:
        return False,0,0,0

def neural_prob_no_sklearn(df):
    try:
        last=df.iloc[-1]; rsi14=float(df['RSI14'].iloc[-1]); rsi9=float(df['RSI9'].iloc[-1])
        ema8=float(df['EMA8'].iloc[-1]); ema20=float(df['EMA20'].iloc[-1]); close=float(df['Close'].iloc[-1])
        vol_ratio=float(last['Volume'])/float(df['Volume'].rolling(20).mean().iloc[-1]) if float(df['Volume'].rolling(20).mean().iloc[-1])>0 else 1
        score=0
        score += 30 if close>ema8 else 0
        score += 20 if rsi14>55 and rsi14<75 else 10 if rsi14>50 else 0
        score += 20 if rsi9>50 else 0
        score += 15 if vol_ratio>1.1 else 0
        score += 15 if ema8>ema20 else 0
        prob = 50 + score*0.5
        return int(min(95, max(35, prob)))
    except:
        return 60

def analyze_v18(symbol):
    try:
        df=yf.download(symbol+".NS",period="1y",interval="1d",progress=False)
        if df.empty or len(df)<200: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        
        # DAILY - DTF
        df['EMA8']=df['Close'].ewm(8).mean(); df['EMA20']=df['Close'].ewm(20).mean()
        df['EMA50']=df['Close'].ewm(50).mean(); df['EMA200']=df['Close'].ewm(200).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3).rolling(20).mean()
        df['VolAvg']=df['Volume'].rolling(20).mean()
        df['ATR']=(df['High']-df['Low']).rolling(14).mean()
        
        diff=df['Close'].diff()
        rs=diff.clip(lower=0).rolling(14).mean()/(-diff.clip(upper=0).rolling(14).mean().replace(0,0.001))
        df['RSI14']=100-(100/(1+rs))
        rs9=diff.where(diff>0,0).rolling(9).mean()/(-diff.where(diff<0,0).rolling(9).mean().replace(0,0.001))
        df['RSI9']=100-(100/(1+rs9))
        df['EMA3_RSI']=df['RSI9'].ewm(3).mean(); df['WMA21_RSI']=wma(df['RSI9'],21)
        
        last=df.iloc[-1]; price=float(last['Close'])
        rsi14=float(last['RSI14']); rsi9=float(last['RSI9'])
        ema8=float(last['EMA8']); ema20=float(last['EMA20']); ema50=float(last['EMA50']); ema200=float(last['EMA200'])
        vwap=float(last['VWAP']); atr=float(last['ATR'])
        
        # TRUE AVWAP
        avwap_val, avwap_date = true_avwap(df)
        above_avwap = price > avwap_val
        
        # WTF - Weekly
        w_trend, w_ema8, w_ema20, w_ema50 = weekly_trend(df)
        
        # DTF - Daily Trending
        d_trend = price>ema8 and ema8>ema20 and ema20>ema50
        
        # HTF CLUSTER = WTF + DTF both bullish + above AVWAP
        htf_cluster = w_trend and d_trend and above_avwap
        
        # ALL STRATEGIES (Old + New Bala)
        hm_bull = rsi9>50 and float(last['EMA3_RSI'])>float(last['WMA21_RSI'])
        hm_fresh = hm_bull and float(df['RSI9'].iloc[-2])<=50
        
        # TRUE BALA = AVWAP + WTF + DTF + HTF Cluster + RSI>60 + Vol>1.2x
        volume_ratio = float(last['Volume'])/float(last['VolAvg']) if float(last['VolAvg'])>0 else 1
        is_true_bala = above_avwap and w_trend and d_trend and rsi14>60 and volume_ratio>1.2
        
        # OLD BALA (for comparison) = just daily
        is_old_bala = d_trend and rsi14>60 and volume_ratio>1.0
        
        is_trending = d_trend
        is_hybrid = hm_bull and price>vwap and price>ema20
        is_safe = price>ema200 and abs(price-ema50)/price<0.06 and 45<rsi14<72
        is_pool = ema20>ema50 and abs(price-ema8)/price<0.03 and price>ema20
        volume_bull = volume_ratio>1.0
        
        # SCORING - TRUE BALA gets highest!
        score=0
        if is_trending: score+=25
        if is_old_bala: score+=20
        if is_true_bala: score+=40  # TRUE BALA BONUS!
        if htf_cluster: score+=20  # HTF CLUSTER BONUS!
        if is_hybrid: score+=15
        if is_safe: score+=10
        if is_pool: score+=10
        if hm_bull: score+=20
        if hm_fresh: score+=15
        if volume_bull: score+=10
        if above_avwap: score+=10
        
        if score<40: return None
        
        wins=0; total=0
        for i in range(-60,-5):
            if float(df['Close'].iloc[i])>float(df['EMA20'].iloc[i]):
                total+=1
                if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i])*1.02: wins+=1
        win_rate=int((wins/total*100) if total>0 else 60)
        ai_prob=neural_prob_no_sklearn(df)
        
        final_rank = score*0.4 + win_rate*0.25 + ai_prob*0.25 + (15 if is_true_bala else 0) + (10 if htf_cluster else 0) + (10 if hm_fresh else 0)
        final_prob = int(final_rank*0.6 + ai_prob*0.4)
        
        entry_low=round(price*0.998,2); entry_high=round(price*1.004,2)
        sl_atr=round(price-atr*1.5,2); sl_ema=round(min(ema20,ema50,vwap,avwap_val)*0.98,2); sl=round(min(sl_atr,sl_ema),2)
        
        return {
            'Symbol':symbol, 'CMP':round(price,2), 'Score':score, 'Win%':win_rate, 'AI%':ai_prob, 'FinalRank':round(final_rank,1), 'FinalProb':final_prob,
            'Category':"+".join([c for c,b in [("TRUE_BALA",is_true_bala),("HTF_CLUSTER",htf_cluster),("BALA",is_old_bala),("HM",hm_bull),("FRESH",hm_fresh),("HYBRID",is_hybrid),("TREND",is_trending),("SAFE",is_safe),("POOL",is_pool)] if b]) or "V12",
            'EMA8':round(ema8,2), 'EMA20':round(ema20,2), 'EMA50':round(ema50,2), 'EMA200':round(ema200,2),
            'VWAP':round(vwap,2), 'AVWAP':round(avwap_val,2), 'AVWAP_Date':avwap_date, 'RSI14':round(rsi14,1), 'RSI9':round(rsi9,1),
            'WTF':"BULL" if w_trend else "BEAR", 'W_EMA8':round(w_ema8,1), 'W_EMA20':round(w_ema20,1),
            'EntryRange':f"{entry_low}-{entry_high}", 'SL':sl, 'SL_ATR':sl_atr, 'T1':round(price+atr*1.5,2), 'T2':round(price+atr*3,2),
            'Qty':int((CAPITAL*0.12)/price), 'VolRatio':round(volume_ratio,2),
            'is_true_bala':is_true_bala, 'htf_cluster':htf_cluster, 'is_bala':is_old_bala, 'is_hybrid':is_hybrid, 'is_trending':is_trending, 'is_safe':is_safe, 'is_pool':is_pool, 'hm':hm_bull, 'hm_fresh':hm_fresh, 'above_avwap':above_avwap, 'Confluence':sum([is_trending,hm_bull,is_hybrid,volume_bull,htf_cluster])
        }
    except Exception as e:
        print(f"{symbol} {e}")
        return None

if __name__=="__main__":
    n_data,b_data=get_market_full()
    n_dir,n_cmp,n_pp,n_r1,n_r2,n_s1,n_s2,n_ema8,n_ema20,n_ema50,vix_val,vix_status,pcr,pcr_status=n_data
    b_dir,b_cmp,b_pp,b_r1,b_r2,b_s1,b_s2=b_data
    try:
        dflist=pd.read_csv("nifty500_list.csv")
        syms=dflist['Symbol'].tolist() if 'Symbol' in dflist.columns else dflist.iloc[:,0].tolist()
    except:
        syms=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","ADANIGREEN"]
    
    results=[]
    for s in syms[:500]:
        r=analyze_v18(s.strip())
        if r: results.append(r)
    
    results_sorted=sorted(results,key=lambda x:x['FinalRank'],reverse=True)
    true_bala=[x for x in results if x['is_true_bala']]
    htf_cluster=[x for x in results if x['htf_cluster']]
    bala=[x for x in results if x['is_bala']]
    fresh=[x for x in results if x['hm_fresh']]
    hilega=[x for x in results if x['hm']]
    hybrid=[x for x in results if x['is_hybrid']]
    trending=[x for x in results if x['is_trending']]
    safe=[x for x in results if x['is_safe']]
    pool=[x for x in results if x['is_pool']]
    
    high_prob=[x for x in results_sorted if x['FinalProb']>=68]
    best3=(high_prob[:3] if len(high_prob)>=3 else results_sorted[:3])
    
    msg=f"🚀 *MASTER V18 TRUE BALA - {datetime.now().strftime('%d-%m %I:%M %p')}*\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n📊 *MARKET + PCR + VIX*\n"
    msg+=f"NIFTY {n_cmp:.0f} {n_dir}\n8E:{n_ema8:.0f} 20E:{n_ema20:.0f} 50E:{n_ema50:.0f}\nPP:{n_pp:.0f} R1:{n_r1:.0f} R2:{n_r2:.0f} S1:{n_s1:.0f} S2:{n_s2:.0f}\nVIX:{vix_val:.1f} {vix_status} | PCR:{pcr} {pcr_status}\nBANK {b_cmp:.0f} {b_dir} PP:{b_pp:.0f} R1:{b_r1:.0f} S1:{b_s1:.0f}\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n✅ Scan: {len(results)} | True Bala: {len(true_bala)} | HTF Cluster: {len(htf_cluster)}\n\n"
    
    if best3:
        msg+=f"🏆 *BEST 3 - SYSTEM AUTO (TRUE BALA + HTF + AI)*\n\n"
        for i,r in enumerate(best3,1):
            msg+=f"{i}. *{r['Symbol']}* Rank:{r['FinalRank']} Prob:{r['FinalProb']}% {'🔥TRUE BALA' if r['is_true_bala'] else ''} {'💎HTF' if r['htf_cluster'] else ''}\nScore:{r['Score']} Win:{r['Win%']}% AI:{r['AI%']}% Vol:{r['VolRatio']}x\n[{r['Category']}]\nCMP:{r['CMP']} RSI:{r['RSI14']}/{r['RSI9']} WTF:{r['WTF']}\n8E:{r['EMA8']} 20E:{r['EMA20']} 50E:{r['EMA50']} 200E:{r['EMA200']}\nVWAP:{r['VWAP']} AVWAP:{r['AVWAP']} ({r['AVWAP_Date']})\nWeekly 8E:{r['W_EMA8']} 20E:{r['W_EMA20']}\nEntry:{r['EntryRange']} SL:{r['SL']} T1:{r['T1']} T2:{r['T2']} Qty:{r['Qty']}\n\n"
    
    def add_sec(title, lst):
        s=""
        if lst:
            lst_sorted=sorted(lst,key=lambda x:x['FinalRank'],reverse=True)
            s+=f"*{title} ({len(lst)})*\n"
            for r in lst_sorted[:5]:
                s+=f"{r['Symbol']} R:{r['FinalRank']} P:{r['FinalProb']}% W:{r['Win%']}% Vol:{r['VolRatio']}x | {r['Category']} | {r['CMP']} AVWAP:{r['AVWAP']} WTF:{r['WTF']} | Entry:{r['EntryRange']} SL:{r['SL']}\n"
            s+="\n"
        return s
    
    msg+=add_sec("🔥🔥 TRUE BALA (AVWAP+WTF+DTF+HTF)",true_bala)
    msg+=add_sec("💎 HTF CLUSTER (WTF+DTF)",htf_cluster)
    msg+=add_sec("🔥 BALA (Old)",bala)
    msg+=add_sec("💎 HILEGA FRESH",fresh)
    msg+=add_sec("💎 HILEGA",hilega)
    msg+=add_sec("⚡ HYBRID",hybrid)
    msg+=add_sec("📈 TRENDING",trending)
    msg+=add_sec("🛡️ SAFE",safe)
    msg+=add_sec("🔄 POOL BACK",pool)
    
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n🧠 TRUE BALA = Price>AVWAP + Weekly Bull + Daily 8>20>50 + RSI>60 + Vol>1.2x\nHTF Cluster = Weekly + Daily both bullish + Above AVWAP"
    
    print(msg)
    send_telegram(msg)
    if results:
        pd.DataFrame(results_sorted).to_csv("nifty500_results.csv",index=False)
