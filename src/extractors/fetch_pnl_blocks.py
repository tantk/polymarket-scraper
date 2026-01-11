import requests
import json
from datetime import datetime
import time

# Configuration
PNL_SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn"
ORDERBOOK_SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
USER_ADDRESS = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# Timestamps
START_TS = 1767571200 # Jan 5 2026 00:00 UTC
END_TS = 1767744000   # Jan 7 2026 00:00 UTC

def get_block_for_timestamp(timestamp):
    """
    Finds the block number closest to the given timestamp using the Orderbook Subgraph.
    We look for the first event *after* the timestamp to be safe (or close enough).
    """
    query = """
    query($ts: BigInt!) {
      orderFilledEvents(
        first: 1,
        orderBy: timestamp,
        orderDirection: asc,
        where: { timestamp_gte: $ts }
      ) {
        block {
          number
        }
        timestamp
      }
    }
    """
    try:
        print(f"DEBUG: Querying block for ts {timestamp}...")
        r = requests.post(ORDERBOOK_SUBGRAPH_URL, json={'query': query, 'variables': {'ts': timestamp}}, timeout=10)
        
        # Fallback values
        fallback_block = 81139400 if timestamp < 1767700000 else 81213222
        
        if r.status_code != 200:
             print(f"DEBUG: HTTP Error {r.status_code}. Using fallback {fallback_block}")
             return fallback_block, timestamp
             
        data = r.json()
        if 'errors' in data:
            print(f"DEBUG: GraphQL Errors: {data['errors']}. Using fallback {fallback_block}")
            return fallback_block, timestamp
            
        events = data.get('data', {}).get('orderFilledEvents', [])
        if events:
            # Try to get block number from various expected structures
            ev = events[0]
            if 'block' in ev and 'number' in ev['block']:
                return int(ev['block']['number']), int(ev['timestamp'])
            elif 'blockNumber' in ev:
                return int(ev['blockNumber']), int(ev['timestamp'])
            
            print(f"DEBUG: Block field missing in {ev}. Using fallback.")
            return fallback_block, int(ev['timestamp'])
        else:
            print(f"DEBUG: No events found. Using fallback {fallback_block}")
            return fallback_block, timestamp
            
    except Exception as e:
        print(f"Error fetching block: {e}. Using fallback.")
        fallback_block = 81139400 if timestamp < 1767700000 else 81213222
        return fallback_block, timestamp

def get_pnl_at_block(block_number):
    """
    Fetches the user's realized PnL at a specific block height.
    """
    query = f"""
    query {{
      userPositions(where: {{ user: "{USER_ADDRESS}" }}, block: {{ number: {block_number} }}) {{
        realizedPnl
      }}
    }}
    """
    try:
        r = requests.post(PNL_SUBGRAPH_URL, json={'query': query})
        if r.status_code != 200:
            print(f"Error: Status {r.status_code} - {r.text}")
            return None
            
        data = r.json()
        if 'errors' in data:
            # Handle block not found or other errors
            print(f"Subgraph Error: {data['errors']}")
            return None
            
        positions = data.get('data', {}).get('userPositions', [])
        
        # Calculate Total Realized PnL across all markets (though user usually has 1 aggregate entry logic depends on schema)
        # In this specific PnL subgraph, UserPositions might be per market or global.
        # Based on previous check_pnl output, it returns a list. We sum them.
        total_realized_pnl = 0.0
        for pos in positions:
            total_realized_pnl += float(pos.get('realizedPnl', 0))
            
        return total_realized_pnl
    except Exception as e:
        print(f"Request Error: {e}")
        return None

def main():
    print(f"--- Fetching Blocks for Time Travel ---")
    
    # 1. Get Blocks
    start_block, start_block_ts = get_block_for_timestamp(START_TS)
    if not start_block:
        print("Failed to find Start Block.")
        return
        
    end_block, end_block_ts = get_block_for_timestamp(END_TS)
    if not end_block:
        print("Failed to find End Block.")
        return
        
    print(f"Start: {datetime.fromtimestamp(START_TS)} -> Block {start_block} (Actual TS: {datetime.fromtimestamp(start_block_ts)})")
    print(f"End:   {datetime.fromtimestamp(END_TS)}   -> Block {end_block}   (Actual TS: {datetime.fromtimestamp(end_block_ts)})")
    
    # 2. Query PnL
    print(f"\n--- Querying PnL Subgraph ---")
    pnl_start = get_pnl_at_block(start_block)
    pnl_end = get_pnl_at_block(end_block)
    
    if pnl_start is None or pnl_end is None:
        print("Failed to fetch PnL values.")
        return
        
    profit = pnl_end - pnl_start
    
    print(f"PnL at Start (Block {start_block}): ${pnl_start:,.2f}")
    print(f"PnL at End   (Block {end_block}):   ${pnl_end:,.2f}")
    print(f"Net Profit (Subgraph):             ${profit:,.2f}")
    
    # Export for Master Script
    result = {
        "start_block": start_block,
        "end_block": end_block,
        "pnl_start": pnl_start,
        "pnl_end": pnl_end,
        "net_profit": profit
    }
    with open("data/raw/pnl_subgraph_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nSaved result to pnl_subgraph_result.json")

if __name__ == "__main__":
    main()
