import requests
import json

url = "https://gamma-api.polymarket.com/markets"
params = {"limit": 5, "closed": "true"}

try:
    r = requests.get(url, params=params)
    data = r.json()
    
    for m in data:
        # Check for potential winning fields
        keys = m.keys()
        print(f"Keys: {list(keys)}")
        
        # Check specific values
        for k in ["outcome", "winner", "resolution", "payout", "winningOutcome"]:
            if k in m:
                print(f"  FOUND {k}: {m[k]}")
                
        # Dig into nested?
        if "question" in m:
             print(f"  Question keys: {m['question'].keys() if isinstance(m['question'], dict) else 'Not Dict'}")
             
        break # Just one
except Exception as e:
    print(e)
