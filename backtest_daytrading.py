# NIFTY PIVOT BOSS V4.0 - INTRADAY BACKTEST
# Strategy: TOP 3 NIFTY500 @ 9:30 AM -> Exit 3:15 PM or SL/TGT
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# CONFIG - Same as your live bot
NIFTY500_LIST = ["BAJFINANCE.NS","ICICIBANK.NS","EICHERMOT.NS","RELIANCE.NS","TCS.NS"] # Add your 500 list here
CAPITAL_PER_STOCK = 100000
SL_PCT = 0.02  # 2% SL as per your bot
TGT1_PCT = 0.02
TGT2_PCT = 0.035

def calculate_score(df):
    # Same logic as your neural boss v2
    close = df['Close'].iloc[-1]
    ema9 = df['Close'].ewm(span=9).mean().iloc[-1]
    ema21 = df['Close'].ewm(span=21).mean().iloc[-1]
    # Simplified Score - Replace with your exact formula
    score = 0
    if close > ema9: score += 3
    if ema9 > ema21: score += 3
    if 60 < df['RSI'].iloc[-1] < 80: score += 2
    if df['Vol_Ratio'].iloc[-1] > 2: score += 1.5
    return score

# BACKTEST LOOP - Last 1 Year
start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')

print(f"Backtesting from {start} to {end}...")
trades = []

for symbol in NIFTY500_LIST:
    data = yf.download(symbol, start=start, end=end, interval='1d')
    # Add RSI, EMA, Volume logic here...
    # For each day, if Score >=7.5 -> Simulate Buy @ Open, Sell @ Close/SL/TGT
    # trades.append({date, symbol, pnl, win})

# RESULTS
df_trades = pd.DataFrame(trades)
win_rate = len(df_trades[df_trades['pnl']>0]) / len(df_trades) * 100
print(f"Total Trades: {len(df_trades)}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Avg PnL: {df_trades['pnl'].mean():.2f}%")
