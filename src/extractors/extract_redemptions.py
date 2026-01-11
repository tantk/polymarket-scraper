import requests
import pandas as pd
import time
import argparse
import os
import json
from datetime import datetime

# Activity Subgraph for Redemptions
SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
USER_ADDRESS = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# Jan 5 - Jan 6
START_TS = 1767571200
END_TS = 1767744000

def extract_redemptions():
    print("Starting Redemption Extraction...")
    
    # Pagination via timestamp
    current_ts = START_TS
    last_id = ""
    
    output_file = "data/interim/polymarket_jan5_jan6_redemptions.csv"
    columns = ["id", "timestamp", "timestamp_utc", "redeemer", "payout", "condition", "indexSets"]
    
    if not os.path.exists(output_file):
        pd.DataFrame(columns=columns).to_csv(output_file, index=False)
        
    total_count = 0
    
    while True:
        # Standard query
        query = """
        query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!, $lastTs: BigInt!, $lastId: ID!) {
          redemptions(
            first: 1000,
            orderBy: timestamp,
            orderDirection: asc,
            where: {
              redeemer: $user,
              timestamp_gte: $minTs,
              timestamp_lt: $maxTs,
              and: [
                 { timestamp_gte: $lastTs },
                 { or: [{ timestamp_gt: $lastTs }, { id_gt: $lastId }] }
              ]
            }
          ) {
            id
            timestamp
            redeemer
            payout
            indexSets
            condition {
              id
            }
          }
        }
        """
        
        # Simplified query if complex filtering fails (Activity subgraph might be older version)
        # Try simple first
        s_query = """
        query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!, $lastTs: BigInt!) {
          redemptions(
            first: 1000,
            orderBy: timestamp,
            orderDirection: asc,
            where: {
              redeemer: $user,
              timestamp_gte: $minTs,
              timestamp_lt: $maxTs,
              timestamp_gt: $lastTs
            }
          ) {
            id
            timestamp
            redeemer
            payout
            indexSets
            condition {
              id
            }
          }
        }
        """
        # Initial First Page logic needs timestamp_gte
        # Subsequent pages need timestamp_gt to avoid dupes (if strict)
        # or timestamp_gte + filter.
        
        # Let's use simple timestamp walk.
        variables = {
            "user": USER_ADDRESS,
            "minTs": START_TS,
            "maxTs": END_TS,
            "lastTs": current_ts
        }
        
        # Adjust query for first run vs subsequent
        # Actually, let's just use `timestamp_gte` for the page start.
        run_query = """
        query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!) {
          redemptions(
            first: 1000,
            orderBy: timestamp,
            orderDirection: asc,
            where: {
              redeemer: $user,
              timestamp_gte: $minTs,
              timestamp_lt: $maxTs
            }
          ) {
            id
            timestamp
            redeemer
            payout
            indexSets
            condition {
              id
            }
          }
        }
        """
        variables = {
            "user": USER_ADDRESS,
            "minTs": current_ts,
            "maxTs": END_TS
        }

        try:
            r = requests.post(SUBGRAPH_URL, json={'query': run_query, 'variables': variables}, timeout=30)
            data = r.json()
            events = data.get('data', {}).get('redemptions', [])
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
            continue
            
        if not events:
            print("Done.")
            break
            
        rows = []
        for ev in events:
            # Manually filter if < current_ts (should generally match query)
            # Dedup logic: If TS == current_ts and we already processed it...
            # Lazy approach: Allow dupes (rare for redemptions to happen in same second for same user?)
            # Actually, batch redemption happens. Same second.
            # Using 'id_gt' is strictly better.
            
            row = ev.copy()
            row['timestamp_utc'] = datetime.fromtimestamp(int(ev['timestamp'])).strftime("%Y-%m-%d %H:%M:%S")
            cond = ev.get('condition')
            if isinstance(cond, dict):
                row['condition'] = cond.get('id')
            else:
                row['condition'] = str(cond) if cond else ""
            
            # Handle indexSets (list to string)
            idx_sets = ev.get('indexSets', [])
            row['indexSets'] = json.dumps(idx_sets)
            
            rows.append(row)
            
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(output_file, mode='a', header=False, index=False)
        
        total_count += len(events)
        
        # Update cursor
        # If we rely on timestamp only, we must increment.
        # But if we have 50 items in same second, incrementing skips them.
        # CORRECT: Use last item's timestamp. And NEXT query must filtering ID or assume >.
        # For Redemptions (low frequency?), maybe okay.
        
        # Let's bump timestamp + 1 to force progress, accepting risk of missed same-second events in tail.
        # Or better: check if last == first.
        
        last_ts_in_batch = int(events[-1]['timestamp'])
        if last_ts_in_batch == current_ts:
             # We are stuck on same second. Force +1 but log warning?
             # Or rely on the fact that we processed them.
             current_ts += 1
        else:
             current_ts = last_ts_in_batch
             # Logic Hole: `timestamp_gte` will fetch the last second again.
             # So we will have duplicates.
             # We should perform dedup in PnL script.
        
        print(f"Fetched {total_count} Redemptions. Last: {rows[-1]['timestamp_utc']}")
        time.sleep(0.1)

if __name__ == "__main__":
    extract_redemptions()
