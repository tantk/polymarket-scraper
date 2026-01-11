import requests
from datetime import datetime

SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"

# Jan 5 00:00 UTC
START_TS = 1767571200
# Jan 7 00:00 UTC
END_TS = 1767744000

def get_block(timestamp, direction="asc"):
    # If asc, we want the first block AFTER timestamp.
    # If desc, we want the last block BEFORE timestamp.
    
    order = "asc" if direction == "asc" else "desc"
    comp = "gte" if direction == "asc" else "lt"
    
    query = f"""
    query {{
      orderFilledEvents(
        first: 1,
        orderBy: timestamp,
        orderDirection: {order},
        where: {{ timestamp_{comp}: {timestamp} }}
      ) {{
        blockNumber
        timestamp
        transactionHash
      }}
    }}
    """
    try:
        r = requests.post(SUBGRAPH_URL, json={'query': query})
        data = r.json()
        events = data.get('data', {}).get('orderFilledEvents', [])
        if events:
            return events[0]
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print(f"Finding blocks for range: {datetime.fromtimestamp(START_TS)} to {datetime.fromtimestamp(END_TS)}")

start_event = get_block(START_TS, "asc")
end_event = get_block(END_TS, "desc")

if start_event:
    print(f"Start Block (Jan 5): {start_event['blockNumber']} (at {datetime.fromtimestamp(int(start_event['timestamp']))})")
else:
    print("Could not find start block.")

if end_event:
    print(f"End Block (Jan 7): {end_event['blockNumber']} (at {datetime.fromtimestamp(int(end_event['timestamp']))})")
else:
    print("Could not find end block.")
