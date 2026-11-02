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
        # Step 1: Get NSE cookie first (IMPORTANT)
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        time.sleep(1)
        
        # Step 2: Now fetch option chain with cookie
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        r = session.get(url, headers=headers, timeout=10)
        data = r.json()
        
        # Calculate PCR
        ce_oi = sum([x['CE']['openInterest'] for x in data['records']['data'] if 'CE' in x])
        pe_oi = sum([x['PE']['openInterest'] for x in data['records']['data'] if 'PE' in x])
        pcr = round(pe_oi/ce_oi, 2) if ce_oi else 1.0
        
        # VIX
        try:
            vix_r = session.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10)
            vix_data = vix_r.json()
            vix = next((x['last'] for x in vix_data['data'] if x['index'] == 'India VIX'), 14.5)
        except:
            vix = 14.5
            
        return {"pcr": pcr, "vix": float(vix), "status": "LIVE"}
    except Exception as e:
        # Fallback but don't crash
        return {"pcr": 1.0, "vix": 14.5, "status": f"Fallback {str(e)[:50]}"}

# Test both
if __name__ == "__main__":
    print(fetch_option_chain("NIFTY"))
    print(fetch_option_chain("BANKNIFTY"))
