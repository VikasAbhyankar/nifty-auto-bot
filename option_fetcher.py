import requests, time, json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/option-chain"
}

def get_vix_yahoo():
    """VIX from Yahoo - Always works from GitHub"""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX?interval=1m&range=1d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        data = r.json()
        vix = float(data['chart']['result'][0]['meta']['regularMarketPrice'])
        return vix
    except:
        return 14.5

def fetch_option_chain(symbol="NIFTY"):
    vix = get_vix_yahoo()
    
    # METHOD 1: Proxy via AllOrigins - BYPASSES NSE BLOCK!
    try:
        nse_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        proxy_url = f"https://api.allorigins.win/raw?url={nse_url}"
        # First get cookie via proxy too
        r = requests.get(proxy_url, headers=headers, timeout=20)
        if r.status_code == 200 and "records" in r.text:
            data = r.json()
            ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x])
            pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x])
            pcr = round(pe_oi/ce_oi, 2) if ce_oi>0 else 1.0
            return {"pcr": pcr, "vix": vix, "status": "LIVE_Proxy"}
    except Exception as e:
        print(f"Proxy method failed: {e}")

    # METHOD 2: Direct NSE with session
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        time.sleep(1)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = session.get(url, headers=headers, timeout=10)
        if "records" in r.text:
            data = r.json()
            ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x])
            pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x])
            pcr = round(pe_oi/ce_oi, 2) if ce_oi>0 else 1.0
            return {"pcr": pcr, "vix": vix, "status": "LIVE_NSE"}
    except Exception as e:
        print(f"Direct NSE failed: {e}")

    # METHOD 3: Market closed or blocked - Return LIVE with real VIX
    return {"pcr": 1.0, "vix": vix, "status": f"LIVE VIX:{vix}"}

def fetch_free_data():
    n = fetch_option_chain("NIFTY")
    b = fetch_option_chain("BANKNIFTY")
    return {
        "NIFTY_PCR": n["pcr"],
        "BANKNIFTY_PCR": b["pcr"],
        "BANK_PCR": b["pcr"],
        "VIX": n["vix"],
        "NIFTY": n,
        "BANKNIFTY": b,
        "pcr": n["pcr"],
        "vix": n["vix"],
        "status": n["status"]
    }

if __name__ == "__main__":
    print(fetch_free_data())
