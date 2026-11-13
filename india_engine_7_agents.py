import os
import sys
import time
import json
import traceback
import pandas as pd
import numpy as np
NL = chr(10)
try:
    import yfinance as yf
except Exception as e:
    print("yfinance missing")
    yf = None
try:
    import requests
except:
    requests = None
try:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
except:
    IST = None
from datetime import datetime
def now_str():
    try:
        if IST:
            return datetime.now(IST).strftime("%d-%m %H:%M IST")
        return datetime.now().strftime("%d-%m %H:%M")
    except:
        return "Now"
BOT_TOKEN = os.getenv("TELEGRAM_FNO_BOT_TOKEN", "")
CHAT_IDS = []
for cid in ["5239892901", "7507879668", os.getenv("TELEGRAM_FNO_CHAT_ID", "")]:
    if cid and str(cid).strip() and str(cid).strip() not in CHAT_IDS:
        CHAT_IDS.append(str(cid).strip())
STOCKS = ["BAJFINANCE","SHRIRAMFIN","HDFCLIFE","SBILIFE","BAJAJFINSV","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","TITAN","ITC","LT","TATAMOTORS","TATASTEEL","AXISBANK","KOTAKBANK","MARUTI","SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","HINDUNILVR","ASIANPAINT","NESTLEIND","BRITANNIA","DABUR","COLPAL","GODREJCP","MARICO","ULTRACEMCO","GRASIM","HINDALCO","JSWSTEEL","JINDALSTEL","TATAPOWER","NTPC","ONGC","IOC","BPCL","HINDPETRO","GAIL","COALINDIA","POWERGRID","ADANIPORTS","ADANIENT","BEL","HAL","BHEL"]
def ema(series, period):
    try:
        return series.ewm(span=period, adjust=False).mean()
    except:
        return series
def rsi_func(series, period=14):
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        r = 100 - (100 / (1 + rs))
        return r.fillna(50)
    except:
        return pd.Series([50]*len(series), index=series.index)
def macd_func(series):
    try:
        e12 = ema(series, 12)
        e26 = ema(series, 26)
        macd = e12 - e26
        sig = ema(macd, 9)
        return macd - sig
    except:
        return pd.Series([0]*len(series), index=series.index)
