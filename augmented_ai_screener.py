import yfinance as yf
import pandas as pd
import numpy as np
import requests, os, json, datetime
from datetime import date

# ========= CONFIG =========
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_ID", "").split(",")
NIFTY_SYMBOL = "^NSEI"
MEMORY_FILE = "ai_memory.csv"
PAPER_FILE = "paper_trades.csv"

def send_telegram(msg):
    if not BOT_TOKEN: return
    for cid in CHAT_IDS:
        cid = cid.strip()
        if not cid: continue
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            print(f"Telegram fail {cid}: {e}")

# ========= AI-1: MARKET REGIME DETECTOR =========
def get_market_regime():
    try:
        nifty = yf.download(NIFTY_SYMBOL, period="3mo", interval="1d", progress=False)
        if len(nifty) < 30: return "UNKNOWN", "Not enough data"
        nifty['EMA20'] = nifty['Close'].ewm(span=20).mean()
        nifty['ATR'] = (nifty['High'] - nifty['Low']).rolling(14).mean()
        
        last = nifty.iloc[-1]
        prev = nifty.iloc[-2]
        price = float(last['Close'])
        ema = float(last['EMA20'])
        atr = float(last['ATR'])
        atr_pct = (atr / price) * 100

        # Regime Logic
        if price > ema and atr_pct > 1.2:
            regime = "TRENDING_BULL"
            reason = f"Nifty {price:.0f} > 20EMA, ATR {atr_pct:.1f}% - Bull Momentum"
        elif price < ema and atr_pct > 1.2:
            regime = "TRENDING_BEAR"
            reason = f"Nifty {price:.0f} < 20EMA, ATR {atr_pct:.1f}% - Bear Momentum"
        elif atr_pct < 0.8:
            regime = "RANGE_LOW_VOL"
            reason = f"ATR {atr_pct:.1f}% low - Range Day, AVOID trading"
        else:
            regime = "RANGE_HIGH_VOL"
            reason = f"Choppy day, ATR {atr_pct:.1f}%"
        
        # Swing High/Low
        swing_high = float(nifty['High'].tail(20).max())
        swing_low = float(nifty['Low'].tail(20).min())
        
        return regime, reason, swing_high, swing_low
    except Exception as e:
        return "UNKNOWN", str(e), 0, 0

# ========= AI-2: OPTION FLOW ENGINE =========
def get_option_flow():
    try:
        # NSE Option Chain - needs session
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/"
        }
        sess = requests.Session()
        sess.get("https://www.nseindia.com", headers=headers, timeout=10)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        r = sess.get(url, headers=headers, timeout=10).json()
        
        data = r['records']['data']
        total_ce_oi = sum([x['CE']['openInterest'] for x in data if 'CE' in x])
        total_pe_oi = sum([x['PE']['openInterest'] for x in data if 'PE' in x])
        
        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        # Find max pain / support resistance
        ce_oi = {}
        pe_oi = {}
        for x in data:
            if 'CE' in x: ce_oi[x['strikePrice']] = x['CE']['openInterest']
            if 'PE' in x: pe_oi[x['strikePrice']] = x['PE']['openInterest']
        
        resistance = max(ce_oi, key=ce_oi.get) if ce_oi else 0
        support = max(pe_oi, key=pe_oi.get) if pe_oi else 0
        
        flow_msg = ""
        if pcr > 1.3: flow_msg = "HEAVY Put writing - Institutional BULLISH"
        elif pcr < 0.7: flow_msg = "HEAVY Call writing - Institutional BEARISH"
        else: flow_msg = "Neutral PCR"

        return pcr, support, resistance, flow_msg
    except Exception as e:
        print(f"Option flow fail: {e}")
        return 1.0, 0, 0, "Option data unavailable"

# ========= MAIN BRAIN =========
def main():
    regime, reason, swing_high, swing_low = get_market_regime()
    # get_market_regime now returns 4 values
    if isinstance(regime, tuple): # fix for old call
        regime, reason, swing_high, swing_low = regime

    pcr, support, resistance, flow_msg = get_option_flow()

    # DECISION LOGIC - This is your risk controller
    should_trade = True
    block_reason = ""
    if regime == "RANGE_LOW_VOL":
        should_trade = False
        block_reason = "Market in low volatility range - AI blocked trades to save capital"
    if pcr < 0.6 or pcr > 1.6:
        should_trade = False
        block_reason = f"Extreme PCR {pcr:.2f} - Institutional panic, AI blocked"

    # Build Message
    msg = f"""🤖 *AUGMENTED AI BRAIN - Market Check*
📅 {date.today()}

*1. Market Regime:* {regime}
   {reason}
   Swing High: {swing_high:.0f} | Low: {swing_low:.0f}

*2. Option Flow:* 
   PCR: {pcr:.2f} - {flow_msg}
   Support: {support} (Max PE OI)
   Resistance: {resistance} (Max CE OI)

*3. AI Decision:*
"""
    if should_trade:
        msg += "✅ *TRADE ALLOWED* - Running Nifty500 + Sniper logic next...\n"
        msg += "AI Learning: Will track today's trades in ai_memory.csv"
        # Here you call your existing screeners logic
        # For now we just log
    else:
        msg += f"🛑 *NO TRADE TODAY* - {block_reason}\n"
        msg += "Capital Protected - This is AI Risk Control working!"

    print(msg)
    send_telegram(msg)

    # Save to memory for self-learning
    mem_row = {
        "date": str(date.today()),
        "regime": regime,
        "pcr": pcr,
        "support": support,
        "resistance": resistance,
        "trade_allowed": should_trade,
        "swing_high": swing_high,
        "swing_low": swing_low
    }
    df_mem = pd.DataFrame([mem_row])
    if os.path.exists(MEMORY_FILE):
        df_mem.to_csv(MEMORY_FILE, mode='a', header=False, index=False)
    else:
        df_mem.to_csv(MEMORY_FILE, index=False)

if __name__ == "__main__":
    main()
