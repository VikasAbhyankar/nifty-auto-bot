# Nifty + BankNifty + Top3 + Self-Learning V4.2 - FIXED for new paper_trading
import os, json, requests, yfinance as yf
import pandas as pd
from datetime import datetime

# This works with BOTH old and new paper_trading.py
try:
    from paper_trading import add_paper_trade, update_open_trades, generate_summary
except ImportError:
    from paper_trading import add_paper_trade, update_paper_trades as update_open_trades, get_summary as generate_summary

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(msg); return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=20)
        print(f"Telegram {r.status_code}")
        if r.status_code != 200:
            print(r.text)
    except Exception as e:
        print(f"Telegram error {e}")

def calc_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except: return 50.0

def get_cpr_and_trend(symbol="^NSEI"):
    try:
        df = yf.download(symbol, period="50d", interval="1d", progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if len(df) < 30: return None
        close, high, low = df['Close'], df['High'], df['Low']
        lc = float(close.iloc[-1]); y_h=float(high.iloc[-2]); y_l=float(low.iloc[-2]); y_c=float(close.iloc[-2])
        prev_c = float(close.iloc[-2]); live = lc
        pivot=(y_h+y_l+y_c)/3; bc=(y_h+y_l)/2; tc=pivot-bc+pivot
        r1=2*pivot-y_l; r2=pivot+(y_h-y_l); r3=y_h+2*(pivot-y_l)
        s1=2*pivot-y_h; s2=pivot-(y_h-y_l); s3=y_l-2*(y_h-pivot)
        ema9=float(close.ewm(span=9).mean().iloc[-1]); ema21=float(close.ewm(span=21).mean().iloc[-1]); ema50=float(close.ewm(span=50).mean().iloc[-1])
        rsi=calc_rsi(close)
        points_diff = lc - prev_c
        bull_points=0; bear_points=0; reasons=[]
        if points_diff > 50: bull_points+=2; reasons.append(f"Gap +{points_diff:.0f} Bull")
        elif points_diff < -50: bear_points+=2; reasons.append(f"Gap {points_diff:.0f} Bear")
        if lc > tc: bull_points+=2; reasons.append(f"Above TC {tc:.0f}")
        elif lc < bc: bear_points+=2; reasons.append(f"Below BC {bc:.0f}")
        if lc > y_h: bull_points+=2; reasons.append(f"Breaks YH {y_h:.0f}")
        elif lc < y_l: bear_points+=2; reasons.append(f"Breaks YL {y_l:.0f}")
        if ema9 > ema21 and lc > ema21: bull_points+=2; reasons.append("EMA9>21")
        elif ema9 < ema21 and lc < ema21: bear_points+=2; reasons.append("EMA9<21")
        if rsi > 55: bull_points+=1; reasons.append(f"RSI {rsi:.0f}")
        elif rsi < 45: bear_points+=1; reasons.append(f"RSI {rsi:.0f}")
        if bull_points >= 4 and bull_points > bear_points: signal = f"BULLISH 🟢 ({bull_points} vs {bear_points})"
        elif bear_points >= 4 and bear_points > bull_points: signal = f"BEARISH 🔴 ({bear_points} vs {bull_points})"
        else: signal = f"SIDEWAYS 🟡 ({bull_points} vs {bear_points})"
        return {"symbol": symbol, "live": lc, "prev_c": prev_c, "diff": points_diff,"y_h": y_h, "y_l": y_l, "y_c": y_c, "pivot": pivot, "bc": bc, "tc": tc,"r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3,"ema9": ema9, "ema21": ema21, "ema50": ema50, "rsi": rsi,"signal": signal, "bull": bull_points, "bear": bear_points, "reasons": reasons}
    except Exception as e:
        print(f"CPR Error {symbol} {e}"); return None

def get_top3(nifty_signal=""):
    if "BEARISH" in nifty_signal:
        print(f"Nifty Bearish - No trades today: {nifty_signal}")
        return [], 0
    symbols=["RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","BHARTIARTL.NS","ITC.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","BAJFINANCE.NS","MARUTI.NS","SUNPHARMA.NS","KOTAKBANK.NS","HCLTECH.NS","M&M.NS","NTPC.NS","AXISBANK.NS","ULTRACEMCO.NS","TITAN.NS","ASIANPAINT.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","WIPRO.NS","POWERGRID.NS","COALINDIA.NS","HINDALCO.NS","JSWSTEEL.NS","TATASTEEL.NS","ONGC.NS","GRASIM.NS","CIPLA.NS","BPCL.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","DRREDDY.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","BRITANNIA.NS","APOLLOHOSP.NS","DIVISLAB.NS","INDUSINDBK.NS","VEDL.NS","LTIM.NS","PIDILITIND.NS","TRENT.NS","HAL.NS","BEL.NS","RECLTD.NS","PFC.NS","TATAPOWER.NS"]
    results=[]
    for sym in symbols:
        try:
            df=yf.download(sym,period="60d",interval="1d",progress=False,auto_adjust=False)
            if df is None or len(df)<35: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            close=df['Close']; high=df['High']; low=df['Low']; vol=df['Volume']
            lc=float(close.iloc[-1]); y_h=float(high.iloc[-2]); y_l=float(low.iloc[-2]); y_c=float(close.iloc[-2])
            ema9=float(close.ewm(span=9).mean().iloc[-1]); ema21=float(close.ewm(span=21).mean().iloc[-1]); ema50=float(close.ewm(span=50).mean().iloc[-1])
            rsi=calc_rsi(close); avg_v=float(vol.tail(10).mean()); last_v=float(vol.iloc[-1]); volx=last_v/avg_v if avg_v>0 else 1
            pivot=(y_h+y_l+y_c)/3; bc=(y_h+y_l)/2; tc=pivot-bc+pivot
            if lc < bc: continue
            if ema9 < ema21: continue
            ema_gap=((ema9-ema21)/ema21*100) if ema21!=0 else 0; tc_gap=((lc-tc)/tc*100) if tc!=0 else 0
            score=0
            if ema9 > ema21 and lc > ema21: score+=3.0
            elif ema9 > ema21: score+=1.5
            if lc > tc: score+=2.5
            elif lc < bc: score-=2.0
            if 60<=rsi<=70: score+=2.5
            elif 55<=rsi<=75: score+=2.0
            elif 50<=rsi<=78: score+=1.2
            else: continue
            score+=min(2.0,volx*0.8)
            if lc>ema50: score+=1.0
            if score < 7.5: continue
            results.append({"symbol":sym.replace(".NS",""),"price":lc,"score":round(score,2),"rsi":round(rsi,1),"volx":round(volx,1),"ema_gap":round(ema_gap,2),"tc_gap":round(tc_gap,2)})
        except: continue
    results=sorted(results,key=lambda x:x['score'],reverse=True)
    return results[:3], len(results)

def main():
    print("V4.2 FIXED Starting...")
    nifty=get_cpr_and_trend("^NSEI")
    bank=get_cpr_and_trend("^NSEBANK")
    
    if not nifty:
        print("Nifty data failed, retry...")
        send_telegram("⚠️ Nifty data download failed today - yfinance issue")
        return

    top3, qualified = get_top3(nifty['signal'] if nifty else "")

    update_open_trades()
    for s in top3:
        price = s['price']
        sl = round(price * 0.975, 2)
        tgt = round(price * 1.035, 2)
        risk = price - sl
        qty = max(1, int(33333 / risk)) if risk > 0 else 10
        add_paper_trade(s['symbol'], price, sl, tgt, qty)
    
    paper_summary = generate_summary()

    try:
        with open("nifty_memory.json","r") as f: mem=json.load(f)
        days=mem.get("days",247)
    except: days=247

    bank_text = f"Live: {bank['live']:.0f} Diff: {bank['diff']:+.0f} Signal: {bank['signal']}" if bank else "BankNifty data unavailable"
    bank_cpr = f"CPR: TC {bank['tc']:.0f} P {bank['pivot']:.0f} BC {bank['bc']:.0f}" if bank else ""

    msg=f"""NIFTY PIVOT BOSS V4.2 FIXED 🧠
Date: {datetime.now().strftime('%d-%b %Y %I:%M %p')}
Memory: {days} days

--- NIFTY50 ---
Live: {nifty['live']:.0f} Prev: {nifty['prev_c']:.0f} Diff: {nifty['diff']:+.0f}
Signal: {nifty['signal']}
Reason: {', '.join(nifty['reasons'])}
CPR: TC {nifty['tc']:.0f} P {nifty['pivot']:.0f} BC {nifty['bc']:.0f}
R: R3 {nifty['r3']:.0f} R2 {nifty['r2']:.0f} R1 {nifty['r1']:.0f}
S: S1 {nifty['s1']:.0f} S2 {nifty['s2']:.0f} S3 {nifty['s3']:.0f}
EMA9 {nifty['ema9']:.0f} EMA21 {nifty['ema21']:.0f} RSI {nifty['rsi']:.0f}

--- BANKNIFTY ---
{bank_text}
{bank_cpr}

--- TOP 3 DAY TRADES (CPR Filtered) ---
Scanned 54 | Qualified {qualified}
"""
    for i,s in enumerate(top3,1):
        sl=s['price']*0.975; t1=s['price']*1.02; t2=s['price']*1.035
        msg+=f"{i}. {s['symbol']} @ {s['price']:.0f} SCORE {s['score']}/10 BUY\n SL {sl:.0f} TGT {t1:.0f}/{t2:.0f} | EMA+{s['ema_gap']}% TC+{s['tc_gap']}% RSI {s['rsi']} Vol {s['volx']}x\n\n"

    if not top3:
        msg+="No Trade Today - Nifty Bearish or No stock Above BC with Score 7.5+ - Capital Protected! 🛡️\n\n"

    msg+=f"\n{paper_summary}"
    print(msg)
    send_telegram(msg)
    
    # Save results CSV for nifty500 workflow
    try:
        df_out = pd.DataFrame(top3)
        df_out.to_csv("nifty500_results.csv", index=False)
    except:
        pass

    with open("nifty_memory.json","w") as f:
        json.dump({"days":days+1,"last_nifty":nifty['signal'],"last_bank":bank['signal'] if bank else "NA","top3":top3,"last_run":str(datetime.now())},f,indent=2)

if __name__=="__main__":
    main()
