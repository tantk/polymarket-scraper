import requests
import json

url = "https://gamma-api.polymarket.com/events"
params = {"limit": 1, "closed": "true"}

try:
    r = requests.get(url, params=params)
    data = r.json()
    
    for m in data:
        if "tokens" in m:
             print(f"TOKENS: {json.dumps(m['tokens'], indent=2)}")
        if "outcomes" in m:
             print(f"OUTCOMES: {m['outcomes']}")
        print(f"CLOSED: {m.get('closed')}")
             
        break # Just one
except Exception as e:
    print(e)
