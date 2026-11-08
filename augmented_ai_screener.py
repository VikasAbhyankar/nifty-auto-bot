# MASTER BOT 500 V12.3 + ALL 3 STRATEGIES + MARKET LEVELS - FINAL
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
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(r.text)
    except Exception as e:
        print(f"Telegram Error {e}")

def wma(s, p):
    w = np.arange(1, p+1)
    return s.rolling(p).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)

def get_pivot_levels(df):
    last = df.iloc[-2]  # yesterday for levels
    h, l, c = last['High'], last['Low'], last['Close']
    pp = (h+l+c)/3
    r1 = 2*pp - l; s1 = 2*pp - h
    r2 = pp + (h-l); s2 = pp - (h-l)
    return pp, r1, r2, s1, s2, last['Close']

def get_market_status():
    try:
        nifty = yf.download("^NSEI", period="2mo", interval="1d", progress=False)
        bank = yf.download("^NSEBANK", period="2mo", interval="1d", progress=False)
        if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.get_level_values(0)
        if isinstance(bank.columns, pd.MultiIndex): bank.columns = bank.columns.get_level_values(0)
        
        nifty['EMA20'] = nifty['Close'].ewm(20).mean()
        nifty['EMA50'] = nifty['Close'].ewm(50).mean()
        bank['EMA20'] = bank['Close'].ewm(20).mean()
        
        n_pp, n_r1, n_r2, n_s1, n_s2, n_cmp = get_pivot_levels(nifty)
        b_pp, b_r1, b_r2, b_s1, b_s2, b_cmp = get_pivot_levels(bank)
        
        n_dir = "BULLISH ✅" if nifty['Close'].iloc[-1] > nifty['EMA20'].iloc[-1] and nifty['EMA20'].iloc[-1] > nifty['EMA50'].iloc[-1] else "BEARISH ⚠️" if nifty['Close'].iloc[-1] < nifty['EMA20'].iloc[-1] else "SIDEWAYS ➖"
        b_dir = "BULLISH ✅" if bank['Close'].iloc[-1] > bank['EMA20'].iloc[-1] else "BEARISH ⚠️"
        
        return (n_dir, n_cmp, n_pp, n_r1, n_r2, n_s1, n_s2), (b_dir, b_cmp, b_pp, b_r1, b_r2, b_s1, b_s2)
    except Exception as e:
        print(f"Market Error {e}")
        return ("N/A",0,0,0,0,0,0), ("N/A",0,0,0,0,0,0)

def analyze_stock(symbol):
    try:
        df = yf.download(symbol+".NS", period="6mo", interval="1d", progress=False)
        if df.empty or len(df)<50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # STRATEGY 1: V12 BASE (VWAP + EMA + RSI + VOL)
        df['EMA20'] = df['Close'].ewm(20).mean(); df['EMA50'] = df['Close'].ewm(50).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3).rolling(20).mean()
        df['VolAvg'] = df['Volume'].rolling(20).mean()
        df['RSI14'] = 100 - (100/(1+ df['Close'].diff().clip(lower=0).rolling(14).mean() / (-df['Close'].diff().clip(upper=0).rolling(14).mean()).replace(0,0.001)))
        s1 = 0
        last = df.iloc[-1]
        if last['Close']>last['EMA20']: s1+=25
        if last['EMA20']>last['EMA50']: s1+=20
        if last['RSI14']>55: s1+=15
        if last['Volume']>last['VolAvg']: s1+=10
        if last['Close']>last['VWAP']: s1+=10
        
        # STRATEGY 2: HILEGA MILEGA (RSI9 + EMA3 + WMA21)
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).rolling(9).mean(); loss = -delta.where(delta<0,0).rolling(9).mean()
        rs = gain/loss.replace(0,0.001); df['RSI9'] = 100 - (100/(1+rs))
        df['EMA3_RSI'] = df['RSI9'].ewm(3).mean(); df['WMA21_RSI'] = wma(df['RSI9'],21)
        hm_bull = (last['RSI9']>50) and (df['EMA3_RSI'].iloc[-1] > df['WMA21_RSI'].iloc[-1])
        s2 = 25 if hm_bull else 0
        if hm_bull and df['RSI9'].iloc[-2]<=50: s2+=10
        
        # STRATEGY 3: AVWAP BREAKOUT + PRICE ACTION
        df['AVWAP'] = ((df['High']+df['Low']+df['Close'])/3).ewm(span=50).mean() # Simplified AVWAP
        df['SuperHigh'] = df['High'].rolling(10).max(); df['SuperLow'] = df['Low'].rolling(10).min()
        s3 = 0
        if last['Close'] > df['AVWAP'].iloc[-1]: s3+=15
        if last['Close'] > df['SuperHigh'].iloc[-2]: s3+=15 # Breakout
        if last['Close'] > last['Open'] and (last['Close']-last['Low']) > (last['High']-last['Close'])*0.5: s3+=10 # Bullish candle
        
        total = s1+s2+s3
        if total < 65: return None
        
        entry_low = round(last['Close']*0.998,2); entry_high = round(last['Close']*1.002,2)
        return {
            'Symbol':symbol, 'CMP':round(last['Close'],2), 'S1_V12':s1, 'S2_HM':s2, 'S3_AVWAP':s3, 'Total':total,
            'EntryRange': f"{entry_low}-{entry_high}", 'Entry':round(last['Close'],2),
            'T1':round(last['Close']*1.025,2), 'T2':round(last['Close']*1.05,2), 'SL':round(min(last['VWAP'], df['AVWAP'].iloc[-1])*0.98,2),
            'VWAP':round(last['VWAP'],2), 'AVWAP':round(df['AVWAP'].iloc[-1],2),
            'HM': "BUY ✅" if hm_bull else "NEUTRAL", 'Qty': int((CAPITAL*0.15)/last['Close'])
        }
    except Exception as e:
        return None

