# MASTER BOT 500 V15 ULTIMATE - ALL INCLUSIVE + WIN% + AUTO BEST 3
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

def get_market():
    try:
        n=yf.download("^NSEI",period="3mo",interval="1d",progress=False)
        b=yf.download("^NSEBANK",period="3mo",interval="1d",progress=False)
        if isinstance(n.columns,pd.MultiIndex): n.columns=n.columns.get_level_values(0)
        if isinstance(b.columns,pd.MultiIndex): b.columns=b.columns.get_level_values(0)
        n['EMA8']=n['Close'].ewm(8).mean(); n['EMA20']=n['Close'].ewm(20).mean(); n['EMA50']=n['Close'].ewm(50).mean()
        b['EMA8']=b['Close'].ewm(8).mean(); b['EMA20']=b['Close'].ewm(20).mean()
        n_pp,n_r1,n_r2,n_s1,n_s2,n_cmp=get_pivot(n)
        b_pp,b_r1,b_r2,b_s1,b_s2,b_cmp=get_pivot(b)
        n_dir="BULLISH ✅" if n['Close'].iloc[-1]>n['EMA20'].iloc[-1] and n['EMA8'].iloc[-1]>n['EMA20'].iloc[-1] else "BEARISH ⚠️" if n['Close'].iloc[-1]<n['EMA20'].iloc[-1] else "SIDEWAYS ➖"
        b_dir="BULLISH ✅" if b['Close'].iloc[-1]>b['EMA20'].iloc[-1] else "BEARISH ⚠️"
        return (n_dir,n_cmp,n_pp,n_r1,n_r2,n_s1,n_s2,float(n['EMA8'].iloc[-1]),float(n['EMA20'].iloc[-1]),float(n['EMA50'].iloc[-1])), (b_dir,b_cmp,b_pp,b_r1,b_r2,b_s1,b_s2)
    except:
        return ("N/A",0,0,0,0,0,0,0,0,0),("N/A",0,0,0,0,0,0)

def calculate_win_rate(df):
    """Backtest last 60 days how many times EMA8>EMA20 gave profit in 5 days"""
    try:
        wins=0; total=0
        for i in range(-60,-5):
            if df['Close'].iloc[i]>df['EMA20'].iloc[i] and df['EMA8'].iloc[i]>df['EMA20'].iloc[i]:
                total+=1
                future = float(df['Close'].iloc[i+5])
                entry = float(df['Close'].iloc[i])
                if future > entry*1.02: wins+=1
        return int((wins/total*100) if total>0 else 65)
    except:
        return 65

def analyze_full(symbol):
    try:
        df=yf.download(symbol+".NS",period="1y",interval="1d",progress=False)
        if df.empty or len(df)<200: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        
        df['EMA8']=df['Close'].ewm(8).mean(); df['EMA20']=df['Close'].ewm(20).mean()
        df['EMA50']=df['Close'].ewm(50).mean(); df['EMA200']=df['Close'].ewm(200).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3).rolling(20).mean()
        df['AVWAP']=df['Close'].ewm(50).mean()
        df['VolAvg']=df['Volume'].rolling(20).mean()
        
        diff=df['Close'].diff(); up=diff.clip(lower=0); down=-diff.clip(upper=0)
        rs=up.rolling(14).mean()/down.rolling(14).mean().replace(0,0.001)
        df['RSI14']=100-(100/(1+rs))
        rs9=diff.where(diff>0,0).rolling(9).mean()/(-diff.where(diff<0,0).rolling(9).mean().replace(0,0.001))
        df['RSI9']=100-(100/(1+rs9))
        df['EMA3_RSI']=df['RSI9'].ewm(3).mean(); df['WMA21_RSI']=wma(df['RSI9'],21)
        
        last=df.iloc[-1]
        price=float(last['Close'])
        rsi14=float(last['RSI14']); rsi9=float(last['RSI9'])
        ema8=float(last['EMA8']); ema20=float(last['EMA20']); ema50=float(last['EMA50']); ema200=float(last['EMA200'])
        vwap=float(last['VWAP']); avwap=float(last['AVWAP'])
        
        hm_bull = rsi9>50 and float(last['EMA3_RSI'])>float(last['WMA21_RSI'])
        hm_fresh = hm_bull and float(df['RSI9'].iloc[-2])<=50
        
        is_trending = price>ema8 and ema8>ema20 and ema20>ema50
        is_bala = is_trending and rsi14>60 and float(last['Volume'])>float(last['VolAvg'])
        is_hybrid = hm_bull and price>vwap and price>ema20
        is_safe = price>ema200 and abs(price-ema50)/price<0.05 and 50<rsi14<70
        is_pool = ema20>ema50 and abs(price-ema8)/price<0.02 and price>ema20
        
        # RANKING SYSTEM
        score=0
        if is_trending: score+=30
        if is_bala: score+=25
        if is_hybrid: score+=20
        if is_safe: score+=15
        if is_pool: score+=15
        if hm_bull: score+=25
        if hm_fresh: score+=15  # Extra for fresh HM buy
        
        if score<45: return None
        
        win_rate=calculate_win_rate(df)
        
        # FINAL RANK = Score + Win% + HM Bonus
        final_rank = score*0.6 + win_rate*0.4 + (10 if hm_fresh else 0)
        
        return {
            'Symbol':symbol, 'CMP':round(price,2), 'Score':score, 'Win%':win_rate, 'FinalRank':round(final_rank,1),
            'Category':"+".join([c for c,b in [("BALA",is_bala),("HM",hm_bull),("HYBRID",is_hybrid),("TREND",is_trending),("SAFE",is_safe),("POOL",is_pool)] if b]) or "V12",
            'EMA8':round(ema8,2), 'EMA20':round(ema20,2), 'EMA50':round(ema50,2), 'EMA200':round(ema200,2),
            'VWAP':round(vwap,2), 'AVWAP':round(avwap,2), 'RSI14':round(rsi14,1), 'RSI9':round(rsi9,1),
            'Entry':f"{round(price*0.998,2)}-{round(price*1.005,2)}", 'SL':round(min(ema20,ema50,vwap)*0.98,2),
            'T1':round(price*1.03,2), 'T2':round(price*1.06,2), 'Qty':int((CAPITAL*0.12)/price),
            'is_bala':is_bala, 'is_hybrid':is_hybrid, 'is_trending':is_trending, 'is_safe':is_safe, 'is_pool':is_pool, 'hm':hm_bull, 'hm_fresh':hm_fresh
        }
    except Exception as e:
        print(f"{symbol} {e}")
        return None

