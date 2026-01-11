import requests
import json

# Activity Subgraph (from extract_redemptions.py)
SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"

# A known condition ID from the previous JSON dump (found in asset_map.json or similar)
# Let's pick one from asset_map.json? I don't have one handy.
# I'll query redemptions first to get a valid condition ID, then query that condition.

query_red = """
{
  redemptions(first: 1) {
    condition {
      id
    }
  }
}
"""

try:
    print("Fetching valid condition ID...")
    r = requests.post(SUBGRAPH_URL, json={'query': query_red})
    data = r.json()
    print(f"Response: {json.dumps(data, indent=2)[:500]}") # Peek
    
    if 'errors' in data:
        print("Subgraph returned errors.")
        exit()
        
    cond_id = data['data']['redemptions'][0]['condition']
    # If it is a dict (some subgraphs), handle it. If str, use it.
    if isinstance(cond_id, dict):
        cond_id = cond_id['id']
    print(f"Condition ID: {cond_id}")
    
    # Now query the condition for payouts
    query_cond = f"""
    {{
      condition(id: "{cond_id}") {{
        id
        payoutNumerators
        oracle
      }}
    }}
    """
    print("Querying condition...")
    r2 = requests.post(SUBGRAPH_URL, json={'query': query_cond})
    print(json.dumps(r2.json(), indent=2))
    
    # Try Gnosis Subgraph URL as fallback
    GNOSIS_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/gnosis-conditional-tokens/1.0.0/gn"
    print("\nAttempting Gnosis Subgraph...")
    r3 = requests.post(GNOSIS_URL, json={'query': query_cond})
    print(f"Gnosis Response: {r3.status_code}")
    if r3.status_code == 200:
        print(json.dumps(r3.json(), indent=2))
        
except Exception as e:
    print(f"Error: {e}")
