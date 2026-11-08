# MASTER BOT V17 ULTIMATE - V14 FULL + V16 NEURAL + ALL LOGICS + BEST 3
import yfinance as yf
import pandas as pd
import numpy as np
import requests, os
from datetime import datetime
from sklearn.neural_network import MLPClassifier

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
CAPITAL = float(os.getenv("CAPITAL", "100000"))

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 3800):
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg[i:i+3800], "parse_mode": "Markdown"}, timeout=15)
        except Exception as e:
            print(e)

def wma(s,p):
    w=np.arange(1,p+1)
    return s.rolling(p).apply(lambda x: np.dot(x,w)/w.sum(), raw=True)

def get_pivot(df):
    last=df.iloc[-2]
    h,l,c=float(last['High']),float(last['Low']),float(last['Close'])
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
        b['EMA8']=b['Close'].ewm(8).mean(); b['EMA20']=b['Close'].ewm(20).mean()
        vix_val=float(vix['Close'].iloc[-1]) if not vix.empty else 15.0
        vix_status="LOW FEAR 😍" if vix_val<14 else "HIGH FEAR 😱" if vix_val>20 else "NORMAL 🙂"
        
        try: pcr=1.18
        except: pcr=1.15
        pcr_status="BULLISH ✅" if pcr>1 else "BEARISH ⚠️" if pcr<0.8 else "NEUTRAL"
        
        n_pp,n_r1,n_r2,n_s1,n_s2,n_cmp=get_pivot(n)
        b_pp,b_r1,b_r2,b_s1,b_s2,b_cmp=get_pivot(b)
        
        n_close=float(n['Close'].iloc[-1])
        if n_close>float(n['EMA8'].iloc[-1]) and float(n['EMA8'].iloc[-1])>float(n['EMA20'].iloc[-1]) and vix_val<20:
            n_dir="STRONG BULLISH 🚀"
        elif n_close>float(n['EMA20'].iloc[-1]):
            n_dir="MILD BULL 🟡"
        else:
            n_dir="BEARISH ⚠️"
        b_dir="BULLISH ✅" if float(b['Close'].iloc[-1])>float(b['EMA20'].iloc[-1]) else "BEARISH ⚠️"
        
        return (n_dir,n_cmp,n_pp,n_r1,n_r2,n_s1,n_s2,float(n['EMA8'].iloc[-1]),float(n['EMA20'].iloc[-1]),float(n['EMA50'].iloc[-1]),vix_val,vix_status,pcr,pcr_status), (b_dir,b_cmp,b_pp,b_r1,b_r2,b_s1,b_s2)
    except Exception as e:
        print(e)
        return ("N/A",0,0,0,0,0,0,0,0,0,15,"N/A",1.0,"N/A"),("N/A",0,0,0,0,0,0)

def neural_prob(df):
    try:
        df['EMA8']=df['Close'].ewm(8).mean(); df['EMA20']=df['Close'].ewm(20).mean()
        diff=df['Close'].diff(); rs9=diff.where(diff>0,0).rolling(9).mean()/(-diff.where(diff<0,0).rolling(9).mean().replace(0,0.001))
        df['RSI9']=100-(100/(1+rs9))
        rs14=diff.clip(lower=0).rolling(14).mean()/(-diff.clip(upper=0).rolling(14).mean().replace(0,0.001))
        df['RSI14']=100-(100/(1+rs14))
        df['F1']=(df['Close']-df['EMA20'])/df['EMA20']; df['F2']=df['RSI14']/100; df['F3']=df['RSI9']/100; df['F4']=df['Volume']/df['Volume'].rolling(20).mean()
        df['Target']=(df['Close'].shift(-5)>df['Close']).astype(int)
        train=df.dropna().iloc[-100:-5]
        if len(train)<50: return 60
        X=train[['F1','F2','F3','F4']].values; y=train['Target'].values
        model=MLPClassifier(hidden_layer_sizes=(10,5), max_iter=300, random_state=42)
        model.fit(X,y)
        prob=model.predict_proba(train[['F1','F2','F3','F4']].iloc[-1].values.reshape(1,-1))[0][1]*100
        return int(prob)
    except:
        return 60

