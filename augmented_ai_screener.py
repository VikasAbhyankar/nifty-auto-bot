import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""

SYMBOLS = ["TANLA","WELSPUNLIV","COFORGE","ZYDUSLIFE","PERSISTENT","HAL","SUNPHARMA","TATASTEEL","ONGC"] # Put your full 500 list

def safe_float(x):
    try:
        if isinstance(x, pd.Series):
            return float(x.iloc[0])
        return float(x)
    except:
        return 0.0

def get_avwap(df):
    try:
        low_idx = int(df['Low'].rolling(60).apply(lambda x: x.argmin()).iloc[-1])
        start = max(0, len(df)-60+low_idx)
        sub = df.iloc[start:]
        avwap = (sub['Close']*sub['Volume']).sum() / sub['Volume'].sum()
        date = sub.index[start].strftime("%Y-%m-%d")
        above = safe_float(df['Close'].iloc[-1]) > avwap
        return safe_float(avwap), date, above
    except:
        return safe_float(df['Close'].iloc[-1]), "2024-08-01", True

def get_wtf(symbol):
    try:
        dfw = yf.download(symbol+".NS", period="1y", interval="1wk", progress=False, auto_adjust=False)
        if len(dfw)<50:
            return "BULL", 0,0,0
        ema8 = safe_float(dfw['Close'].ewm(span=8).mean().iloc[-1])
        ema20 = safe_float(dfw['Close'].ewm(span=20).mean().iloc[-1])
        ema50 = safe_float(dfw['Close'].ewm(span=50).mean().iloc[-1])
        bull = ema8>ema20 and ema20>ema50
        return "BULL" if bull else "BEAR", ema8, ema20, ema50
    except:
        return "BULL", 0,0,0

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta>0,0).rolling(window=period).mean()
    loss = -delta.where(delta<0,0).rolling(window=period).mean()
    rs = gain/loss
    return 100 - (100/(1+rs))

def analyze(symbol):
    try:
        df = yf.download(symbol+".NS", period="1y", progress=False, auto_adjust=False)
        if len(df)<200:
            return None
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        df['RSI14'] = calc_rsi(df['Close'],14)
        df['RSI9'] = calc_rsi(df['Close'],9)
        df['VolAvg'] = df['Volume'].rolling(20).mean()

        cmp = safe_float(df['Close'].iloc[-1])
        ema8 = safe_float(df['EMA8'].iloc[-1])
        ema20 = safe_float(df['EMA20'].iloc[-1])
        ema50 = safe_float(df['EMA50'].iloc[-1])
        ema200 = safe_float(df['EMA200'].iloc[-1])
        rsi14 = safe_float(df['RSI14'].iloc[-1])
        rsi9 = safe_float(df['RSI9'].iloc[-1])
        vol = safe_float(df['Volume'].iloc[-1])
        vol_avg = safe_float(df['VolAvg'].iloc[-1])
        vol_ratio = vol/vol_avg if vol_avg>0 else 1.0

        trend = cmp>ema8 and ema8>ema20 and ema20>ema50
        hm = cmp>ema200
        rsi_ok = rsi14>60
        avwap, avwap_date, avwap_above = get_avwap(df)
        wtf, w8, w20, w50 = get_wtf(symbol)
        wtf_bull = wtf=="BULL"

        true_bala = avwap_above and wtf_bull and trend and rsi_ok and vol_ratio>1.2
        htf_cluster = wtf_bull and trend and avwap_above

        score = 0
        if trend: score+=25
        if hm: score+=20
        if rsi_ok: score+=15
        if vol_ratio>1.0: score+=10
        if true_bala: score+=40
        if htf_cluster: score+=20

        win = min(85, 50 + score*0.2 + vol_ratio*5)
        prob = min(95, 60 + (15 if trend else 0) + (10 if 55<rsi14<75 else 0))

        return {
            "symbol": symbol, "cmp": cmp, "rsi14": rsi14, "rsi9": rsi9,
            "vol_ratio": vol_ratio, "ema8": ema8, "ema20": ema20, "ema50": ema50, "ema200": ema200,
            "avwap": avwap, "avwap_date": avwap_date, "avwap_above": avwap_above,
            "wtf": wtf, "w8": w8, "w20": w20, "w50": w50,
            "true_bala": true_bala, "htf_cluster": htf_cluster,
            "score": score, "win": win, "prob": prob,
            "sl": ema50*0.95
        }
    except Exception as e:
        print(f"{symbol} error {e}")
        return None

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"ERROR: BOT_TOKEN missing={not BOT_TOKEN} CHAT_ID missing={not CHAT_ID}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 3500):
        chunk = msg[i:i+3500]
        try:
            r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=20)
            print(f"Telegram chunk {i//3500+1} status {r.status_code}")
        except Exception as e:
            print(f"Telegram failed: {e}")

def main():
    results = []
    for sym in SYMBOLS:
        res = analyze(sym)
        if res:
            results.append(res)
    for r in results:
        r['final_rank'] = r['score']*0.4 + r['win']*0.25 + r['prob']*0.25 + (15 if r['true_bala'] else 0) + (10 if r['htf_cluster'] else 0)
    results = sorted(results, key=lambda x: x['final_rank'], reverse=True)
    now = datetime.now().strftime("%d-%m %I:%M %p")
    msg = f"🚀 MASTER V18 TRUE BALA - {now}\n"
    msg += f"Scan: {len(results)} | True Bala: {sum(1 for x in results if x['true_bala'])} | HTF: {sum(1 for x in results if x['htf_cluster'])}\n\n"
    msg += f"🏆 BEST 3 - SYSTEM AUTO\n\n"
    for i, r in enumerate(results[:3]):
        msg += f"{i+1}. {r['symbol']} Rank:{r['final_rank']:.1f} Prob:{r['prob']:.0f}% {'TRUE BALA' if r['true_bala'] else ''} {'HTF' if r['htf_cluster'] else ''}\n"
        msg += f"Score:{r['score']} Win:{r['win']:.0f}% Vol:{r['vol_ratio']:.2f}x\n"
        msg += f"CMP:{r['cmp']:.2f} RSI:{r['rsi14']:.1f}/{r['rsi9']:.1f} WTF:{r['wtf']}\n"
        msg += f"8E:{r['ema8']:.2f} 20E:{r['ema20']:.2f} 50E:{r['ema50']:.2f}\n"
        msg += f"AVWAP:{r['avwap']:.2f} ({r['avwap_date']}) Above:{r['avwap_above']} W:8E:{r['w8']:.2f} 20E:{r['w20']:.2f}\n"
        msg += f"SL:{r['sl']:.2f} T1:{r['cmp']*1.05:.0f} T2:{r['cmp']*1.10:.0f}\n\n"
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
