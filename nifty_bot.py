import requests, os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=data, timeout=20)

def get_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    daily_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=30d"
    intraday_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=2d"
    
    r1 = requests.get(daily_url, headers=headers, timeout=15).json()
    r2 = requests.get(intraday_url, headers=headers, timeout=15).json()
    
    d_result = r1['chart']['result'][0]
    d_q = d_result['indicators']['quote'][0]
    daily = []
    for i in range(len(d_q['close'])):
        if d_q['close'][i]:
            daily.append((d_q['open'][i], d_q['high'][i], d_q['low'][i], d_q['close'][i]))
    
    H, L, C = daily[-2][1], daily[-2][2], daily[-2][3]
    
    i_result = r2['chart']['result'][0]
    i_q = i_result['indicators']['quote'][0]
    closes = [c for c in i_q['close'] if c is not None]
    highs = [h for h in i_q['high'] if h is not None]
    lows = [l for l in i_q['low'] if l is not None]
    
    return H, L, C, closes, highs, lows

def ema(data, period):
    if len(data) < period: return None
    k = 2 / (period + 1)
    e = sum(data[:period]) / period
    for p in data[period:]:
        e = p * k + e * (1 - k)
    return e

def rsi(data, period=14):
    if len(data) < period+1: return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = data[-i] - data[-i-1]
        if diff > 0: gains += diff
        else: losses += abs(diff)
    if losses == 0: return 75
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def macd_calc(data):
    if len(data) < 35: return 0, 0, 0
    ema12 = ema(data, 12)
    ema26 = ema(data, 26)
    if not ema12 or not ema26: return 0,0,0
    macd_line = ema12 - ema26
    # Signal line - EMA9 of MACD history
    # Simplified: calculate MACD for last 9 periods
    macd_hist = []
    for i in range(9):
        slice_data = data[:len(data)-i if i>0 else None]
        if len(slice_data) < 26: break
        e12 = ema(slice_data, 12)
        e26 = ema(slice_data, 26)
        if e12 and e26:
            macd_hist.append(e12 - e26)
    signal = sum(macd_hist)/len(macd_hist) if macd_hist else 0
    hist = macd_line - signal
    return macd_line, signal, hist

def supertrend_calc(closes, highs, lows, period=10, multiplier=3.0):
    if len(closes) < period+2: return None, None
    # ATR
    tr_list = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i] if i < len(highs) else closes[i], lows[i] if i < len(lows) else closes[i], closes[i-1]
        tr = max(h-l, abs(h-pc), abs(l-pc))
        tr_list.append(tr)
    atr = sum(tr_list[-period:]) / period
    
    hl2 = (highs[-1] + lows[-1]) / 2 if highs and lows else closes[-1]
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    
    # Trend: if close > upper band -> bullish, if close < lower -> bearish
    curr = closes[-1]
    if curr > upper:
        trend = "BULLISH"
        st_value = lower
    elif curr < lower:
        trend = "BEARISH"
        st_value = upper
    else:
        # Use previous logic
        trend = "BULLISH" if curr > lower else "BEARISH"
        st_value = lower if trend=="BULLISH" else upper
    
    return trend, st_value, atr

