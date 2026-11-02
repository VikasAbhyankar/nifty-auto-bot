import requests, time
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive"
}
def fetch_option_chain(symbol="NIFTY"):
    try:
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        time.sleep(1)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = session.get(url, headers=headers, timeout=10)
        data = r.json()
        ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x])
        pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x])
        pcr = round(pe_oi/ce_oi, 2) if ce_oi else 1.0
        try:
            vix_r = session.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10)
            vix_data = vix_r.json()
            vix = next((x['last'] for x in vix_data['data'] if x['index'] == 'India VIX'), 14.5)
        except:
            vix = 14.5
        return {"pcr": pcr, "vix": float(vix), "status": "LIVE"}
    except Exception as e:
        return {"pcr": 1.0, "vix": 14.5, "status": f"Fallback {str(e)[:30]}"}

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
