import requests
import pandas as pd
import time
import argparse
import os
from datetime import datetime

SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
USER_ADDRESS = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# Timestamps for Jan 5 2026 to Jan 6 2026 (inclusive)
# Start: Jan 5 00:00 UTC
# End: Jan 7 00:00 UTC (exclusive)
START_TS = 1767571200
END_TS = 1767744000

def fetch_page(last_ts, last_id):
    query = """
    query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!, $lastTs: BigInt!, $lastId: ID!) {
      orderFilledEvents(
        first: 1000,
        orderBy: timestamp,
        orderDirection: asc,
        where: {
          maker: $user,
          timestamp_gte: $minTs,
          timestamp_lt: $maxTs,
          and: [
            { timestamp_gte: $lastTs },
            { or: [{ timestamp_gt: $lastTs }, { id_gt: $lastId }] }
          ]
        }
      ) {
        id
        transactionHash
        timestamp
        maker
        taker
        makerAssetId
        takerAssetId
        makerAmountFilled
        takerAmountFilled
      }
    }
    """
    
    # Simplified cursor logic:
    # We sort by timestamp ASC.
    # We filter timestamp >= START_TS and timestamp < END_TS.
    # To paginate, we use (timestamp > last_ts) OR (timestamp == last_ts AND id > last_id).
    # Since GraphQL 'OR' with complex nesting can be tricky or slow, simpler is:
    # Just use timestamp_gte: last_ts.
    # And then client-side filter or use the specific 'id_gt' technique if the subgraph supports specific complex filtering.
    # Many subgraphs support `where: {timestamp_gte: $lastTs, id_gt: $lastId}` ONLY if sorted by id.
    # But we want sort by timestamp.
    
    # Robust approach: Sort by timestamp ASC.
    # where: {timestamp_gte: $lastTs}
    # Loop through results. If we get 1000 items and they ALL have the same timestamp, we are stuck.
    # But usually timestamps vary. We just track the last seen ID and Timestamp.
    
    # Let's try standard timestamp walk.
    
    q_simple = """
    query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!) {
      orderFilledEvents(
        first: 1000,
        orderBy: timestamp,
        orderDirection: asc,
        where: {
          maker: $user,
          timestamp_gte: $minTs,
          timestamp_lt: $maxTs
        }
      ) {
        id
        timestamp
        maker
        taker
        makerAssetId
        takerAssetId
        makerAmountFilled
        takerAmountFilled
      }
    }
    """
    
    variables = {
        "user": USER_ADDRESS,
        "minTs": last_ts,
        "maxTs": END_TS
    }
    
    try:
        r = requests.post(SUBGRAPH_URL, json={'query': q_simple, 'variables': variables}, timeout=30)
        data = r.json()
        if 'errors' in data:
            print("Errors:", data['errors'])
            return []
        
        events = data.get('data', {}).get('orderFilledEvents', [])
        return events
    except Exception as e:
        print(f"Request failed: {e}")
        return []

