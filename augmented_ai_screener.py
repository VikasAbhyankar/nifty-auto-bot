# MASTER BOT 500 V12.3 + HILEGA MILEGA - FULL FIXED CODE
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# --- ENV VARS - Supports both names ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
CAPITAL = float(os.getenv("CAPITAL", "100000"))

print(f"Bot Token found: {'Yes' if BOT_TOKEN else 'No'}")
print(f"Chat ID found: {'Yes' if CHAT_ID else 'No'}")

def wma(series, period):
    weights = np.arange(1, period+1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)

def calculate_v12_base(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['RSI14'] = 100 - (100 / (1 + df['Close'].diff().clip(lower=0).rolling(14).mean() / (-df['Close'].diff().clip(upper=0).rolling(14).mean())))
    # VWAP approx = (H+L+C)/3 rolling 20
    df['VWAP'] = ((df['High'] + df['Low'] + df['Close'])/3).rolling(20).mean()
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    df['Base_Score'] = 0
    df.loc[df['Close'] > df['EMA20'], 'Base_Score'] += 20
    df.loc[df['EMA20'] > df['EMA50'], 'Base_Score'] += 20
    df.loc[df['RSI14'] > 55, 'Base_Score'] += 20
    df.loc[df['Volume'] > df['Vol_Avg'], 'Base_Score'] += 10
    df.loc[df['Close'] > df['VWAP'], 'Base_Score'] += 10
    return df

def calculate_hilega_milega(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(9).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(9).mean()
    rs = gain / loss
    df['RSI9'] = 100 - (100 / (1 + rs))
    df['EMA3_RSI'] = df['RSI9'].ewm(span=3).mean()
    df['WMA21_RSI'] = wma(df['RSI9'], 21)
    df['HM_Bullish'] = (df['RSI9'] > 50) & (df['EMA3_RSI'] > df['WMA21_RSI'])
    df['HM_Score'] = 0
    df.loc[df['HM_Bullish'], 'HM_Score'] += 15
    df.loc[(df['HM_Bullish']) & (df['RSI9'].shift(1) <= 50), 'HM_Score'] += 10
    df['HM_Signal'] = np.where(df['HM_Bullish'], 'BUY ✅', 'NEUTRAL')
    return df

def scan_stock(symbol):
    try:
        df = yf.download(symbol+".NS", period="3mo", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if len(df) < 30: return None
        df = calculate_v12_base(df)
        df = calculate_hilega_milega(df)
        last = df.iloc[-1]
        total = last['Base_Score'] + max(0, last['HM_Score'])
        if total >= 70 and last['HM_Bullish']:
            return {
                'Symbol': symbol, 'CMP': round(last['Close'],2),
                'Base': int(last['Base_Score']), 'HM_Score': int(last['HM_Score']),
                'Total': int(total), 'HM_Signal': last['HM_Signal'],
                'RSI9': round(last['RSI9'],1), 'Entry': round(last['Close'],2),
                'T1': round(last['Close']*1.02,2), 'T2': round(last['Close']*1.04,2),
                'SL': round(last['VWAP']*0.99,2), 'AVWAP': round(last['VWAP'],2)
            }
        return None
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: Telegram secrets missing!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram Response: {r.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- MAIN ---
if __name__ == "__main__":
    try:
        # Load list
        try:
            nifty = pd.read_csv("nifty500_list.csv")
            symbols = nifty['Symbol'].tolist() if 'Symbol' in nifty.columns else nifty.iloc[:,0].tolist()
        except:
            symbols = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","MARUTI"]
        
        print(f"Scanning {len(symbols)} stocks...")
        results = []
        for sym in symbols[:100]:  # Scan first 100 for speed, change to all later
            res = scan_stock(sym.strip())
            if res: results.append(res)
        
        print(f"Found {len(results)} stocks")
        
        if results:
            df_res = pd.DataFrame(results).sort_values("Total", ascending=False)
            df_res.to_csv("nifty500_results.csv", index=False)
            msg = f"🚀 *MASTER BOT V12.3 + HM - {datetime.now().strftime('%d-%m-%Y %I:%M %p')}*\n\n"
            msg += f"Found: {len(results)} Stocks\nCapital: Rs.{int(CAPITAL)}\n\n"
            for i, r in enumerate(results[:10],1):
                msg += f"{i}. *{r['Symbol']}* - {r['CMP']} | Total:{r['Total']} (Base:{r['Base']}+HM:{r['HM_Score']})\n"
                msg += f"   Entry:{r['Entry']} T1:{r['T1']} T2:{r['T2']} SL:{r['SL']}\n\n"
            msg += "Trade with SL. Not financial advice."
        else:
            msg = f"⚠️ *MASTER BOT V12.3 + HM - {datetime.now().strftime('%d-%m-%Y')}*\n\nNo stocks passed 70+HM Bullish filter today.\nMarket weak / No fresh BUY.\n\nChecked {len(symbols[:100])} stocks."
        
        print(msg)
        send_telegram(msg)
        
    except Exception as e:
        print(f"Main Error: {e}")
        send_telegram(f"❌ Bot Error: {e}")
