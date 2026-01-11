import argparse
import sys
import json
import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def parse_args():
    parser = argparse.ArgumentParser(description="Instantly extract full PnL history from Polymarket internals.")
    parser.add_argument("--user", type=str, default="0x63ce342161250d705dc0b16df89036c8e5f9ba9a", 
                        help="User Address or Profile Slug")
    parser.add_argument("--start-date", type=str, help="Filter Start Date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Filter End Date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="data/final/polymarket_full_history.csv", help="CSV Output file")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--show-browser", action="store_false", dest="headless", help="Show browser")
    return parser.parse_args()

def extract_pnl_json(user, output_file, start_date=None, end_date=None, headless=True):
    url = f"https://polymarket.com/profile/{user}"
    print(f"--- Starting Instant Extractor ---")
    print(f"Target: {url}")
    
    # Parse date filters if provided
    min_ts = 0
    max_ts = 9999999999
    
    if start_date:
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            min_ts = dt.timestamp()
            print(f"Filter Start: {start_date} ({min_ts})")
        except ValueError:
            print("Error: Invalid Start Date format. Use YYYY-MM-DD")
            sys.exit(1)
            
    if end_date:
        try:
            # End of the day for end_date
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Create a timestamp for 23:59:59 of that day approx, or just strict comparison
            # Let's add 24 hours to include the full day
            max_ts = dt.timestamp() + 86400
            print(f"Filter End: {end_date} ({max_ts})")
        except ValueError:
            print("Error: Invalid End Date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    data_points = []
    
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        print(f"Navigating to {url}...")
        response = page.goto(url)
        page.wait_for_load_state("networkidle")
        
        if response.status == 404:
            print("Error: Profile not found.")
            browser.close()
            return

        print("Page loaded. Extracting __NEXT_DATA__...")
        
        # This is the "Magic" - extracting the pre-loaded JSON state
        try:
            result = page.evaluate("""() => {
                if (!window.__NEXT_DATA__) return null;
                try {
                    return window.__NEXT_DATA__.props.pageProps.dehydratedState.queries;
                } catch(e) { return null; }
            }""")
            
            if not result:
                print("Error: Could not find PnL data in global state.")
                browser.close()
                return
                
            # Find the correct query key
            pnl_query = None
            
            # Use 'ALL' if available to get max history, otherwise largest available
            for q in result:
                key = q.get('queryKey', [])
                if key and key[0] == 'portfolio-pnl':
                    timeframe = key[3] if len(key) > 3 else "UNKNOWN"
                    print(f"Found PnL Dataset: {timeframe} with {len(q['state']['data'])} points")
                    
                    if timeframe == "ALL":
                        pnl_query = q
                        break
                    elif timeframe == "1M" and (not pnl_query or pnl_query['queryKey'][3] != "ALL"):
                         pnl_query = q
                    elif not pnl_query:
                         pnl_query = q
            
            if pnl_query:
                raw_data = pnl_query['state']['data']
                print(f"Selected Dataset: {pnl_query['queryKey'][3]} ({len(raw_data)} points)")
                
                # Transform data
                for pt in raw_data:
                    ts = pt.get('t')
                    val = pt.get('p')
                    
                    if ts and val is not None:
                        # Apply Filters
                        if ts < min_ts or ts > max_ts:
                            continue
                            
                        dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        data_points.append({
                            "Timestamp": ts,
                            "Date_Readable": dt_str,
                            "PnL_Value": val,
                            "User": user
                        })
            else:
                print("Warning: No 'portfolio-pnl' query found in state. Profile might be private/empty.")
                
        except Exception as e:
            print(f"Extraction Error: {e}")
            
        browser.close()

    print(f"Extracted {len(data_points)} matching data points.")
    
    if data_points:
        import csv
        # Check if file exists to append header only if needed? 
        # For 'full history' dumps, overwrite is usually safer unless specified.
        # But let's append if file exists to match previous scraper behavior?
        # Actually for 'instant full history', it's cleaner to overwrite or start fresh.
        # But user asked for "same saving to csv feature". 
        # I'll stick to 'w' (overwrite) for now to ensure clean history dumps, 
        # or 'a' (append) if that's crucial.
        # Let's do 'a' (append) but check for header.
        
        file_exists = os.path.isfile(output_file)
        keys = ["Timestamp", "Date_Readable", "PnL_Value", "User"]
        
        try:
            with open(output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(data_points)
                
            print(f"Success: Saved {len(data_points)} rows to '{output_file}'")
        except Exception as e:
            print(f"File Write Error: {e}")

if __name__ == "__main__":
    args = parse_args()
    extract_pnl_json(args.user, args.output, args.start_date, args.end_date, args.headless)
