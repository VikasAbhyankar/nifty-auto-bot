import os, csv, json, yfinance as yf
from datetime import datetime

CSV_FILE = "paper_trades.csv"

def add_paper_trade(symbol, buy, sl, tgt, qty):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["Date","Symbol","Buy","SL","TGT","Qty","Status","ExitPrice","Pnl"])
        w.writerow([datetime.now().strftime("%Y-%m-%d"), symbol, buy, sl, tgt, qty, "OPEN", "", ""])
    print(f"Paper Trade Added: {symbol} @ {buy}")

def update_open_trades():
    if not os.path.exists(CSV_FILE):
        return
    rows = []
    with open(CSV_FILE, "r") as f:
        r = csv.DictReader(f)
        rows = list(r)
    updated = False
    for row in rows:
        if row["Status"] == "OPEN":
            try:
                sym = row["Symbol"] + ".NS" if ".NS" not in row["Symbol"] else row["Symbol"]
                df = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=False)
                if len(df) == 0: continue
                low = float(df["Low"].iloc[-1])
                high = float(df["High"].iloc[-1])
                buy = float(row["Buy"])
                sl = float(row["SL"])
                tgt = float(row["TGT"])
                if low <= sl:
                    row["Status"] = "SL HIT"
                    row["ExitPrice"] = sl
                    row["Pnl"] = (sl - buy) * float(row["Qty"])
                    updated = True
                elif high >= tgt:
                    row["Status"] = "TGT HIT"
                    row["ExitPrice"] = tgt
                    row["Pnl"] = (tgt - buy) * float(row["Qty"])
                    updated = True
            except: continue
    if updated:
        with open(CSV_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Date","Symbol","Buy","SL","TGT","Qty","Status","ExitPrice","Pnl"])
            w.writeheader()
            w.writerows(rows)

def generate_summary():
    if not os.path.exists(CSV_FILE):
        return "Paper Trading: No trades yet"
    try:
        with open(CSV_FILE, "r") as f:
            r = list(csv.DictReader(f))
        total = len(r)
        open_t = len([x for x in r if x["Status"]=="OPEN"])
        win = len([x for x in r if x["Status"]=="TGT HIT"])
        loss = len([x for x in r if x["Status"]=="SL HIT"])
        pnl = sum([float(x["Pnl"]) for x in r if x["Pnl"]!=""])
        return f"📊 PAPER TRADING SUMMARY\nTotal: {total} | Open: {open_t} | TGT: {win} | SL: {loss}\nTotal P&L: ₹{pnl:.0f}"
    except Exception as e:
        return f"Paper Summary Error {e}"

# Alias for old name
def add_new_trade(symbol, buy, sl, tgt, qty):
    return add_paper_trade(symbol, buy, sl, tgt, qty)
