import requests
import json

url = "https://gamma-api.polymarket.com/markets"
params = {"limit": 1, "closed": "true"}

r = requests.get(url, params=params)
data = r.json()

print(json.dumps(data[0], indent=2))