if __name__=="__main__":
    n_data,b_data=get_market()
    n_dir,n_cmp,n_pp,n_r1,n_r2,n_s1,n_s2,n_ema8,n_ema20,n_ema50=n_data
    b_dir,b_cmp,b_pp,b_r1,b_r2,b_s1,b_s2=b_data
    
    try:
        dflist=pd.read_csv("nifty500_list.csv")
        syms=dflist['Symbol'].tolist() if 'Symbol' in dflist.columns else dflist.iloc[:,0].tolist()
    except:
        syms=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","ADANIGREEN","ADANIPORTS","AXISBANK","AUROPHARMA","ANANDRATHI","ANGELONE","APLAPOLLO","ASTRAL","ASIANPAINT"]
    
    results=[]
    for s in syms[:350]:
        r=analyze_full(s.strip())
        if r: results.append(r)
    
    # SYSTEM DECIDES BEST 3 BY FINAL RANK = Score + Win% + HM
    results=sorted(results,key=lambda x:x['FinalRank'],reverse=True)
    bala=[x for x in results if x['is_bala']][:8]
    hilega=[x for x in results if x['hm']][:8]
    hybrid=[x for x in results if x['is_hybrid']][:8]
    trending=[x for x in results if x['is_trending']][:8]
    safe=[x for x in results if x['is_safe']][:8]
    pool=[x for x in results if x['is_pool']][:8]
    fresh_hm=[x for x in results if x['hm_fresh']][:5]
    best3=results[:3]
    
    msg=f"🚀 *MASTER BOT V15 ULTIMATE - {datetime.now().strftime('%d-%m %I:%M %p')}*\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n📊 *MARKET DIRECTION*\n"
    msg+=f"NIFTY {n_cmp:.0f} {n_dir}\n8E:{n_ema8:.0f} 20E:{n_ema20:.0f} 50E:{n_ema50:.0f}\nPP:{n_pp:.0f} R1:{n_r1:.0f} R2:{n_r2:.0f} S1:{n_s1:.0f} S2:{n_s2:.0f}\n\n"
    msg+=f"BANK {b_cmp:.0f} {b_dir}\nPP:{b_pp:.0f} R1:{b_r1:.0f} S1:{b_s1:.0f}\n"
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n✅ Scan: {len(results)} Stocks | Cap: Rs.{int(CAPITAL)}\n\n"
    
    if best3:
        msg+=f"🏆 *BEST 3 - AUTO SELECTED BY SYSTEM*\n*Rank = Score(60%) + Win%(40%) + HM Fresh Bonus*\n\n"
        for i,r in enumerate(best3,1):
            msg+=f"{i}. *{r['Symbol']}* FinalRank:{r['FinalRank']} (Score:{r['Score']} Win%:{r['Win%']}%)\n[{r['Category']}] {'🔥FRESH HM' if r['hm_fresh'] else ''}\nCMP:{r['CMP']} RSI:{r['RSI14']} HM RSI:{r['RSI9']}\n8E:{r['EMA8']} 20E:{r['EMA20']} 50E:{r['EMA50']} 200E:{r['EMA200']}\nVWAP:{r['VWAP']} AVWAP:{r['AVWAP']}\nEntry:{r['Entry']} T1:{r['T1']} T2:{r['T2']} SL:{r['SL']} Qty:{r['Qty']}\n\n"
    
    def add_section(title, lst):
        s=""
        if lst:
            s+=f"*{title} ({len(lst)})*\n"
            for r in lst[:5]:
                s+=f"{r['Symbol']} R:{r['FinalRank']} Win:{r['Win%']}% | {r['Category']} | {r['CMP']} SL:{r['SL']}\n"
            s+="\n"
        return s
    
    msg+=add_section("💎 HILEGA MILEGA FRESH",fresh_hm)
    msg+=add_section("🔥 BALA STOCKS",bala)
    msg+=add_section("💎 HILEGA MILEGA",hilega)
    msg+=add_section("⚡ HYBRID",hybrid)
    msg+=add_section("📈 TRENDING",trending)
    msg+=add_section("🛡️ TOP SAFE",safe)
    msg+=add_section("🔄 POOL BACK",pool)
    msg+=f"━━━━━━━━━━━━━━━━━━━━\n_System auto picks Best 3 by FinalRank. Trade with SL._"
    
    print(msg)
    send_telegram(msg)
    if results:
        pd.DataFrame(results).to_csv("nifty500_results.csv",index=False)