try:
    H, L, C, closes, highs, lows = get_data()
    P = (H+L+C)/3
    BC = (H+L)/2
    TC = 2*P - BC
    R1 = 2*P - L
    S1 = 2*P - H
    R2 = P + (H-L)
    S2 = P - (H-L)
    Cam_R4 = C + (H-L)*1.1/2
    Cam_S4 = C - (H-L)*1.1/2
    
    curr = closes[-1]
    
    # Indicators
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    rsi_val = rsi(closes, 14)
    macd_line, signal_line, hist = macd_calc(closes)
    st_trend, st_val, atr = supertrend_calc(closes, highs, lows)
    
    # VWAP
    typical = [(h+l+c)/3 for h,l,c in zip(highs[-50:], lows[-50:], closes[-50:])]
    vwap = sum(typical)/len(typical) if typical else P
    
    buy, sell = 0, 0
    reasons = []
    
    # 1. CPR (2 pts)
    if curr > TC:
        buy+=2; reasons.append("✅ Above CPR")
    elif curr < BC:
        sell+=2; reasons.append("🔴 Below CPR")
    else:
        reasons.append("⚪ Inside CPR")
    
    # 2. EMA (1 pt)
    if ema9 and ema21:
        if ema9 > ema21 and curr > ema9:
            buy+=1; reasons.append(f"✅ EMA9 {ema9:.0f} > EMA21 {ema21:.0f}")
        elif ema9 < ema21 and curr < ema9:
            sell+=1; reasons.append(f"🔴 EMA9 {ema9:.0f} < EMA21 {ema21:.0f}")
    
    # 3. Supertrend (2 pts - Most powerful per Pivot Boss)
    if st_trend == "BULLISH":
        buy+=2; reasons.append(f"✅ Supertrend BULLISH ({st_val:.0f})")
    else:
        sell+=2; reasons.append(f"🔴 Supertrend BEARISH ({st_val:.0f})")
    
    # 4. MACD (2 pts)
    if macd_line > signal_line and hist > 0:
        buy+=2; reasons.append(f"✅ MACD Bullish ({macd_line:.1f}>{signal_line:.1f})")
    elif macd_line < signal_line and hist < 0:
        sell+=2; reasons.append(f"🔴 MACD Bearish ({macd_line:.1f}<{signal_line:.1f})")
    else:
        reasons.append(f"⚪ MACD Neutral")
    
    # 5. VWAP (1 pt)
    if curr > vwap:
        buy+=1; reasons.append(f"✅ Above VWAP {vwap:.0f}")
    else:
        sell+=1; reasons.append(f"🔴 Below VWAP {vwap:.0f}")
    
    # 6. RSI (1 pt)
    if rsi_val > 60:
        buy+=1; reasons.append(f"✅ RSI {rsi_val:.0f} Strong")
    elif rsi_val < 40:
        sell+=1; reasons.append(f"🔴 RSI {rsi_val:.0f} Weak")
    
    # 7. Camarilla Breakout (1 pt)
    if curr > Cam_R4:
        buy+=1; reasons.append("✅ Cam R4 Breakout")
    elif curr < Cam_S4:
        sell+=1; reasons.append("🔴 Cam S4 Breakdown")
    
    total = buy + sell
    # Final Signal - Need 6/10 for strong
    if buy >= 6 and buy > sell:
        signal = f"🟢 *STRONG BUY* ({buy}/10)"
        conf = int(buy/total*100) if total else 0
        sl = min(S1, st_val, curr-atr)
        tgt = R2
    elif sell >= 6 and sell > buy:
        signal = f"🔴 *STRONG SELL* ({sell}/10)"
        conf = int(sell/total*100) if total else 0
        sl = max(R1, st_val, curr+atr)
        tgt = S2
    elif buy > sell:
        signal = f"🟡 *WEAK BUY* ({buy}/10)"
        conf = int(buy/total*100) if total else 0
        sl = S1; tgt = R1
    elif sell > buy:
        signal = f"🟠 *WEAK SELL* ({sell}/10)"
        conf = int(sell/total*100) if total else 0
        sl = R1; tgt = S1
    else:
        signal = "⚪ *NO TRADE*"
        conf = 0
        sl = S2; tgt = R2
    
    cpr_w = abs(TC-BC)
    cpr_pct = cpr_w/P*100
    cpr_type = "NARROW (Trend Day)" if cpr_pct<0.2 else "WIDE (Range Day)" if cpr_pct>0.5 else "Normal"
    
    msg = f"""🚀 *NIFTY PIVOT BOSS + SUPERTREND + MACD*

📅 {datetime.now().strftime('%d-%b %I:%M %p')}
Prev H {H:.0f} L {L:.0f} C {C:.0f} | Live {curr:.0f}

💎 *CPR:* TC {TC:.0f} P {P:.0f} BC {BC:.0f} ({cpr_type})

📊 *LEVELS:* R2 {R2:.0f} R1 {R1:.0f} S1 {S1:.0f} S2 {S2:.0f}
Cam R4 {Cam_R4:.0f} S4 {Cam_S4:.0f}

📈 *INDICATORS:*
EMA9 {ema9:.0f} EMA21 {ema21:.0f} EMA50 {ema50:.0f if ema50 else 0:.0f}
VWAP {vwap:.0f}
RSI {rsi_val:.1f}
MACD {macd_line:.1f} Signal {signal_line:.1f} Hist {hist:.1f}
Supertrend {st_trend} {st_val:.0f}
ATR {atr:.0f}

{signal} - {conf}% Confidence

🎯 *TRADE PLAN:*
Entry: {curr:.0f}
SL: {sl:.0f} ({abs(curr-sl):.0f} pts)
Target1: {tgt:.0f} ({abs(tgt-curr):.0f} pts)
RR: 1:{abs(tgt-curr)/max(1,abs(curr-sl)):.2f}

🔍 *Confluence ({buy} Buy vs {sell} Sell):*
{chr(10).join(reasons)}

⚡ *Pivot Boss Rule:*
ST + MACD + CPR alignment = High Probability
{'>'}6 points = Take Trade, <4 = No Trade
"""
    send_telegram(msg)
    print("Supertrend + MACD sent!")

except Exception as e:
    send_telegram(f"⚠️ Error: {e}")
    print(e)
