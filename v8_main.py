import requests, os, datetime, json
import risk_manager as rm
from v8_brain import SelfLearningBrain
from option_fetcher import fetch_option_chain as fetch_free_data
BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")

def fetch_spot():
    url="https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=5m&range=5d"
    d=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=10).json()['chart']['result'][0]
    q=d['indicators']['quote'][0]
    candles=[]
    for i in range(len(q['close'])):
        if q['close'][i]:
            candles.append({'close':float(q['close'][i]),'high':float(q['high'][i]),'low':float(q['low'][i]),'vol':float(q['volume'][i] or 0)})
    live=candles[-1]['close']
    # Features
    closes=[c['close'] for c in candles]
    def ema(p):
        k=2/(p+1); e=sum(closes[:p])/p
        for v in closes[p:]: e=v*k+e*(1-k)
        return e
    ema9,ema21=ema(9),ema(21)
    g=l=0
    for i in range(len(closes)-14,len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: g+=d
        else: l+=abs(d)
    rsi=100-(100/(1+g/l if l else 1)) if l else 50
    pv=sum(c['close']*c['vol'] for c in candles[-20:])
    vv=sum(c['vol'] for c in candles[-20:])
    vwap=pv/vv if vv else live
    # BankNifty live
    try:
        b=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEBANK?interval=1m&range=1d",
            headers={"User-Agent":"Mozilla/5.0"},timeout=8).json()['chart']['result'][0]
        bank_live=float(b['meta']['regularMarketPrice'])
    except: bank_live=51000
    return live,bank_live,candles,ema9,ema21,rsi,vwap

def decide_regime(live,ema9,ema21,rsi,vwap,pcr,vix):
    features={
        "vwap": 1 if live>vwap else -1,
        "ema": 1 if ema9>ema21 else -1,
        "rsi": 1 if 55<rsi<72 else (-1 if rsi<42 else 0),
        "pcr": 1 if pcr>1.1 else (-1 if pcr<0.85 else 0),
        "vix": -1 if vix>17 else (1 if vix<13 else 0),
        "cpr": 1 if live>vwap else -1,
        "oi": 1 if pcr>1 else -1
    }
    # Regime logic
    score=sum(features.values())
    if vix>18: regime="HIGH_VOL"
    elif score>=3: regime="STRONG_BULL"
    elif score==2: regime="BULL"
    elif score<=-3: regime="STRONG_BEAR"
    elif score==-2: regime="BEAR"
    else: regime="SIDEWAYS"
    return regime, features

def strategy_for_regime(regime, spot, index_name):
    atm=round(spot/50)*50 if index_name=="NIFTY" else round(spot/100)*100
    if regime in ["STRONG_BULL","BULL"]:
        return f"BUY {index_name} {atm} CE", atm, "CALL", 40, 80, 120
    elif regime in ["STRONG_BEAR","BEAR"]:
        return f"BUY {index_name} {atm} PE", atm, "PUT", 40, 80, 120
    elif regime=="SIDEWAYS":
        return f"SELL {index_name} IRON CONDOR {atm-200}/{atm+200}", atm, "CONDOR", 30, 50, 70
    else:
        return f"BUY {index_name} {atm} STRADDLE HEDGE", atm, "HEDGE", 50, 100, 150

# MAIN
now=datetime.datetime.now()
live,bank_live,candles,ema9,ema21,rsi,vwap=fetch_spot()
opt=fetch_free_data()
brain=SelfLearningBrain()

n_regime, n_feat=decide_regime(live,ema9,ema21,rsi,vwap,opt['NIFTY_PCR'],opt['VIX'])
b_regime, b_feat=decide_regime(bank_live,ema9,ema21,rsi,vwap,opt['BANK_PCR'],opt['VIX'])

n_score,n_conf=brain.get_score(n_feat,n_regime)
b_score,b_conf=brain.get_score(b_feat,b_regime)

can, risk_msg=rm.can_trade()
risk=rm.load_risk()

def build_msg(idx, spot, regime, feat, score, conf, pcr):
    strat, atm, typ, sl_pts, t1_pts, t2_pts = strategy_for_regime(regime, spot, idx)
    charges=rm.calc_charges(100,150) # approx option premium 100 to 150
    # Self learning weights
    w=brain.data["weights"]
    wr=brain.data["regime_perf"].get(regime,{}).get("win_rate",0.5)
    
    # Decision filter
    final_sig="NO TRADE"
    if conf>=75 and can and regime!="SIDEWAYS":
        final_sig=strat
    elif conf>=80 and regime=="SIDEWAYS":
        final_sig=strat
    
    return f"""
{idx} Spot {spot:.0f} | {regime} Score {score:.1f} Conf {conf}% PCR {pcr} VIX {opt['VIX']}
Features: {feat}
Strategy: {final_sig}
ATM {atm} SL {sl_pts}% TGT {t1_pts}%/{t2_pts}% | Charges ~₹{charges}
Past WinRate for {regime}: {wr*100:.0f}% | Total Reward: {brain.data['total_reward']}
Weights Learned: VWAP {w['vwap']:.2f} RSI {w['rsi']:.2f} PCR {w['pcr']:.2f} VIX {w['vix']:.2f}
"""

n_msg=build_msg("NIFTY",live,n_regime,n_feat,n_score,n_conf,opt['NIFTY_PCR'])
b_msg=build_msg("BANKNIFTY",bank_live,b_regime,b_feat,b_score,b_conf,opt['BANK_PCR'])

full_msg=f"""NIFTY+BANK OPTIONS V8.0 ELITE 🧠🔥 SELF-LEARNING
Time: {now.strftime('%d-%b %I:%M %p')} | {opt['status']}

{n_msg}
{b_msg}

🛡️ RISK V8:
Trades {risk['trades']}/3 PnL ₹{risk['pnl']:.0f} Loss ₹{risk['loss']:.0f}/2000 {risk_msg}
{'⛔ STOPPED' if risk['blocked'] else '✅ Active'}

🧠 BRAIN: Learned from {len(brain.data['trades'])} past trades | Experience file: v8_experience.json
Rule: Max 2 trades per index, 4 total/day | 40% SL | 80-120% TGT | >75% conf only
"""

print(full_msg)
if BOT_TOKEN and CHAT_ID:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id":CHAT_ID,"text":full_msg[:3800]})

# Simulate learning update with dummy 0 pnl for now - Real pnl you will update after market close via learn()
# To update after trade: brain.learn(n_feat,n_regime,strategy,pnl_points)
