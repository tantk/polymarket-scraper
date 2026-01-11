import requests
import json

# PnL Subgraph
SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn"
USER = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# Block Numbers for Polygon (Approximate)
# You can find exact blocks via PolygonScan or RPC.
# Jan 10 2026 (Current-ish): Let's assume latest.
# Jan 5 2026 (Start of period): ~Block 70,000,000? 
# Note: Polygon moves fast. 40k blocks/day approx? No, 2 sec block time = 43k/day.
# Let's try to query current block first to see where we are.

def get_pnl(block=None):
    if block:
        block_arg = f", block: {{ number: {block} }}"
    else:
        block_arg = ""
        
    query = f"""
    query {{
      userPositions(where: {{ user: "{USER}" }}{block_arg}) {{
        id
        realizedPnl
        totalBought
      }}
      _meta {{
        block {{
            number
        }}
      }}
    }}
    """
    try:
        r = requests.post(SUBGRAPH_URL, json={'query': query})
        data = r.json()
        if 'errors' in data:
            print(f"Error at block {block}: {data['errors']}")
            return None, None
            
        users = data.get('data', {}).get('userPositions', [])
        meta = data.get('data', {}).get('_meta', {}).get('block', {})
        current_block = meta.get('number')
        
        total_pnl = 0.0
        for u in users:
            total_pnl += float(u['realizedPnl'])
            
        return total_pnl, current_block
    except Exception as e:
        print(f"Req error: {e}")
        return None, None

print("Fetching Current PnL...")
current_pnl, current_block = get_pnl()
print(f"Current Block: {current_block}")
print(f"Current Cumulative PnL: ${current_pnl:,.2f}")

if current_block:
    # To get the EXACT PnL for a specific time, you need the exact Block Number.
    # You can get this from PolygonScan: https://polygonscan.com/block/countdown/[TIMESTAMP]
    # Example: Jan 5 2026 00:00 UTC = Timestamp 1767571200
    
    # Found via Activity Subgraph Redemptions (via user trade history)
    # Start of period (Jan 5): ~81139400
    # End of period (Jan 7): ~81213222
    
    target_block = 81139400 # Jan 5 Anchor
    
    print(f"\n--- Demonstrating Time Travel ---")
    print(f"Target Block: {target_block}")
    
    pnl_target, _ = get_pnl(target_block)
    
    if pnl_target is not None:
        print(f"PnL at Target Block: ${pnl_target:,.2f}")
        print(f"PnL Change (Current - Target): ${current_pnl - pnl_target:,.2f}")
    else:
        print("Failed to fetch past PnL.")
