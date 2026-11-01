# Risk Manager with Govt Levies + Brokerage
import json, os, datetime

RISK_FILE = "intraday_risk.json"
BROKERAGE_PER_ORDER = 20
STT_RATE = 0.00025  # 0.025% on sell
EXCHANGE_RATE = 0.0000345
GST_RATE = 0.18
SEBI_RATE = 0.000001
STAMP_RATE = 0.00002

MAX_DAILY_LOSS = 2000
MAX_LOSS_PER_TRADE = 40  # points
MAX_TRADES_PER_DAY = 3
BREAKEVEN_POINTS = 18 # Approx for Nifty

def calc_charges(buy_price, sell_price, qty=50):
    turnover = (buy_price + sell_price) * qty
    brokerage = BROKERAGE_PER_ORDER * 2
    stt = sell_price * qty * STT_RATE
    exch = turnover * EXCHANGE_RATE
    sebi = turnover * SEBI_RATE
    stamp = buy_price * qty * STAMP_RATE
    gst = brokerage * GST_RATE
    total = brokerage + stt + exch + sebi + stamp + gst
    return round(total,2)

def load_risk():
    today = datetime.datetime.now().strftime("%d-%b-%Y")
    if os.path.exists(RISK_FILE):
        try:
            with open(RISK_FILE,'r') as f:
                data=json.load(f)
                if data.get("date") != today:
                    return {"date":today, "trades":0, "pnl":0, "loss":0, "blocked":False, "history":[]}
                return data
        except:
            pass
    return {"date":today, "trades":0, "pnl":0, "loss":0, "blocked":False, "history":[]}

def save_risk(data):
    with open(RISK_FILE,'w') as f:
        json.dump(data,f,indent=2)

def can_trade():
    r=load_risk()
    if r["blocked"]:
        return False, f"BLOCKED - Daily Loss ₹{r['loss']} >= {MAX_DAILY_LOSS}"
    if r["trades"] >= MAX_TRADES_PER_DAY:
        return False, f"MAX {MAX_TRADES_PER_DAY} trades done today"
    if r["loss"] >= MAX_DAILY_LOSS:
        r["blocked"]=True
        save_risk(r)
        return False, "Daily Max Loss Hit - Bot Stopped"
    return True, "OK"

def add_trade(pnl_points, buy_price, sell_price):
    r=load_risk()
    charges = calc_charges(buy_price, sell_price)
    pnl_rs = pnl_points * 50 - charges
    r["trades"]+=1
    r["pnl"]+=pnl_rs
    if pnl_rs < 0:
        r["loss"] += abs(pnl_rs)
    r["history"].append({"time":datetime.datetime.now().strftime("%H:%M"), "pnl_points":pnl_points, "pnl_rs":pnl_rs, "charges":charges})
    if r["loss"] >= MAX_DAILY_LOSS:
        r["blocked"]=True
    save_risk(r)
    return r, pnl_rs, charges
