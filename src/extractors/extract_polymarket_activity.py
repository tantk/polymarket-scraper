import requests
import pandas as pd
import argparse
import time
import json
import os
import signal
import sys
import logging
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
API_URL = "https://data-api.polymarket.com/activity"
USER_ADDRESS = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"
POLYGON_RPC = "https://polygon-rpc.com"
DEFAULT_DATE_LIMIT = "2025-12-01"

# Global flag for graceful exit
running = True

def setup_logger(log_file="extraction.log"):
    """Sets up a logger that writes to both file and console."""
    logger = logging.getLogger("PolymarketExtractor")
    logger.setLevel(logging.INFO)
    
    # File Handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(message)s')
    ch.setFormatter(ch_formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def signal_handler(sig, frame):
    global running
    print("\nGracefully exiting...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def create_session():
    """Creates a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    return session

def get_block_number(session, tx_hash):
    """Fetches block number for a transaction hash using Polygon RPC."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionReceipt",
        "params": [tx_hash],
        "id": 1
    }
    try:
        response = session.post(POLYGON_RPC, json=payload, timeout=5)
        data = response.json()
        if 'result' in data and data['result']:
            return int(data['result']['blockNumber'], 16)
    except Exception:
        return None
    return None

def process_trade(trade, fetch_blocks, session):
    timestamp = trade.get("timestamp")
    dt_object = datetime.fromtimestamp(timestamp)
    
    row = {
        "timestamp_unix": timestamp,
        "timestamp_utc": dt_object.strftime("%Y-%m-%d %H:%M:%S"),
        "market_title": trade.get("title"),
        "market_slug": trade.get("slug"),
        "outcome": trade.get("outcome"),
        "side": trade.get("side"),
        "price": trade.get("price"),
        "size": trade.get("size"),
        "usdc_size": trade.get("usdcSize"),
        "transaction_hash": trade.get("transactionHash"),
        "asset_id": trade.get("asset"),
        "condition_id": trade.get("conditionId"),
        "pseudonym": trade.get("pseudonym"),
        "raw_json": json.dumps(trade),
        "block_number": ""
    }
    
    if fetch_blocks:
        row['block_number'] = get_block_number(session, row['transaction_hash'])
        
    return row

def fetch_activity(args, logger):
    logger.info(f"Starting extraction for {USER_ADDRESS}")
    logger.info(f"Date Limit: {args.date_limit}")
    logger.info(f"Fetch Blocks: {args.fetch_blocks}")
    
    session = create_session()
    
    limit = 100
    offset = args.offset # Resume support
    total_fetched = 0
    
    date_limit_ts = datetime.strptime(args.date_limit, "%Y-%m-%d").timestamp()
    
    # Initialize CSV header logic
    file_exists = os.path.exists(args.output)
    write_header = not file_exists or args.overwrite
    
    if args.overwrite and file_exists:
        logger.info(f"Overwriting existing file: {args.output}")
        os.remove(args.output)
        write_header = True
    elif file_exists:
        logger.info(f"Appending to existing file: {args.output}")

    columns = ["timestamp_unix", "timestamp_utc", "market_title", "market_slug", "outcome", "side", "price", "size", "usdc_size", "transaction_hash", "asset_id", "condition_id", "pseudonym", "block_number", "raw_json"]

    start_time = time.time()
    
    while running:
        params = {
            "user": USER_ADDRESS,
            "limit": limit,
            "offset": offset
        }
        
        try:
            response = session.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            activities = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request failed at offset {offset}: {e}")
            # With exponential backoff in session, if we get here, it's serious.
            # Convert to a hard failure or long sleep?
            # Let's sleep and try again loop
            time.sleep(10)
            continue
            
        if not activities:
            logger.info("No more activities returned by API.")
            break
        
        trades = [a for a in activities if a.get("type") == "TRADE"]
        processed_rows = []

        reached_limit = False
        current_batch_min_ts = None
        
        for trade in trades:
            ts = trade.get("timestamp")
            current_batch_min_ts = ts
            
            # Check date limit
            if ts < date_limit_ts:
                logger.info(f"Reached date limit ({args.date_limit}). Stopping.")
                reached_limit = True
                break

            processed_rows.append(process_trade(trade, args.fetch_blocks, session))
            total_fetched += 1
            
            if args.max_items and total_fetched >= args.max_items:
                logger.info(f"Reached max items limit ({args.max_items}). Stopping.")
                reached_limit = True
                break
        
        # Save batch
        if processed_rows:
            df = pd.DataFrame(processed_rows, columns=columns)
            df.to_csv(args.output, mode='a', header=write_header, index=False)
            write_header = False 
            
        # Logging progress
        if offset % 1000 == 0 or reached_limit:
            elapsed = time.time() - start_time
            rate = total_fetched / elapsed if elapsed > 0 else 0
            last_date_str = datetime.fromtimestamp(current_batch_min_ts).strftime("%Y-%m-%d %H:%M:%S") if current_batch_min_ts else "N/A"
            logger.info(f"Saved {total_fetched} trades. Offset: {offset}. Last Date: {last_date_str}. Rate: {rate:.1f} trades/sec")

        if reached_limit:
            break

        offset += limit
        # Dynamic sleep? 
        # API limit is reasonable, 0.1s sleep is ~10 req/s.  
        # Be slightly gentler for long runs.
        time.sleep(0.15) 

    logger.info(f"Finished extraction. Total items saved: {total_fetched}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Polymarket user trades.")
    parser.add_argument("--fetch-blocks", action="store_true", help="Fetch block numbers from RPC (SLOW).")
    parser.add_argument("--output", default="data/raw/polymarket_user_transactions.csv", help="Output filename.")
    parser.add_argument("--date-limit", default=DEFAULT_DATE_LIMIT, help="Stop reaching this date (YYYY-MM-DD).")
    parser.add_argument("--max-items", type=int, default=0, help="Max items to fetch (0 for no limit).")
    parser.add_argument("--offset", type=int, default=0, help="Start offset (for resuming).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing file.")
    
    args = parser.parse_args()
    
    logger = setup_logger()
    fetch_activity(args, logger)
