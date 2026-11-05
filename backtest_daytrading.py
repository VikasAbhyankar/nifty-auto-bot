# NIFTY PIVOT BOSS V4.0 - INTRADAY BACKTEST (Exact your logic)
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

SYMBOLS=["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","LTIM.NS","PIDILITIND.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"]

def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except: return pd.Series([50]*len(prices))

def score_stock(df):
    if len(df)<35: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    close=df['Close']; high=df['High']; low=df['Low']; vol=df['Volume']
    lc=float(close.iloc[-2]) # use prev day close to avoid lookahead - for backtest
    y_h=float(high.iloc[-2]); y_l=float(low.iloc[-2]); y_c=float(close.iloc[-2])
    ema9=float(close.ewm(span=9).mean().iloc[-2]); ema21=float(close.ewm(span=21).mean().iloc[-2]); ema50=float(close.ewm(span=50).mean().iloc[-2])
    rsi=float(calc_rsi(close).iloc[-2])
    avg_v=float(vol.tail(10).mean()); last_v=float(vol.iloc[-2]); volx=last_v/avg_v if avg_v>0 else 1
    pivot=(y_h+y_l+y_c)/3; bc=(y_h+y_l)/2; tc=pivot-bc+pivot
    ema_gap=((ema9-ema21)/ema21*100) if ema21!=0 else 0; tc_gap=((lc-tc)/tc*100) if tc!=0 else 0
    score=0; 
    score+=max(0,min(2.5,ema_gap*2)); score+=max(0,min(2.0,tc_gap*1.5))
    if 60<=rsi<=70: score+=2.5
    elif 55<=rsi<=75: score+=2.0
    elif 50<=rsi<=78: score+=1.2
    score+=min(2.0,volx*0.8)
    if lc>ema50: score+=1.0
    return {"price":lc,"score":score,"rsi":rsi,"volx":volx,"ema_gap":ema_gap,"tc_gap":tc_gap}

# BACKTEST
print("Downloading 300 days data for 54 stocks...")
data_cache={}
for sym in SYMBOLS:
    try:
        df=yf.download(sym, period="300d", interval="1d", progress=False, auto_adjust=False)
        data_cache[sym]=df
    except: pass

trades=[]
start_date = datetime.now() - timedelta(days=260)
# loop each trading day in last 247 days
for days_back in range(247, 1, -1):
    test_date = datetime.now() - timedelta(days=days_back)
    # get scores for that day (using data up to that day)
    day_results=[]
    for sym, df in data_cache.items():
        # filter df up to test_date
        df_cut = df[df.index <= test_date.strftime('%Y-%m-%d')]
        if len(df_cut)<35: continue
        s=score_stock(df_cut)
        if s: 
            s['symbol']=sym
            day_results.append(s)
    day_results=sorted(day_results,key=lambda x:x['score'],reverse=True)[:3]
    
    # Simulate next day PnL
    for stock in day_results:
        if stock['score'] < 7.5: continue
        sym=stock['symbol']
        df_full=data_cache[sym]
        try:
            # Next day candle
            next_idx = df_full.index.get_indexer([test_date], method='bfill')[0]+1
            if next_idx >= len(df_full): continue
            next_day=df_full.iloc[next_idx]
            open_p=float(next_day['Open']); high_p=float(next_day['High']); low_p=float(next_day['Low']); close_p=float(next_day['Close'])
            entry=open_p
            sl=entry*0.98; t1=entry*1.02; t2=entry*1.035
            
            # Check SL hit first then TGT (intraday logic)
            pnl=0; result="CLOSE"
            if low_p <= sl:
                pnl=-2.0; result="SL"
            elif high_p >= t2:
                pnl=3.5; result="TGT2"
            elif high_p >= t1:
                pnl=2.0; result="TGT1"
            else:
                pnl=((close_p-entry)/entry*100); result="CLOSE"
            
            trades.append({"date":test_date.strftime('%Y-%m-%d'),"symbol":sym.replace('.NS',''),"score":stock['score'],"pnl":pnl,"result":result})
        except: continue

# FINAL REPORT
df_trades=pd.DataFrame(trades)
if len(df_trades)>0:
    win_rate=len(df_trades[df_trades['pnl']>0])/len(df_trades)*100
    avg_pnl=df_trades['pnl'].mean()
    print(f"\n=== NIFTY BOSS V4.0 BACKTEST (247 Days) ===")
    print(f"Total Trades: {len(df_trades)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg PnL per trade: {avg_pnl:.2f}%")
    print(f"Total PnL (3 stocks/day, 1L each): {(df_trades['pnl'].sum()/100*100000):,.0f} Rs on 3L capital")
    print(f"\nBest 10 trades:\n{df_trades.sort_values('pnl',ascending=False).head(10)}")
    print(f"\nWorst 10 trades:\n{df_trades.sort_values('pnl').head(10)}")
    df_trades.to_csv("backtest_results.csv",index=False)
    print("\nSaved to backtest_results.csv")
else:
    print("No trades found - check data")