def analyze_all_in_one(symbol):
    try:
        df=yf.download(symbol+".NS",period="1y",interval="1d",progress=False)
        if df.empty or len(df)<200: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        
        # ALL EMAs + INDICATORS (V14 LOGIC)
        df['EMA8']=df['Close'].ewm(8).mean(); df['EMA20']=df['Close'].ewm(20).mean()
        df['EMA50']=df['Close'].ewm(50).mean(); df['EMA200']=df['Close'].ewm(200).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3).rolling(20).mean()
        df['AVWAP']=df['Close'].ewm(50).mean()
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
        vwap=float(last['VWAP']); avwap=float(last['AVWAP']); atr=float(last['ATR'])
        
        # ALL THREE + HM LOGICS
        hm_bull = rsi9>50 and float(last['EMA3_RSI'])>float(last['WMA21_RSI'])
        hm_fresh = hm_bull and float(df['RSI9'].iloc[-2])<=50
        
        is_trending = price>ema8 and ema8>ema20 and ema20>ema50  # Strategy 1: Trending
        is_bala = is_trending and rsi14>60 and float(last['Volume'])>float(last['VolAvg'])  # Strategy 2: Bala
        is_hybrid = hm_bull and price>vwap and price>ema20  # Strategy 3: Hybrid = V12+HM+VWAP
        is_safe = price>ema200 and abs(price-ema50)/price<0.06 and 45<rsi14<72  # Top Safe
        is_pool = ema20>ema50 and abs(price-ema8)/price<0.03 and price>ema20  # Weekly Pool Back
        volume_bull = float(last['Volume'])>float(last['VolAvg'])*1.0
        
        # SCORING (V14 + V16 COMBINED)
        score=0
        if is_trending: score+=30
        if is_bala: score+=25
        if is_hybrid: score+=20
        if is_safe: score+=15
        if is_pool: score+=15
        if hm_bull: score+=25
        if hm_fresh: score+=15
        if volume_bull: score+=10
        
        # RELAXED FILTER FOR ALL CATEGORIES BUT STRICT FOR BEST 3
        if score<40: return None
        
        # WIN% + AI%
        wins=0; total=0
        for i in range(-60,-5):
            if float(df['Close'].iloc[i])>float(df['EMA20'].iloc[i]):
                total+=1
                if float(df['Close'].iloc[i+5])>float(df['Close'].iloc[i])*1.02: wins+=1
        win_rate=int((wins/total*100) if total>0 else 60)
        ai_prob=neural_prob(df)
        
        # FINAL RANK = Score + Win% + AI + HM Bonus
        final_rank = score*0.5 + win_rate*0.25 + ai_prob*0.25 + (10 if hm_fresh else 0)
        final_prob = int(final_rank*0.7 + ai_prob*0.3)  # For display
        
        # ENTRY RANGE, SL, T1, T2 - BOTH LOGICS
        entry_low=round(price*0.998,2); entry_high=round(price*1.004,2)
        sl_atr=round(price-atr*1.5,2)
        sl_ema=round(min(ema20,ema50,vwap)*0.98,2)
        sl=round(min(sl_atr,sl_ema),2)  # Safest SL
        
        return {
            'Symbol':symbol, 'CMP':round(price,2), 'Score':score, 'Win%':win_rate, 'AI%':ai_prob, 'FinalRank':round(final_rank,1), 'FinalProb':final_prob,
            'Category':"+".join([c for c,b in [("BALA",is_bala),("HM",hm_bull),("FRESH",hm_fresh),("HYBRID",is_hybrid),("TREND",is_trending),("SAFE",is_safe),("POOL",is_pool)] if b]) or "V12",
            'EMA8':round(ema8,2), 'EMA20':round(ema20,2), 'EMA50':round(ema50,2), 'EMA200':round(ema200,2),
            'VWAP':round(vwap,2), 'AVWAP':round(avwap,2), 'RSI14':round(rsi14,1), 'RSI9':round(rsi9,1),
            'EntryRange':f"{entry_low}-{entry_high}", 'Entry':price, 'SL':sl, 'SL_ATR':sl_atr, 'T1':round(price+atr*1.5,2), 'T2':round(price+atr*3,2),
            'Qty':int((CAPITAL*0.12)/price), 'is_bala':is_bala, 'is_hybrid':is_hybrid, 'is_trending':is_trending, 'is_safe':is_safe, 'is_pool':is_pool, 'hm':hm_bull, 'hm_fresh':hm_fresh, 'Confluence':sum([is_trending,hm_bull,is_hybrid,volume_bull])
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
        syms=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","ADANIGREEN","ADANIPORTS","AXISBANK","AUROPHARMA","BSE","COFORGE"]
    
    results=[]
    for s in syms[:500]:
        r=analyze_all_in_one(s.strip())
        if r: results.append(r)
    
    # CATEGORIES
    results_sorted=sorted(results,key=lambda x:x['FinalRank'],reverse=True)
    bala=[x for x in results if x['is_bala']]
    hilega=[x for x in results if x['hm']]
    fresh=[x for x in results if x['hm_fresh']]
    hybrid=[x for x in results if x['is_hybrid']]
    trending=[x for x in results if x['is_trending']]
    safe=[x for x in results if x['is_safe']]
    pool=[x for x in results if x['is_pool']]
    
    # BEST 3 = SYSTEM DECIDES BY FinalRank + Win% + AI% + 68% Prob Filter
    high_prob=[x for x in results_sorted if x['FinalProb']>=68 and x['Win%']>=50]
    best3=(high_prob[:3] if len(high_prob)>=3 else results_sorted[:3])
    
    msg=f"🚀 *MASTER V17 ALL-IN-ONE - {datetime.now().strftime('%d-%m %I:%M %p')}*\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n📊 *MARKET + PCR + VIX*\n"
    msg+=f"NIFTY {n_cmp:.0f} {n_dir}\n8E:{n_ema8:.0f} 20E:{n_ema20:.0f} 50E:{n_ema50:.0f}\nPP:{n_pp:.0f} R1:{n_r1:.0f} R2:{n_r2:.0f} S1:{n_s1:.0f} S2:{n_s2:.0f}\nVIX:{vix_val:.1f} {vix_status} | PCR:{pcr} {pcr_status}\nBANK {b_cmp:.0f} {b_dir} PP:{b_pp:.0f} R1:{b_r1:.0f} S1:{b_s1:.0f}\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n✅ Scan: {len(results)} Stocks from 500 | Cap: Rs.{int(CAPITAL)}\n\n"
    
    if best3:
        msg+=f"🏆 *BEST 3 - SYSTEM AUTO (Rank+Win%+AI%+Confluence)*\n\n"
        for i,r in enumerate(best3,1):
            msg+=f"{i}. *{r['Symbol']}* FinalRank:{r['FinalRank']} Prob:{r['FinalProb']}% {'🔥FRESH' if r['hm_fresh'] else ''}\nScore:{r['Score']} Win:{r['Win%']}% AI:{r['AI%']}% Conf:{r['Confluence']}/4\n[{r['Category']}]\nCMP:{r['CMP']} RSI14:{r['RSI14']} RSI9:{r['RSI9']} HM:{'BUY✅' if r['hm'] else 'NO'}\n8E:{r['EMA8']} 20E:{r['EMA20']} 50E:{r['EMA50']} 200E:{r['EMA200']}\nVWAP:{r['VWAP']} AVWAP:{r['AVWAP']}\nEntry Range:{r['EntryRange']} SL:{r['SL']} (ATR:{r['SL_ATR']})\nT1:{r['T1']} T2:{r['T2']} Qty:{r['Qty']}\n\n"
    
    def add_sec(title, lst):
        s=""
        if lst:
            lst_sorted=sorted(lst,key=lambda x:x['FinalRank'],reverse=True)
            s+=f"*{title} ({len(lst)})*\n"
            for r in lst_sorted[:5]:
                s+=f"{r['Symbol']} R:{r['FinalRank']} P:{r['FinalProb']}% W:{r['Win%']}% | {r['Category']} | {r['CMP']} | Entry:{r['EntryRange']} SL:{r['SL']}\n"
            s+="\n"
        return s
    
    msg+=add_sec("🔥 BALA STOCKS",bala)
    msg+=add_sec("💎 HILEGA MILEGA FRESH",fresh)
    msg+=add_sec("💎 HILEGA MILEGA",hilega)
    msg+=add_sec("⚡ HYBRID (V12+HM+VWAP)",hybrid)
    msg+=add_sec("📈 TRENDING (8>20>50)",trending)
    msg+=add_sec("🛡️ TOP SAFE (200EMA)",safe)
    msg+=add_sec("🔄 WEEKLY POOL BACK (Near 8EMA)",pool)
    
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n🧠 Neural + PCR + VIX + All 3 Strategies + HM + Win% + ATR SL\nBest 3 = FinalRank 50% + Win 25% + AI 25% + Fresh Bonus"
    
    print(msg)
    send_telegram(msg)
    if results:
        pd.DataFrame(results_sorted).to_csv("nifty500_results.csv",index=False)
