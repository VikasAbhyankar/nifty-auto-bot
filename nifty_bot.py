import requests
import os
from datetime import datetime

# ========== TELEGRAM CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(msg):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        r = requests.post(url, data=data, timeout=20)
        print(f"Telegram status: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

# ========== DATA FETCH ==========
def get_market_data():
    """Fetch Nifty data from Yahoo Finance"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        # Daily for Pivots (last 30 days for ATR)
        daily_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=30d"
        # Intraday 5m for indicators (last 2 days)
        intraday_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=2d"
        
        d_json = requests.get(daily_url, headers=headers, timeout=15).json()
        i_json = requests.get(intraday_url, headers=headers, timeout=15).json()
        
        # Parse Daily
        d_result = d_json['chart']['result'][0]
        d_q = d_result['indicators']['quote'][0]
        daily_data = []
        for i in range(len(d_q['close'])):
            if d_q['close'][i] and d_q['high'][i] and d_q['low'][i]:
                daily_data.append({
                    'open': d_q['open'][i],
                    'high': d_q['high'][i],
                    'low': d_q['low'][i],
                    'close': d_q['close'][i]
                })
        
        if len(daily_data) < 2:
            raise Exception("Not enough daily data")
        
        prev = daily_data[-2]  # Yesterday for pivot calculation
        H, L, C, O = prev['high'], prev['low'], prev['close'], prev['open']
        
        # Parse Intraday for indicators
        i_result = i_json['chart']['result'][0]
        i_q = i_result['indicators']['quote'][0]
        closes = [c for c in i_q['close'] if c is not None]
        highs = [h for h in i_q['high'] if h is not None]
        lows = [l for l in i_q['low'] if l is not None]
        volumes = i_q['volume']
        
        if not closes:
            closes = [d['close'] for d in daily_data]
            highs = [d['high'] for d in daily_data]
            lows = [d['low'] for d in daily_data]
        
        current = closes[-1]
        
        return H, L, C, O, current, closes, highs, lows, volumes, daily_data
        
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None

# ========== INDICATOR FUNCTIONS ==========
def ema(data, period):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(data[:period]) / period
    for price in data[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

def rsi_calc(data, period=14):
    if len(data) < period + 1:
        return 50.0
    gains = 0
    losses = 0
    for i in range(len(data)-period, len(data)):
        if i <= 0: continue
        diff = data[i] - data[i-1]
        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)
    if losses == 0:
        return 75.0
    rs = gains / losses if losses != 0 else 0
    return 100 - (100 / (1 + rs))

def macd_calc(data):
    """Returns macd_line, signal_line, histogram"""
    if len(data) < 35:
        return 0, 0, 0
    ema12 = ema(data, 12)
    ema26 = ema(data, 26)
    if ema12 is None or ema26 is None:
        return 0, 0, 0
    macd_line = ema12 - ema26
    
    # Signal line - EMA9 of last 9 MACD values
    macd_hist = []
    for i in range(9):
        slice_end = len(data) - i if i > 0 else None
        slice_data = data[:slice_end]
        if len(slice_data) < 26:
            break
        e12 = ema(slice_data, 12)
        e26 = ema(slice_data, 26)
        if e12 and e26:
            macd_hist.append(e12 - e26)
    signal = sum(macd_hist) / len(macd_hist) if macd_hist else 0
    hist = macd_line - signal
    return macd_line, signal, hist

def supertrend_calc(closes, highs, lows, period=10, multiplier=3.0):
    """Supertrend calculation"""
    if len(closes) < period + 2:
        return "BULLISH", closes[-1], 0
    
    # Calculate ATR
    tr_list = []
    for i in range(1, min(len(closes), len(highs), len(lows))):
        h = highs[i]
        l = lows[i]
        pc = closes[i-1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)
    
    if len(tr_list) < period:
        atr = (highs[-1] - lows[-1]) if highs and lows else 100
    else:
        atr = sum(tr_list[-period:]) / period
    
    hl2 = (highs[-1] + lows[-1]) / 2 if highs and lows else closes[-1]
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr
    
    curr = closes[-1]
    # Simplified trend logic
    if curr > upper_band:
        trend = "BULLISH"
        st_val = lower_band
    elif curr < lower_band:
        trend = "BEARISH"
        st_val = upper_band
    else:
        trend = "BULLISH" if curr > lower_band else "BEARISH"
        st_val = lower_band if trend == "BULLISH" else upper_band
    
    return trend, st_val, atr

def calculate_all_pivots(H, L, C):
    """All pivot types from Pivot Boss book"""
    # Basic Pivot
    P = (H + L + C) / 3
    
    # 1. CPR - Central Pivot Range (Most Important)
    BC = (H + L) / 2
    TC = 2 * P - BC
    
    # 2. Classic Floor Pivots
    R1 = 2 * P - L
    S1 = 2 * P - H
    R2 = P + (H - L)
    S2 = P - (H - L)
    R3 = H + 2 * (P - L)
    S3 = L - 2 * (H - P)
    
    # 3. Fibonacci Pivots (0.382, 0.618, 1.0)
    rng = H - L
    fR1 = P + 0.382 * rng
    fS1 = P - 0.382 * rng
    fR2 = P + 0.618 * rng
    fS2 = P - 0.618 * rng
    fR3 = P + 1.0 * rng
    fS3 = P - 1.0 * rng
    
    # 4. Camarilla (Intraday reversal)
    cam_R4 = C + (H - L) * 1.1 / 2
    cam_S4 = C - (H - L) * 1.1 / 2
    cam_R3 = C + (H - L) * 1.1 / 4
    cam_S3 = C - (H - L) * 1.1 / 4
    cam_R5 = C + (H - L) * 1.1 / 1
    cam_S5 = C - (H - L) * 1.1 / 1
    
    # 5. Woodie's (More weight to close)
    woodie_P = (H + L + 2 * C) / 4
    woodie_R1 = 2 * woodie_P - L
    woodie_S1 = 2 * woodie_P - H
    woodie_R2 = woodie_P + (H - L)
    woodie_S2 = woodie_P - (H - L)
    
    return {
        'P': P, 'BC': BC, 'TC': TC,
        'classic_R1': R1, 'classic_S1': S1, 'classic_R2': R2, 'classic_S2': S2, 'classic_R3': R3, 'classic_S3': S3,
        'fib_R1': fR1, 'fib_S1': fS1, 'fib_R2': fR2, 'fib_S2': fS2, 'fib_R3': fR3, 'fib_S3': fS3,
        'cam_R3': cam_R3, 'cam_S3': cam_S3, 'cam_R4': cam_R4, 'cam_S4': cam_S4, 'cam_R5': cam_R5, 'cam_S5': cam_S5,
        'woodie_P': woodie_P, 'woodie_R1': woodie_R1, 'woodie_S1': woodie_S1, 'woodie_R2': woodie_R2, 'woodie_S2': woodie_S2
    }

# ========== MAIN LOGIC ==========
try:
    data = get_market_data()
    if not data:
        raise Exception("Failed to fetch market data from Yahoo")
    
    H, L, C, O, curr, closes, highs, lows, volumes, daily_data = data
    piv = calculate_all_pivots(H, L, C)
    
    # Indicators
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200) if len(closes) > 200 else ema([d['close'] for d in daily_data], 50)
    rsi_val = rsi_calc(closes, 14)
    macd_line, signal_line, hist = macd_calc(closes)
    st_trend, st_val, atr = supertrend_calc(closes, highs, lows, 10, 3.0)
    
    # VWAP (Simplified)
    if highs and lows and len(highs) >= 20:
        typical = [(h+l+c)/3 for h,l,c in zip(highs[-50:], lows[-50:], closes[-50:])]
        vwap = sum(typical) / len(typical) if typical else piv['P']
    else:
        vwap = piv['P']
    
    # Bollinger Bands (20,2)
    if len(closes) >= 20:
        ma20 = sum(closes[-20:]) / 20
        std = (sum((x-ma20)**2 for x in closes[-20:]) / 20) ** 0.5
        bb_upper = ma20 + 2*std
        bb_lower = ma20 - 2*std
    else:
        bb_upper = curr + 100
        bb_lower = curr - 100
    
    # CPR Analysis
    cpr_width = abs(piv['TC'] - piv['BC'])
    cpr_pct = (cpr_width / piv['P']) * 100
    if cpr_pct < 0.15:
        cpr_status = "🔥 NARROW CPR (Big Trend Day Expected!)"
    elif cpr_pct > 0.50:
        cpr_status = "💤 WIDE CPR (Choppy Range Day)"
    else:
        cpr_status = "Normal CPR"
    
    # ========== CONFLUENCE SCORING (10 points) ==========
    buy_pts = 0
    sell_pts = 0
    reasons = []
    
    # 1. CPR Position (2 pts) - Core Pivot Boss concept
    if curr > piv['TC']:
        buy_pts += 2
        reasons.append("✅ Above CPR (Bullish)")
    elif curr < piv['BC']:
        sell_pts += 2
        reasons.append("🔴 Below CPR (Bearish)")
    else:
        reasons.append("⚪ Inside CPR - Wait")
    
    # 2. Supertrend (2 pts) - Most powerful trend filter
    if st_trend == "BULLISH":
        buy_pts += 2
        reasons.append(f"✅ Supertrend BULL {st_val:.0f}")
    else:
        sell_pts += 2
        reasons.append(f"🔴 Supertrend BEAR {st_val:.0f}")
    
    # 3. MACD (2 pts)
    if macd_line > signal_line and hist > 0:
        buy_pts += 2
        reasons.append(f"✅ MACD Bullish ({macd_line:.1f} > {signal_line:.1f})")
    elif macd_line < signal_line and hist < 0:
        sell_pts += 2
        reasons.append(f"🔴 MACD Bearish ({macd_line:.1f} < {signal_line:.1f})")
    else:
        reasons.append(f"⚪ MACD Neutral")
    
    # 4. EMA (1 pt)
    if ema9 and ema21:
        if ema9 > ema21 and curr > ema9:
            buy_pts += 1
            reasons.append(f"✅ EMA9 {ema9:.0f} > EMA21 {ema21:.0f}")
        elif ema9 < ema21 and curr < ema9:
            sell_pts += 1
            reasons.append(f"🔴 EMA9 {ema9:.0f} < EMA21 {ema21:.0f}")
    
    # 5. VWAP (1 pt)
    if curr > vwap:
        buy_pts += 1
        reasons.append(f"✅ Above VWAP {vwap:.0f}")
    else:
        sell_pts += 1
        reasons.append(f"🔴 Below VWAP {vwap:.0f}")
    
    # 6. RSI (1 pt)
    if rsi_val >= 60:
        buy_pts += 1
        reasons.append(f"✅ RSI {rsi_val:.0f} Strong")
    elif rsi_val <= 40:
        sell_pts += 1
        reasons.append(f"🔴 RSI {rsi_val:.0f} Weak")
    else:
        reasons.append(f"⚪ RSI {rsi_val:.0f} Neutral")
    
    # 7. Camarilla Breakout (1 pt)
    if curr > piv['cam_R4']:
        buy_pts += 1
        reasons.append("✅ Breaks Cam R4 (Breakout)")
    elif curr < piv['cam_S4']:
        sell_pts += 1
        reasons.append("🔴 Breaks Cam S4 (Breakdown)")
    
    # ========== FINAL SIGNAL ==========
    total = buy_pts + sell_pts
    if buy_pts >= 6 and buy_pts > sell_pts:
        signal = f"🟢 *STRONG BUY* ({buy_pts}/10)"
        conf = int((buy_pts/total)*100) if total else 0
        sl = min(piv['classic_S1'], st_val, curr - atr*1.5)
        tgt1 = piv['classic_R1']
        tgt2 = piv['classic_R2']
    elif sell_pts >= 6 and sell_pts > buy_pts:
        signal = f"🔴 *STRONG SELL* ({sell_pts}/10)"
        conf = int((sell_pts/total)*100) if total else 0
        sl = max(piv['classic_R1'], st_val, curr + atr*1.5)
        tgt1 = piv['classic_S1']
        tgt2 = piv['classic_S2']
    elif buy_pts > sell_pts:
        signal = f"🟡 *WEAK BUY* ({buy_pts}/10)"
        conf = int((buy_pts/total)*100) if total else 0
        sl = piv['classic_S1']
        tgt1 = piv['classic_R1']
        tgt2 = piv['classic_R2']
    elif sell_pts > buy_pts:
        signal = f"🟠 *WEAK SELL* ({sell_pts}/10)"
        conf = int((sell_pts/total)*100) if total else 0
        sl = piv['classic_R1']
        tgt1 = piv['classic_S1']
        tgt2 = piv['classic_S2']
    else:
        signal = "⚪ *NO TRADE - WAIT*"
        conf = 0
        sl = piv['classic_S2']
        tgt1 = piv['classic_S1']
        tgt2 = piv['classic_R1']
    
    rr1 = abs(tgt1-curr) / max(1, abs(curr-sl))
    rr2 = abs(tgt2-curr) / max(1, abs(curr-sl))
    
    # ========== TELEGRAM MESSAGE ==========
    msg = f"""🚀 *NIFTY PIVOT BOSS PRO MAX*
📅 {datetime.now().strftime('%d-%b-%Y %I:%M %p IST')}
Prev: O {O:.0f} H {H:.0f} L {L:.0f} C {C:.0f}
Live: {curr:.0f}

💎 *CPR (Pivot Boss Core):*
TC {piv['TC']:.0f} | P {piv['P']:.0f} | BC {piv['BC']:.0f}
Width {cpr_width:.0f} ({cpr_pct:.2f}%) - {cpr_status}

📊 *ALL PIVOT TYPES:*
*Classic:* R3 {piv['classic_R3']:.0f} R2 {piv['classic_R2']:.0f} R1 {piv['classic_R1']:.0f} | P {piv['P']:.0f} | S1 {piv['classic_S1']:.0f} S2 {piv['classic_S2']:.0f} S3 {piv['classic_S3']:.0f}
*Fib:* R3 {piv['fib_R3']:.0f} R2 {piv['fib_R2']:.0f} R1 {piv['fib_R1']:.0f} S1 {piv['fib_S1']:.0f} S2 {piv['fib_S2']:.0f} S3 {piv['fib_S3']:.0f}
*Cam:* R5 {piv['cam_R5']:.0f} R4 {piv['cam_R4']:.0f} R3 {piv['cam_R3']:.0f} S3 {piv['cam_S3']:.0f} S4 {piv['cam_S4']:.0f} S5 {piv['cam_S5']:.0f}
*Woodie:* R2 {piv['woodie_R2']:.0f} R1 {piv['woodie_R1']:.0f} P {piv['woodie_P']:.0f} S1 {piv['woodie_S1']:.0f} S2 {piv['woodie_S2']:.0f}

📈 *INDICATORS:*
EMA9 {ema9:.0f} | EMA21 {ema21:.0f} | EMA50 {ema50:.0f if ema50 else 0:.0f}
VWAP {vwap:.0f}
RSI(14) {rsi_val:.1f} {'🟢' if rsi_val>60 else '🔴' if rsi_val<40 else '⚪'}
MACD {macd_line:.2f} | Signal {signal_line:.2f} | Hist {hist:.2f} {'🟢' if hist>0 else '🔴'}
Supertrend {st_trend} {st_val:.0f} {'🟢' if st_trend=='BULLISH' else '🔴'}
ATR {atr:.0f} | BB {bb_lower:.0f}-{bb_upper:.0f}

{signal} - {conf}% Confidence
(Buy {buy_pts} vs Sell {sell_pts})

🎯 *TRADE PLAN:*
Entry: {curr:.0f}
SL: {sl:.0f} ({abs(curr-sl):.0f} pts)
TGT1: {tgt1:.0f} ({abs(tgt1-curr):.0f} pts) RR 1:{rr1:.2f}
TGT2: {tgt2:.0f} ({abs(tgt2-curr):.0f} pts) RR 1:{rr2:.2f}

🔍 *Confluence:*
{chr(10).join(reasons)}

📖 *PIVOT BOSS RULES:*
1. Above CPR + ST Bull + MACD Bull = High Prob BUY
2. Below CPR + ST Bear + MACD Bear = High Prob SELL
3. Inside CPR first 15 min = NO TRADE (Trading in Zone)
4. Narrow CPR = Expect 100+ pts trend
5. SL = Supertrend or S1/R1

_Auto Bot 9:15 AM IST - GitHub Actions_
"""
    
    send_telegram(msg)
    print("PRO MAX Pivot Boss message sent successfully!")

except Exception as e:
    error_msg = f"⚠️ *Bot Error*\n{str(e)}\nTime: {datetime.now()}"
    send_telegram(error_msg)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
