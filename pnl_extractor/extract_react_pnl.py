import os
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

# Setup Logger
log_file = os.path.join(os.path.dirname(__file__), 'extraction.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

import argparse
import sys
import json
import csv
import os
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

# Setup Logger
log_file = os.path.join(os.path.dirname(__file__), 'extraction.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_args():
    parser = argparse.ArgumentParser(description="Instantly extract PnL history from Polymarket.")
    
    # Input group: Single User OR File
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--user", type=str, help="Single User Address, Slug, or Profile URL")
    group.add_argument("--input-file", type=str, help="Path to file (CSV, JSON, TXT) containing users/links")
    
    parser.add_argument("--start-date", type=str, help="Filter Start Date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Filter End Date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="polymarket_full_history.csv", help="CSV Output file")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--show-browser", action="store_false", dest="headless", help="Show browser")
    return parser.parse_args()

def normalize_user(input_str):
    """Extracts username/address from full URL or returns raw string."""
    if not input_str:
        return None
    s = input_str.strip()
    
    # Handle Full URLs
    if "polymarket.com" in s:
        if "/@" in s:
            return s.split("/@")[-1].split("/")[0]
        if "/profile/" in s:
            return s.split("/profile/")[-1].split("/")[0]
            
    # Handle raw input being just an address or slug
    return s.strip("/")

def load_users_from_file(filepath):
    users = []
    if not os.path.exists(filepath):
        logging.error(f"Input file not found: {filepath}")
        return []
    
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if ext == '.json':
                data = json.load(f)
                # Handle list of strings or list of objects
                for item in data:
                    if isinstance(item, str):
                        users.append(item)
                    elif isinstance(item, dict) and 'user' in item:
                        users.append(item['user'])
                    elif isinstance(item, dict) and 'link' in item:
                         users.append(item['link'])
            elif ext == '.csv':
                reader = csv.reader(f)
                for row in reader:
                    if row: 
                        users.append(row[0]) # Assume first column is user/link
            else: # TXT (one per line)
                for line in f:
                    if line.strip():
                        users.append(line.strip())
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        
    return [normalize_user(u) for u in users if u]

def fetch_user_data(page, user):
    """Navigates to profile and extracts PnL data."""
    # Polymarket uses /@identifier for profiles now
    url = f"https://polymarket.com/@{user}"
    logging.info(f"Processing user: {user}")
    print(f"  > Fetching: {user} ({url})")
    
    try:
        # Relaxed wait condition: 'domcontentloaded' is usually enough for __NEXT_DATA__
        response = page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        
        if response.status == 404:
            logging.warning(f"User not found: {user}")
            print("    Error: 404 Not Found")
            return []

        # Extract JSON from __NEXT_DATA__
        result = page.evaluate("""() => {
            if (!window.__NEXT_DATA__) return null;
            try {
                return window.__NEXT_DATA__.props.pageProps.dehydratedState.queries;
            } catch(e) { return null; }
        }""")
        
        if not result:
            logging.warning(f"No global state found for {user}. Page might not be fully loaded.")
            print("    Warning: No data found in page state.")
            return []
            
        # Find PnL Queries
        pnl_queries = []
        for q in result:
            key = q.get('queryKey', [])
            if key and key[0] == 'portfolio-pnl':
                timeframe = key[3] if len(key) > 3 else "UNKNOWN"
                count = len(q.get('state', {}).get('data', []) or [])
                logging.info(f"Found dataset: {timeframe} with {count} points")
                pnl_queries.append({'q': q, 'tf': timeframe})

        if not pnl_queries:
            logging.warning(f"No 'portfolio-pnl' queries found for {user}")
            print("    Warning: No PnL history found (Profile might be private/empty).")

        extracted_rows = []
        
        for item in pnl_queries:
            q = item['q']
            tf = item['tf']
            raw_data = q.get('state', {}).get('data', [])
            
            if not raw_data:
                continue

            for pt in raw_data:
                ts = pt.get('t')
                val = pt.get('p')
                if ts and val is not None:
                     extracted_rows.append({
                        "Timestamp": ts,
                        "PnL_Value": val,
                        "User": user,
                        "Timeframe": tf
                    })
        
        return extracted_rows

    except Exception as e:
        logging.error(f"Extraction failed for {user}: {e}")
        print(f"    Error: {e}")
        return []

def main():
    try:
        args = parse_args()
        
        # 1. Build User List
        target_users = []
        if args.user:
            target_users.append(normalize_user(args.user))
        if args.input_file:
            target_users.extend(load_users_from_file(args.input_file))
            
        # Deduplicate while preserving order
        target_users = list(dict.fromkeys(target_users))
        
        if not target_users:
            print("No users specified. Use --user or --input-file.")
            return

        print(f"--- Starting Bulk Extraction ({len(target_users)} users) ---")
        
        # 2. Date Filtering Setup
        min_ts = 0
        max_ts = 9999999999
        if args.start_date:
            min_ts = datetime.strptime(args.start_date, "%Y-%m-%d").timestamp()
        if args.end_date:
            max_ts = datetime.strptime(args.end_date, "%Y-%m-%d").timestamp() + 86400

        # 3. Output Setup
        file_exists = os.path.isfile(args.output)
        keys = ["Timestamp", "Date_Readable", "PnL_Value", "User", "Timeframe", "Scrape_Time"]
        
        total_saved = 0
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=args.headless)
            page = browser.new_page()
            
            # Open CSV in append mode
            with open(args.output, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                if not file_exists:
                    writer.writeheader()
                    
                for user in target_users:
                    rows = fetch_user_data(page, user)
                    
                    # Filter and Enrich
                    cleaned_rows = []
                    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    for r in rows:
                        t = r['Timestamp']
                        if t < min_ts or t > max_ts:
                            continue
                        
                        r['Date_Readable'] = datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
                        r['Scrape_Time'] = scrape_time
                        cleaned_rows.append(r)
                    
                    if cleaned_rows:
                        writer.writerows(cleaned_rows)
                        total_saved += len(cleaned_rows)
                        print(f"    Saved {len(cleaned_rows)} rows.")
                    
            browser.close()
            
        print(f"Done. {total_saved} total rows saved to '{args.output}'.")
        logging.info(f"Batch complete. Users: {len(target_users)}, Rows: {total_saved}")

    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
