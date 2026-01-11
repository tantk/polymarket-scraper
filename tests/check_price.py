import requests

# Token ID from enriched CSV (Bitcoin Up/Down Jan 5)
TOKEN_ID = "97309601198998981373371956202495470768918830865913622025564392184226538342767"

# Try Ticker
URL_TICKER = f"https://clob.polymarket.com/ticker?token_id={TOKEN_ID}"
# Try Price
URL_PRICE = f"https://clob.polymarket.com/price?token_id={TOKEN_ID}"

print(f"Checking Token: {TOKEN_ID}")

try:
    print("--- Ticker ---")
    r = requests.get(URL_TICKER)
    print(r.text)
    
    print("\n--- Price ---")
    r = requests.get(URL_PRICE)
    print(r.text)
except Exception as e:
    print(e)
