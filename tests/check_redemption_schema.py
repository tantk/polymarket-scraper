import requests
import json

SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"

query = """
{
  redemptions(first: 5) {
    id
    payout
    indexSets
    condition {
      id
    }
  }
}
"""

try:
    print("Testing indexSets field...")
    r = requests.post(SUBGRAPH_URL, json={'query': query})
    print(r.status_code)
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(e)