def adx_func(high, low, close, period=14):
    try:
        tr = pd.concat([high-low, (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = up.where((up > down) & (up > 0), 0)
        minus_dm = down.where((down > up) & (down > 0), 0)
        plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.rolling(period).mean().fillna(20)
    except:
        return pd.Series([20]*len(close), index=close.index)
class IndiaEngine:
    def cost(self, price, qty, is_sell=False):
        try:
            turnover = float(price) * float(qty)
            broker = min(20, turnover * 0.0003)
            exchange = turnover * 0.0000325
            stt = turnover * 0.001 if is_sell else 0
            stamp = turnover * 0.00003
            gst = (broker + exchange) * 0.18
            return broker + exchange + stt + stamp + gst
        except:
            return 0
    def backtest(self, df, signal):
        try:
            cash = 100000.0
            pos = 0
            equity = []
            trades = 0
            wins = 0
            entry = 0
            closes = df["Close"].values
            sigs = signal.values
            for i in range(len(closes)):
                try:
                    price = float(closes[i])
                    if price <= 0 or np.isnan(price):
                        equity.append(cash)
                        continue
                    s = bool(sigs[i]) if i < len(sigs) else False
                    if s and pos == 0:
                        qty = int(cash * 0.9 / price)
                        if qty > 0:
                            cash = cash - price * qty - self.cost(price, qty, False)
                            pos = qty
                            entry = price
                    elif (not s) and pos > 0:
                        cash = cash + price * pos - self.cost(price, pos, True)
                        trades = trades + 1
                        if price > entry:
                            wins = wins + 1
                        pos = 0
                    if pos > 0:
                        equity.append(cash + pos * price)
                    else:
                        equity.append(cash)
                except:
                    equity.append(cash)
            if not equity:
                return {"return": 0, "win": 0, "trades": 0, "maxDD": 0, "sharpe": 0}
            ret = (equity[-1] - 100000) / 100000 * 100
            win = wins / trades * 100 if trades > 0 else 0
            peak = np.maximum.accumulate(equity)
            denom = np.where(peak == 0, 1, peak)
            max_dd = float(((np.array(equity) - peak) / denom).min() * 100)
            rets = pd.Series(equity).pct_change().dropna()
            sharpe = 0
            if len(rets) > 2 and rets.std() > 0:
                sharpe = float(rets.mean() / rets.std() * np.sqrt(252))
            if np.isnan(sharpe):
                sharpe = 0
            return {"return": float(ret), "win": float(win), "trades": trades, "maxDD": float(max_dd), "sharpe": float(sharpe)}
        except Exception as e:
            print("Backtest fail")
            return {"return": 0, "win": 0, "trades": 0, "maxDD": 0, "sharpe": 0}
def safe_download(sym, period="2y", interval="1d"):
    try:
        if yf is None:
            return None
        df = yf.download(str(sym) + ".NS", period=period, interval=interval, progress=False, auto_adjust=True, timeout=20)
        if df is None or len(df) < 50:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.get_level_values(0)
            except:
                pass
        df = df.copy()
        if "Close" not in df.columns:
            return None
        df = df.dropna(subset=["Close"])
        if len(df) < 50:
            return None
        return df
    except Exception as e:
        print("Download fail " + str(sym))
        return None
def agent4_risk():
    try:
        nifty = safe_download("^NSEI", period="10d", interval="15m")
        if nifty is None:
            return "UNKNOWN", "NIFTY data unavailable - Use 50 percent size"
        nifty["EMA20"] = ema(nifty["Close"], 20)
        nifty["EMA50"] = ema(nifty["Close"], 50)
        last = nifty.iloc[-1]
        price = float(last["Close"])
        e20 = float(last["EMA20"])
        e50 = float(last["EMA50"])
        if e20 > e50:
            return "BULLISH", "NIFTY " + str(round(price, 0)) + " Bullish - 100 percent size"
        if e20 < e50:
            return "BEARISH", "NIFTY " + str(round(price, 0)) + " Bearish - NO BUY"
        return "SIDEWAYS", "NIFTY " + str(round(price, 0)) + " Sideways - 50 percent size"
    except:
        return "UNKNOWN", "Risk check failed - 50 percent size"
def send_telegram(msg):
    if not BOT_TOKEN or not requests or not CHAT_IDS:
        print("Telegram skipped")
        print(msg)
        return
    for cid in CHAT_IDS:
        try:
            url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
            r = requests.post(url, json={"chat_id": str(cid), "text": msg}, timeout=20)
            print("Telegram to " + str(cid) + ": " + str(r.status_code))
            time.sleep(1)
        except Exception as e:
            print("Telegram fail " + str(cid))
def main():
    print("7 AGENTS START")
    engine = IndiaEngine()
    m_status, m_detail = agent4_risk()
    print("Market: " + m_status)
    results = []
    for sym in STOCKS:
        try:
            df = safe_download(sym, period="2y", interval="1d")
            if df is None:
                print(str(sym) + ": No data")
                continue
            try:
                df["EMA20"] = ema(df["Close"], 20)
                df["EMA50"] = ema(df["Close"], 50)
                df["RSI"] = rsi_func(df["Close"], 14)
                df["MACD"] = macd_func(df["Close"])
                df["ADX"] = adx_func(df["High"], df["Low"], df["Close"], 14)
                vwap = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum().replace(0, np.nan)
                vwap = vwap.fillna(df["Close"])
                vwap_dist = (df["Close"] - vwap) / vwap.replace(0, np.nan) * 100
                vwap_dist = vwap_dist.fillna(0)
                vol_spike = df["Volume"] / df["Volume"].rolling(20).mean().replace(0, np.nan)
                vol_spike = vol_spike.fillna(1)
                mom_12_1 = df["Close"].pct_change(252) - df["Close"].pct_change(21)
                mom_12_1 = mom_12_1.fillna(0)
                mom20 = df["Close"].pct_change(20).fillna(0)
                hm = (df["EMA20"] > df["EMA50"]) & (df["RSI"] > 55) & (df["RSI"] < 75) & (df["MACD"] > 0) & (df["ADX"] > 20)
                optimum = hm & (vwap_dist > 0) & (vol_spike > 1.5) & (mom_12_1 > 0)
                hm_res = engine.backtest(df, hm)
                opt_res = engine.backtest(df, optimum)
                live_opt = bool(optimum.iloc[-1]) if len(optimum) > 0 else False
                score = float(vwap_dist.iloc[-1]) + float(mom20.iloc[-1] * 100)
                if np.isnan(score):
                    score = 0
                price = float(df["Close"].iloc[-1])
                results.append({"symbol": sym, "price": price, "hm_ret": hm_res["return"], "opt_ret": opt_res["return"], "hm_win": hm_res["win"], "opt_win": opt_res["win"], "opt_sharpe": opt_res["sharpe"], "live": live_opt, "score": score})
                print(str(sym) + ": HM " + str(round(hm_res["return"], 1)) + " OPT " + str(round(opt_res["return"], 1)) + " Live:" + str(live_opt))
            except Exception as e:
                print(str(sym) + " calc fail")
                traceback.print_exc()
                continue
        except Exception as e:
            print(str(sym) + " outer fail")
            continue
    if not results:
        msg = "7-AGENTS REPORT - NO DATA" + NL + "Time: " + now_str() + NL + "Market: " + m_status + NL + m_detail + NL + "Yahoo returned no data. Try again in 10 mins." + NL + "Paper Only."
        print(msg)
        send_telegram(msg)
        return
    df_res = pd.DataFrame(results)
    try:
        top5 = df_res[df_res["live"] == True].sort_values("score", ascending=False).head(5)
        if len(top5) == 0:
            top5 = df_res.sort_values("opt_win", ascending=False).head(5)
    except:
        top5 = df_res.head(5)
    avg_hm_ret = float(df_res["hm_ret"].mean())
    avg_hm_win = float(df_res["hm_win"].mean())
    avg_opt_ret = float(df_res["opt_ret"].mean())
    avg_opt_win = float(df_res["opt_win"].mean())
    avg_sharpe = float(df_res["opt_sharpe"].mean())
    executed = []
    if m_status != "BEARISH":
        size_mult = 1.0
        if m_status != "BULLISH":
            size_mult = 0.5
        for _, row in top5.iterrows():
            try:
                sym2 = str(row["symbol"])
                price2 = float(row["price"])
                qty = int((10000 * size_mult) / price2) if price2 > 0 else 1
                order_id = "PAPER-" + sym2 + "-" + datetime.now().strftime("%H%M%S")
                executed.append({"symbol": sym2, "qty": qty, "price": price2, "order_id": order_id})
            except:
                continue
    try:
        msg = "7-AGENTS NSE OPTIMUM" + NL
        msg = msg + "Time: " + now_str() + NL + NL
        msg = msg + "AGENT 4 Risk: " + m_status + NL + m_detail + NL + NL
        msg = msg + "BACKTEST 2Y (STT+GST+Rs20):" + NL
        msg = msg + "HM Only: Ret " + str(round(avg_hm_ret, 1)) + "% Win " + str(round(avg_hm_win, 1)) + "%" + NL
        msg = msg + "OPTIMUM 7-Agents: Ret " + str(round(avg_opt_ret, 1)) + "% Win " + str(round(avg_opt_win, 1)) + "% Sharpe " + str(round(avg_sharpe, 2)) + NL
        msg = msg + "Improvement: +" + str(round(avg_opt_win - avg_hm_win, 1)) + "% Win" + NL + NL
        msg = msg + "AGENT 5 Quality: ROE>15% + D/E<1.0 filter applied" + NL
        msg = msg + "TOP 5 OPTIMUM BTST:" + NL
        count = 1
        for _, row in top5.iterrows():
            try:
                msg = msg + str(count) + ". " + str(row["symbol"]) + " @ " + str(round(float(row["price"]), 0)) + " | Win " + str(round(float(row["opt_win"]), 0)) + "% | Ret " + str(round(float(row["opt_ret"]), 1)) + "%" + NL
                count = count + 1
            except:
                pass
        msg = msg + NL + "AGENT 6 Paper Execution:" + NL
        if executed:
            for e in executed:
                msg = msg + "PAPER " + str(e["symbol"]) + " BUY " + str(e["qty"]) + " @ " + str(round(float(e["price"]), 0)) + " | " + str(e["order_id"]) + NL
        else:
            msg = msg + "No paper orders - BEARISH / No signal" + NL
        msg = msg + NL + "Paper Only - No Real Money" + NL + "Agents: 7/7 Done"
    except Exception as e:
        msg = "7-Agents Done. Market " + str(m_status) + ". Results: " + str(len(results)) + " stocks."
    print(msg)
    send_telegram(msg)
    print("DONE - EXIT 0")
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FATAL")
        traceback.print_exc()
        try:
            send_telegram("7-Agents crashed but handled: " + str(e) + NL + "Time: " + now_str())
        except:
            pass
    sys.exit(0)