def extract_subgraph():
    print(f"Starting Subgraph Extraction for {USER_ADDRESS}")
    print(f"Time Range: {datetime.fromtimestamp(START_TS)} to {datetime.fromtimestamp(END_TS)}")
    
    current_min_ts = START_TS
    last_id_seen = ""
    
    all_events = []
    total_fetched = 0
    
    output_file = "data/raw/polymarket_jan5_jan6_raw.csv"
    
    # Initialize CSV
    columns = ["id", "timestamp", "timestamp_utc", "transactionHash", "maker", "taker", "makerAssetId", "takerAssetId", "makerAmountFilled", "takerAmountFilled"]
    df_header = pd.DataFrame(columns=columns)
    df_header.to_csv(output_file, index=False)
    
    while current_min_ts < END_TS:
        events = fetch_page(current_min_ts, last_id_seen)
        
        if not events:
            print("No more events or error.")
            break
            
        # Deduplication and processing
        # Since we query timestamp_gte, we might re-fetch the last timestamp's items.
        # We need to filter out items we've already seen if they share the same timestamp.
        # But keeping track of all IDs is expensive.
        # Better: Update current_min_ts to the LAST timestamp seen.
        # BUT, if there are multiple items with that same last timestamp, we miss them if we increment, or duplicate if we don't.
        
        # Simple Logic:
        # Filter `events` to exclude strictly those <= last_id_seen if timestamp == current_min_ts? 
        # Too complex for this snippet.
        
        # Iterative update:
        # 1. Process all events.
        # 2. Set current_min_ts = events[-1]['timestamp']
        # 3. IF events[-1]['timestamp'] == events[0]['timestamp'] (Entire page is same second),
        #    we need `id_gt` pagination.
        
        processed_batch = []
        for ev in events:
            # Skip if we strictly already processed this ID (naive check defers to 'id_gt' logic if we implemented it, 
            # but for now let's just accept potential slight overlap close to the boundary and dedup later in pandas if needed,
            # OR assume high volume timestamp doesn't span >1000 items per second often.
            # User is HF bot, so >1000/sec IS possible.
            
            # Let's rely on simple `timestamp_gt` for the NEXT page.
            # This risks MISSING items in the same second.
            # THIS IS DANGEROUS for HF bots.
            
            # Fix: We will assume we simply append everything and `drop_duplicates` at the end? 
            # No, file is too big.
            
            # Let's use the valid `id_gt` hack: 
            # Actually, `fetch_page` SHOULD handle this.
            pass

        # Let's use a simpler pagination: `skip`? No, max 5000 skip.
        # ID-based pagination is best. Sort by ID?
        # IDs are UUIDs or Hashes? "0x...-0x..." OrderFilledEvent ID is usually `txHash-logIndex`.
        # This is strictly sortable! 
        
        # NEW PLAN: Sort by `id`. Filter `timestamp` in the where clause, but paginate by `id`.
        # Much safer.
        break 

    # RESTARTING LOGIC WITH ID PAGINATION BELOW
    pass

def extract_safe():
    print("Strategy: Paginate by ID (TransactionHash-LogIndex) for stability.")
    
    last_id = ""
    total_count = 0
    output_file = "data/raw/polymarket_jan5_jan6_raw.csv"
    
     # Initialize CSV
    columns = ["id", "timestamp", "timestamp_utc", "transactionHash", "maker", "taker", "makerAssetId", "takerAssetId", "makerAmountFilled", "takerAmountFilled"]
    if not os.path.exists(output_file):
        pd.DataFrame(columns=columns).to_csv(output_file, index=False)
        
    while True:
        query = """
        query($user: Bytes!, $minTs: BigInt!, $maxTs: BigInt!, $lastId: ID!) {
          orderFilledEvents(
            first: 1000,
            orderBy: id,
            orderDirection: asc,
            where: {
              maker: $user,
              timestamp_gte: $minTs,
              timestamp_lt: $maxTs,
              id_gt: $lastId
            }
          ) {
            id
            transactionHash
            timestamp
            maker
            taker
            makerAssetId
            takerAssetId
            makerAmountFilled
            takerAmountFilled
          }
        }
        """
        
        variables = {
            "user": USER_ADDRESS,
            "minTs": START_TS,
            "maxTs": END_TS,
            "lastId": last_id
        }
        
        try:
            r = requests.post(SUBGRAPH_URL, json={'query': query, 'variables': variables}, timeout=30)
            data = r.json()
            events = data.get('data', {}).get('orderFilledEvents', [])
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
            continue
            
        if not events:
            print("Done.")
            break
            
        rows = []
        for ev in events:
            row = ev.copy()
            row['timestamp_utc'] = datetime.fromtimestamp(int(ev['timestamp'])).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(row)
            
        # Save
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(output_file, mode='a', header=False, index=False)
        
        total_count += len(events)
        last_id = events[-1]['id']
        last_ts_disp = rows[-1]['timestamp_utc']
        
        print(f"Fetched {total_count} events. Last: {last_ts_disp}")
        time.sleep(0.1)

if __name__ == "__main__":
    extract_safe()
