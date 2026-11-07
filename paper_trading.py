import os
import csv
import yfinance as yf
from datetime import datetime

CSV_FILE = "paper_trades.csv"
HEADER = ["Date","Symbol","Buy","SL","TGT","Qty","Status","ExitPrice","Pnl"]

def ensure_file():
    # Create file with header if not exists or empty
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) < 5:
        with open(CSV_FILE, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
        print("Created paper_trades.csv with header")

def add_paper_trade(symbol, buy, sl, tgt, qty=100):
    ensure_file()
    # Check duplicate - don't add same symbol if already OPEN today
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Symbol"] == symbol and row["Date"] == today and row["Status"] == "OPEN":
                    print(f"Skip duplicate: {symbol} already OPEN today")
                    return False
    except:
        pass

    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([today, symbol, round(buy,2), round(sl,2), round(tgt,2), qty, "OPEN", "", ""])
    print(f"✅ Paper Trade Added: {symbol} @ {buy} | SL {sl} | TGT {tgt}")
    return True

def update_paper_trades():
    """Check all OPEN trades - if LTP hits SL or TGT, close it"""
    ensure_file()
    if not os.path.exists(CSV_FILE):
        return
    
    rows = []
    updated = 0
    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return

    new_rows = []
    for row in rows:
        if row["Status"] != "OPEN":
            new_rows.append(row)
            continue
        
        symbol = row["Symbol"]
        try:
            buy = float(row["Buy"])
            sl = float(row["SL"])
            tgt = float(row["TGT"])
            qty = int(row["Qty"])
            # Get LTP
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period="1d")
            if hist.empty:
                new_rows.append(row)
                continue
            ltp = float(hist["Close"].iloc[-1])
            
            exit_price = 0
            status = "OPEN"
            pnl = 0
            
            # Check TGT first (for long trades)
            if ltp >= tgt:
                status = "TGT HIT"
                exit_price = tgt
                pnl = (tgt - buy) * qty
            elif ltp <= sl:
                status = "SL HIT"
                exit_price = sl
                pnl = (sl - buy) * qty
            
            if status != "OPEN":
                row["Status"] = status
                row["ExitPrice"] = round(exit_price,2)
                row["Pnl"] = round(pnl,2)
                print(f"🔔 CLOSED: {symbol} - {status} | P&L {pnl}")
                updated += 1
            
            new_rows.append(row)
            
        except Exception as e:
            print(f"Error updating {symbol}: {e}")
            new_rows.append(row)
    
    # Write back
    if updated > 0:
        with open(CSV_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER)
            w.writeheader()
            w.writerows(new_rows)
        print(f"Updated {updated} trades")

def get_summary():
    ensure_file()
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            total = 0
            open_c = 0
            pnl = 0
            for r in reader:
                total += 1
                if r["Status"] == "OPEN":
                    open_c += 1
                else:
                    try:
                        pnl += float(r["Pnl"])
                    except:
                        pass
            return f"Total:{total} Open:{open_c} P&L:₹{pnl:.0f}"
    except:
        return "No trades yet"

# Run update when called directly
if __name__ == "__main__":
    update_paper_trades()
    print(get_summary())