# --- MAIN ---
if __name__ == "__main__":
    nifty_data, bank_data = get_market_status()
    n_dir, n_cmp, n_pp, n_r1, n_r2, n_s1, n_s2 = nifty_data
    b_dir, b_cmp, b_pp, b_r1, b_r2, b_s1, b_s2 = bank_data
    
    try:
        df_list = pd.read_csv("nifty500_list.csv")
        symbols = df_list['Symbol'].tolist() if 'Symbol' in df_list.columns else df_list.iloc[:,0].tolist()
    except:
        symbols = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","ADANIGREEN","ADANIPORTS","AXISBANK","AUROPHARMA"]
    
    results = []
    for sym in symbols[:150]:
        r = analyze_stock(sym.strip())
        if r: results.append(r)
    
    results = sorted(results, key=lambda x: x['Total'], reverse=True)
    best3 = results[:3]
    
    # --- TELEGRAM MESSAGE ---
    msg = f"🚀 *MASTER BOT 500 V12.3 - ALL STRATEGY {datetime.now().strftime('%d-%m %I:%M %p')}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 *MARKET DIRECTION*\n"
    msg += f"NIFTY: {n_cmp:.0f} - {n_dir}\nBANK: {b_cmp:.0f} - {b_dir}\n\n"
    msg += f"📈 *NIFTY LEVELS*\nPP:{n_pp:.0f} | R1:{n_r1:.0f} R2:{n_r2:.0f}\nS1:{n_s1:.0f} S2:{n_s2:.0f}\n\n"
    msg += f"🏦 *BANK NIFTY LEVELS*\nPP:{b_pp:.0f} | R1:{b_r1:.0f} R2:{b_r2:.0f}\nS1:{b_s1:.0f} S2:{b_s2:.0f}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ Found: {len(results)} Stocks | Capital: Rs.{int(CAPITAL)}\n\n"
    
    if best3:
        msg += f"🏆 *BEST 3 - RANKING SYSTEM*\n"
        for i, r in enumerate(best3,1):
            msg += f"\n{i}. *{r['Symbol']}* ({r['Total']}/120) [V12:{r['S1_V12']} HM:{r['S2_HM']} AVWAP:{r['S3_AVWAP']}]\n"
            msg += f"   CMP:{r['CMP']} | HM:{r['HM']}\n"
            msg += f"   Entry Range: {r['EntryRange']}\n"
            msg += f"   T1:{r['T1']} | T2:{r['T2']} | SL:{r['SL']}\n"
            msg += f"   VWAP:{r['VWAP']} AVWAP:{r['AVWAP']} Qty:{r['Qty']}\n"
    else:
        msg += "⚠️ No stocks passed 65+ score today - NO TRADE DAY"
    
    msg += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    if len(results)>3:
        msg += f"📋 *Next 7 Stocks:*\n"
        for r in results[3:10]:
            msg += f"{r['Symbol']}:{r['Total']} | {r['EntryRange']} | SL:{r['SL']}\n"
    
    msg += f"\n_Strategy decides Best 3 by Total Score. Trade with SL._"
    
    print(msg)
    send_telegram(msg)
    if results:
        pd.DataFrame(results).to_csv("nifty500_results.csv", index=False)
