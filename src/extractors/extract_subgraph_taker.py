import requests
import pandas as pd
import time
import argparse
import os
from datetime import datetime

SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
USER_ADDRESS = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

# Jan 5 - Jan 6 (Same range)
START_TS = 1767571200
END_TS = 1767744000

def extract_taker():
    print("Starting Taker Extraction...")
    
    last_id = ""
    total_count = 0
    output_file = "data/interim/polymarket_jan5_jan6_taker.csv"
    
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
              taker: $user,
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
            
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(output_file, mode='a', header=False, index=False)
        
        total_count += len(events)
        last_id = events[-1]['id']
        last_ts_disp = rows[-1]['timestamp_utc']
        
        print(f"Fetched {total_count} Taker events. Last: {last_ts_disp}")
        time.sleep(0.1)

if __name__ == "__main__":
    extract_taker()
