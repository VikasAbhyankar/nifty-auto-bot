"""
MASTER BOT V12.3 ULTRA + HILEGA-MILEGA
V12.2 + RSI9 + EMA3 + WMA21 + 50 Filter
"""

import yfinance as yf
import pandas as pd
import numpy as np

def wma(series, period):
    weights = np.arange(1, period+1)
    return series.rolling(period).apply(
        lambda x: np.dot(x, weights)/weights.sum(), raw=True)

def calculate_hilega_milega(df):
    # RSI 9
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(9).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(9).mean()
    rs = gain / loss
    rsi9 = 100 - (100 / (1 + rs))
    df['RSI9'] = rsi9
    
    # EMA 3 on RSI9
    df['EMA3_RSI'] = df['RSI9'].ewm(span=3, adjust=False).mean()
    # WMA 21 on RSI9
    df['WMA21_RSI'] = wma(df['RSI9'], 21)
    
    # Signals
    df['HM_Bullish'] = (df['RSI9'] > 50) & (df['EMA3_RSI'] > df['WMA21_RSI'])
    df['HM_Bearish'] = (df['RSI9'] < 50) & (df['EMA3_RSI'] < df['WMA21_RSI'])
    df['HM_Fresh_Buy'] = df['HM_Bullish'] & (df['RSI9'].shift(1) <= 50)
    
    # Score 0-25
    df['HM_Score'] = 0
    df.loc[df['HM_Bullish'], 'HM_Score'] += 15
    df.loc[df['HM_Fresh_Buy'], 'HM_Score'] += 10
    df.loc[df['HM_Bearish'], 'HM_Score'] -= 15
    
    df['HM_Signal'] = 'NEUTRAL'
    df.loc[df['HM_Fresh_Buy'], 'HM_Signal'] = 'FRESH BUY 🔥'
    df.loc[df['HM_Bullish'] & ~df['HM_Fresh_Buy'], 'HM_Signal'] = 'BUY ✅'
    df.loc[df['HM_Bearish'], 'HM_Signal'] = 'SELL ❌'
    return df

def calculate_v12_base(df):
    df['VWAP'] = (df['Close']*df['Volume']).rolling(20).sum()/df['Volume'].rolling(20).sum()
    df['PP'] = (df['High']+df['Low']+df['Close'])/3
    delta = df['Close'].diff()
    gain = (delta.where(delta>0,0)).rolling(14).mean()
    loss = (-delta.where(delta<0,0)).rolling(14).mean()
    df['RSI14'] = 100-(100/(1+gain/loss))
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    df['Vol_Ratio'] = df['Volume']/df['Vol_Avg']
    
    df['Base_Score']=0
    df.loc[df['Close']>df['VWAP'],'Base_Score']+=25
    df.loc[df['Close']>df['PP'],'Base_Score']+=20
    df.loc[(df['RSI14']>55)&(df['RSI14']<75),'Base_Score']+=25
    df.loc[df['Vol_Ratio']>1.2,'Base_Score']+=15
    df.loc[df['Close']>df['Close'].rolling(20).mean(),'Base_Score']+=15
    return df

def screen_stock(symbol):
    try:
        df = yf.download(symbol+".NS", period="3mo", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if len(df)<30: return None
        df = calculate_v12_base(df)
        df = calculate_hilega_milega(df)
        last = df.iloc[-1]
        total = last['Base_Score'] + max(0,last['HM_Score'])
        if total>=70 and last['HM_Bullish']:
            return {
                'Symbol':symbol,'CMP':round(last['Close'],2),
                'Base':int(last['Base_Score']),'HM_Score':int(last['HM_Score']),
                'Total':int(total),'HM_Signal':last['HM_Signal'],
                'RSI9':round(last['RSI9'],1),'Entry':round(last['Close'],2),
                'T1':round(last['Close']*1.02,2),'T2':round(last['Close']*1.04,2),
                'SL':round(last['VWAP']*0.99,2),'AVWAP':round(last['VWAP'],2)
            }
    except: return None
