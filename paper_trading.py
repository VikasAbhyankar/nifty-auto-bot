# paper_trading.py - GitHub Paper Trading Engine
# Works with NIFTY PIVOT BOSS V4.1 + V11 SNIPER format

import csv
import os
import yfinance as yf
from datetime import datetime
import pytz

# CONFIG - Change as per your capital
CAPITAL = 200000
RISK_PER_TRADE = 0.01  # 1% = Rs 2000
CSV_FILE = "paper_trades.csv"
IST = pytz.timezone('Asia/Kolkata')

def get_live_price(symbol):
    """Get live price from Yahoo - NSE symbols"""
    try:
        # Convert your symbol: HINDALCO -> HINDALCO.NS
        ticker = f"{symbol}.NS" if "-EQ" not in symbol else symbol.replace("-EQ",".NS")
        ticker = ticker.replace("HDFCBANK","HDFCBANK.NS").replace("NIFTY","^NSEI")
        data = yf.Ticker(ticker).history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1]), float(data['Low'].iloc[-1]), float(data['High'].iloc[-1])
    except:
        pass
    return None, None, None

def calculate_qty(entry, sl):
    risk_rs = CAPITAL * RISK_PER_TRADE
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0:
        return 1
    qty = int(risk_rs / risk_per_share)
    return max(1, qty)

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["date","time","symbol","entry","sl","tgt1","tgt2","qty","risk_rs","status","pnl","exit_price","score"])

def add_new_trade(symbol, entry, sl, tgt1, tgt2, score=""):
    init_csv()
    now = datetime.now(IST)
    qty = calculate_qty(entry, sl)
    risk_rs = qty * abs(entry - sl)
    
    # Don't add duplicate OPEN trade for same symbol same day
    with open(CSV_FILE, 'r') as f:
        rows = list(csv.reader(f))
        for r in rows[1:]:
            if len(r)>2 and r[2]==symbol and r[0]==now.strftime("%Y-%m-%d") and r[9]=="OPEN":
                print(f"Skipping duplicate OPEN {symbol}")
                return None
    
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M"),
            symbol,
            entry, sl, tgt1, tgt2,
            qty,
            round(risk_rs,2),
            "OPEN",
            0,
            "",
            score
        ])
    print(f"ADDED PAPER: {symbol} @ {entry} Qty {qty} Risk Rs {risk_rs}")
    return qty

def update_open_trades():
    """Check SL/TGT for all OPEN trades"""
    if not os.path.exists(CSV_FILE):
        return []
    
    init_csv()
    updated_rows = []
    closed_today = []
    
    with open(CSV_FILE, 'r') as f:
        rows = list(csv.reader(f))
    
    header = rows[0]
    for row in rows[1:]:
        if len(row) < 10:
            continue
        if row[9] != "OPEN":
            updated_rows.append(row)
            continue
            
        symbol = row[2]
        entry = float(row[3])
        sl = float(row[4])
        tgt1 = float(row[5]) if row[5] else entry*1.025
        qty = int(row[7])
        
        live, low, high = get_live_price(symbol)
        if live is None:
            updated_rows.append(row)
            continue
        
        # Check SL first
        if low <= sl:
            pnl = (sl - entry) * qty
            row[9] = "SL_HIT"
            row[10] = round(pnl,2)
            row[11] = sl
            closed_today.append(row)
        elif high >= tgt1:
            # TGT1 hit - Book 50%, trail rest
            # For paper, we book full at TGT1 for simplicity
            pnl = (tgt1 - entry) * qty
            row[9] = "TGT1_HIT"
            row[10] = round(pnl,2)
            row[11] = tgt1
            closed_today.append(row)
        
        updated_rows.append(row)
    
    # Rewrite CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(updated_rows)
    
    return closed_today

def generate_summary():
    """Daily P&L summary for Telegram"""
    if not os.path.exists(CSV_FILE):
        return "📝 PAPER: No trades yet"
    
    with open(CSV_FILE, 'r') as f:
        rows = list(csv.reader(f))[1:]
    
    today = datetime.now(IST).strftime("%Y-%m-%d")
    today_rows = [r for r in rows if r[0]==today]
    
    wins = len([r for r in today_rows if "TGT" in r[9]])
    losses = len([r for r in today_rows if "SL_HIT" in r[9]])
    open_trades = len([r for r in today_rows if r[9]=="OPEN"])
    
    total_pnl = sum([float(r[10]) for r in today_rows if r[10]])
    
    msg = f"📝 PAPER TRADING {today}\n"
    msg += f"Today: {wins}W {losses}L {open_trades} Open | Net P&L: Rs {round(total_pnl,2)}\n"
    
    if today_rows:
        msg += "\n".join([f"{r[2]} {r[9]} {r[10]}" for r in today_rows[-5:]])
    
    # Overall win rate
    all_closed = [r for r in rows if r[9]!="OPEN" and r[10]]
    if len(all_closed) >= 10:
        overall_wins = len([r for r in all_closed if float(r[10])>0])
        wr = overall_wins/len(all_closed)*100
        msg += f"\n\nOverall: {len(all_closed)} trades | Win Rate {round(wr,1)}%"
    
    return msg

# --- HOW TO USE WITH YOUR EXISTING BOT ---

# Example 1: When your V4.1 generates HINDALCO signal
# Call this function from your main scanner file:
# from paper_trading import add_new_trade
# add_new_trade("HINDALCO", 958, 934, 978, 992, "11.0/10")

# Example 2: At start of every 15 min run, update old trades
# closed = update_open_trades()
# summary = generate_summary()
# send_to_telegram(summary)

if __name__ == "__main__":
    # Test run - updates existing OPEN trades
    closed = update_open_trades()
    print(generate_summary())
    if closed:
        print(f"Closed today: {closed}")
