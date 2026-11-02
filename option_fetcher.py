import requests, time, json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive"
}

def fetch_option_chain(symbol="NIFTY"):
    # TRY 1: NiftyTrader API - WORKS from GitHub!
    try:
        url = f"https://webapi.niftytrader.in/webapi/option/fatch-option-chain?symbol={symbol.lower()}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and "opDatas" in r.text:
            data = r.json()
            ce_oi = sum([x.get('call_oi',0) for x in data.get('opDatas',[]) if x.get('call_oi')])
            pe_oi = sum([x.get('put_oi',0) for x in data.get('opDatas',[]) if x.get('put_oi')])
            pcr = round(pe_oi/ce_oi, 2) if ce_oi >0 else 1.0
            # VIX from Yahoo backup
            try:
                vix_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX?interval=1m&range=1d"
                vr = requests.get(vix_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
                vix = float(vr['chart']['result'][0]['meta']['regularMarketPrice'])
            except:
                vix = 14.5
            return {"pcr": pcr, "vix": vix, "status": "LIVE_NiftyTrader"}
    except Exception as e:
        print(f"Try1 failed: {e}")

    # TRY 2: NSE with session cookie
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        time.sleep(1.5)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and "records" in r.text:
            data = r.json()
            ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x])
            pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x])
            pcr = round(pe_oi/ce_oi, 2) if ce_oi else 1.0
            return {"pcr": pcr, "vix": 14.5, "status": "LIVE_NSE"}
    except Exception as e:
        print(f"Try2 failed: {e}")

    # TRY 3: Fallback
    return {"pcr": 1.0, "vix": 14.5, "status": f"Fallback"}

def fetch_free_data():
    try:
        nifty = fetch_option_chain("NIFTY")
        bank = fetch_option_chain("BANKNIFTY")
        return {
            "NIFTY_PCR": nifty["pcr"],
            "BANKNIFTY_PCR": bank["pcr"],
            "BANK_PCR": bank["pcr"],
            "VIX": nifty["vix"],
            "NIFTY": nifty,
            "BANKNIFTY": bank,
            "pcr": nifty["pcr"],
            "vix": nifty["vix"],
            "status": nifty["status"]
        }
    except:
        return {
            "NIFTY_PCR": 1.0,
            "BANKNIFTY_PCR": 1.0,
            "BANK_PCR": 1.0,
            "VIX": 14.5,
            "status": "Fallback"
        }
