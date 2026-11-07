import yfinance as yf
import pandas as pd
import numpy as np
import requests, os, json, datetime
from datetime import date

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or ""
CHAT_IDS = [x.strip() for x in CHAT_ID_RAW.split(",") if x.strip()]
MEMORY_FILE = "ai_memory.csv"

print(f"DEBUG: BOT_TOKEN exists? {bool(BOT_TOKEN)}")
print(f"DEBUG: CHAT_ID_RAW = '{CHAT_ID_RAW}' -> {CHAT_IDS}")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_IDS:
        print(f"ERROR: Token or Chat ID missing! Token={bool(BOT_TOKEN)} IDs={CHAT_IDS}")
        return
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": cid, "text": msg}, timeout=15)
            print(f"Telegram send to {cid}: Status {r.status_code} - {r.text[:200]}")
        except Exception as e:
            print(f"Telegram fail {cid}: {e}")

def get_market_regime():
    try:
        nifty = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
        nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
        nifty['ATR'] = (nifty['High'] - nifty['Low']).rolling(14).mean()
        last = nifty.iloc[-1]
        price = float(last['Close'].iloc[0] if hasattr(last['Close'], 'iloc') else last['Close'])
        ema = float(last['EMA20'].iloc[0] if hasattr(last['EMA20'], 'iloc') else last['EMA20'])
        atr = float(last['ATR'].iloc[0] if hasattr(last['ATR'], 'iloc') else last['ATR'])
        atr_pct = (atr / price) * 100
        if price > ema and atr_pct > 1.2:
            regime = "TRENDING_BULL"
            reason = f"Nifty {price:.0f} > 20EMA, ATR {atr_pct:.1f}% - Bull Momentum"
        elif price < ema and atr_pct > 1.2:
            regime = "TRENDING_BEAR"
            reason = f"Nifty {price:.0f} < 20EMA, ATR {atr_pct:.1f}% - Bear"
        elif atr_pct < 0.8:
            regime = "RANGE_LOW_VOL"
            reason = f"ATR {atr_pct:.1f}% low - Range Day"
        else:
            regime = "RANGE"
            reason = f"Choppy, ATR {atr_pct:.1f}%"
        swing_high = float(nifty['High'].tail(20).max().iloc[0])
        swing_low = float(nifty['Low'].tail(20).min().iloc[0])
        return regime, reason, swing_high, swing_low
    except Exception as e:
        print(f"Regime fail {e}")
        return "UNKNOWN", str(e), 25000, 24000

def get_option_flow():
    # NSE blocks GitHub IP, so we use fallback
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        sess = requests.Session()
        sess.get("https://www.nseindia.com", headers=headers, timeout=10)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        r = sess.get(url, headers=headers, timeout=10)
        j = r.json()
        data = j['records']['data']
        total_ce = sum([x['CE']['openInterest'] for x in data if 'CE' in x])
        total_pe = sum([x['PE']['openInterest'] for x in data if 'PE' in x])
        pcr = total_pe/total_ce if total_ce>0 else 1.0
        ce_oi = {x['strikePrice']: x['CE']['openInterest'] for x in data if 'CE' in x}
        pe_oi = {x['strikePrice']: x['PE']['openInterest'] for x in data if 'PE' in x}
        res = max(ce_oi, key=ce_oi.get) if ce_oi else 0
        sup = max(pe_oi, key=pe_oi.get) if pe_oi else 0
        msg = "Bullish" if pcr>1.2 else "Bearish" if pcr<0.8 else "Neutral"
        return pcr, sup, res, msg
    except Exception as e:
        print(f"Option flow fail: {e} - Using PCR=1.0 fallback")
        return 1.0, 0, 0, "NSE blocked (fallback)"

def main():
    regime, reason, sh, sl = get_market_regime()
    pcr, sup, res, flow = get_option_flow()
    should = "RANGE_LOW_VOL" not in regime
    txt = f"🤖 *AUGMENTED AI BRAIN*\nDate: {date.today()}\n\nRegime: {regime}\n{reason}\nSwing H: {sh:.0f} L: {sl:.0f}\n\nPCR: {pcr:.2f} - {flow}\nSupport: {sup} Resist: {res}\n\nDecision: {'✅ TRADE ALLOWED' if should else '🛑 NO TRADE'}"
    print(txt)
    send_telegram(txt)
    df = pd.DataFrame([{"date": str(date.today()), "regime": regime, "pcr": pcr, "trade_allowed": should}])
    if os.path.exists(MEMORY_FILE):
        df.to_csv(MEMORY_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(MEMORY_FILE, index=False)

if __name__ == "__main__":
    main()
