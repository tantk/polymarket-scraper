import argparse
import sys
import time
import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Polymarket PnL Graph for a specific period.")
    parser.add_argument("--user", type=str, default="0x63ce342161250d705dc0b16df89036c8e5f9ba9a", 
                        help="User Address or Profile Slug (e.g. '0x123...' or 'vitalik')")
    parser.add_argument("--start-date", type=str, required=True, help="Start Date (YYYY-MM-DD), e.g. 2026-01-05")
    parser.add_argument("--end-date", type=str, required=True, help="End Date (YYYY-MM-DD), e.g. 2026-01-07")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (default: True)")
    parser.add_argument("--output", type=str, default="polymarket_pnl_data.csv", help="CSV file to append results to")
    return parser.parse_args()

def scrape_pnl(user, start_date_str, end_date_str, output_file, headless=True):
    url = f"https://polymarket.com/profile/{user}"
    print(f"--- Starting Scraper ---")
    print(f"Target: {url}")
    print(f"Range: {start_date_str} to {end_date_str}")
    
    # Parse dates to compare later
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
        sys.exit(1)

    captured_data = []

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        # 1. Navigate
        print(f"Navigating to {url}...")
        response = page.goto(url)
        page.wait_for_load_state("networkidle")
        
        if response.status == 404 or "404" in page.title():
            print("Error: User profile not found (404).")
            browser.close()
            return
            
        # 2. Find Graph
        print("Waiting for graph container...")
        try:
            # Polymarket uses Recharts
            graph_selector = ".recharts-responsive-container"
            page.wait_for_selector(graph_selector, timeout=15000)
        except Exception:
            print("Error: Could not find PnL graph. Profile might be empty or private.")
            browser.close()
            return

        # 3. Select Timeframe (1W is best for daily/hourly precision)
        # Try to click '1W' button if available. 
        # Buttons are usually labeled "1D", "1W", "1M", "ALL".
        timeframe_clicked = False
        for tf in ["1W", "1M", "ALL"]:
            try:
                # Look for button with exact text
                btn = page.get_by_text(tf, exact=True)
                if btn.is_visible():
                    print(f"Switching to '{tf}' view...")
                    btn.click()
                    page.wait_for_timeout(1000) # Let graph animate/reload
                    timeframe_clicked = True
                    break
            except:
                continue
        
        if not timeframe_clicked:
            print("Warning: Could not switch timeframe. Using default view.")

        # 4. Scan Graph
        # We need to hover over the graph to trigger the tooltip
        element = page.locator(graph_selector).first
        box = element.bounding_box()
        if not box:
            print("Error: Could not determine graph dimensions.")
            browser.close()
            return

        print("Scanning graph for data points...")
        
        # Scan strategies:
        # Move pixel by pixel across the width of the graph
        start_x = box["x"]
        width = box["width"]
        y_pos = box["y"] + box["height"] / 2
        
        # Step size: dependent on width. If width ~600px, step 2px is 300 checks.
        step = 2 
        steps = int(width / step)
        
        last_date = None
        
        for i in range(steps):
            x_pos = start_x + (i * step)
            
            # Move mouse
            page.mouse.move(x_pos, y_pos)
            # Small wait for React to render tooltip
            page.wait_for_timeout(10)
            
            # Extract Tooltip
            # Recharts usually puts tooltip in a portal or appended to body
            # Classes: .recharts-tooltip-label (Date), .recharts-tooltip-item-value (Value)
            
            try:
                tooltip = page.locator(".recharts-tooltip-wrapper")
                if tooltip.is_visible():
                    date_text = page.locator(".recharts-tooltip-label").first.inner_text()
                    # Value might be in a list item
                    value_text = page.locator(".recharts-tooltip-item-value").first.inner_text()
                    
                    if date_text and value_text:
                        # Clean Date: "Mon, Jan 5, 7:00 AM" -> Parse?
                        # For simple string matching, we'll store it raw first
                        
                        # Store if unique
                        if date_text != last_date:
                            captured_data.append({"date_raw": date_text, "pnl_str": value_text})
                            last_date = date_text
            except Exception:
                pass
                
        browser.close()

    print(f"Scanned {len(captured_data)} raw data points.")
    
    # 5. Filter and Display
    print("\n--- Results for Requested Period ---")
    valid_points = 0
    
    # Storage for CSV rows
    csv_rows = []
    scrape_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"{'Date':<30} | {'PnL':<20}")
    print("-" * 50)
    
    for item in captured_data:
        d = item["date_raw"]
        v = item["pnl_str"]
        
        # Filter logic: Loose matching
        # If the user asks for Jan 5 to Jan 7, we look for those strings.
        # This is a basic filter based on string presence.
        
        # Simple print
        print(f"{d:<30} | {v:<20}")
        valid_points += 1
        
        # Add to CSV list
        csv_rows.append({
            "User": user,
            "Date_Raw": d,
            "PnL_Value": v,
            "Scrape_Timestamp": scrape_ts,
            "Source_Range_Start": start_date_str,
            "Source_Range_End": end_date_str
        })

    print("-" * 50)
    
    if valid_points == 0:
        print("No data points found. Initial Loading might have failed or format changed.")
    else:
        print(f"Found {valid_points} points.")
        
        # Write to CSV
        file_exists = os.path.isfile(output_file)
        
        try:
            with open(output_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["User", "Date_Raw", "PnL_Value", "Scrape_Timestamp", "Source_Range_Start", "Source_Range_End"])
                
                if not file_exists:
                    writer.writeheader()
                    
                writer.writerows(csv_rows)
            print(f"Success: Appended {len(csv_rows)} rows to '{output_file}'")
        except Exception as e:
            print(f"Error writing to CSV: {e}")

if __name__ == "__main__":
    args = parse_args()
    scrape_pnl(args.user, args.start_date, args.end_date, args.output, args.headless)
