import requests

def fetch_free_data():
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com",headers={"User-Agent":"Mozilla/5.0"},timeout=5)
        # Nifty Option Chain
        n=s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
                headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"},timeout=8).json()
        b=s.get("https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY",
                headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"},timeout=8).json()
        
        def parse(d):
            pcr=d['filtered']['CE']['totOI']/d['filtered']['PE']['totOI'] if d['filtered']['PE']['totOI'] else 1
            # Max pain approx
            return round(1/pcr if pcr else 1,2), pcr
        
        n_pcr_inv, n_pcr = parse(n)
        b_pcr_inv, b_pcr = parse(b)
        
        # VIX
        vix_r=s.get("https://www.nseindia.com/api/allIndices",headers={"User-Agent":"Mozilla/5.0"},timeout=5).json()
        vix=15
        for idx in vix_r['data']:
            if 'VIX' in idx['index']:
                vix=float(idx['last'])
                break
        
        return {"NIFTY_PCR":round(n_pcr,2),"BANK_PCR":round(b_pcr,2),"VIX":vix,"status":"LIVE"}
    except Exception as e:
        return {"NIFTY_PCR":1.0,"BANK_PCR":1.0,"VIX":14.5,"status":f"Fallback {e}"}
