import argparse
import time
import csv
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Polymarket Positions (Active & Closed).")
    parser.add_argument("--user", type=str, default="0x8dxd", help="User Address or Profile Slug (e.g. '0x123...' or 'vitalik')")
    parser.add_argument("--limit", type=int, default=100, help="Max number of closed positions to extract.")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode.")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run in visible mode (default).")
    parser.set_defaults(headless=False)
    return parser.parse_args()

def clean_text(text):
    if not text: 
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_position_data(row_locator):
    """
    Parses a single position row locator.
    """
    try:
        full_text = row_locator.inner_text()
        
        # 1. Market Name & Link from the row
        # Locator doesn't support query_selector_all, use locator().all()
        market_links = row_locator.locator("a[href*='/event/']").all()
        market_name = "Unknown Market"
        market_url = ""
        
        # Pick the link with text (the image link usually has empty text or just image)
        for link in market_links:
            try:
                if not link.is_visible(): continue
                txt = clean_text(link.inner_text())
                if len(txt) > len(market_name) and txt != "Unknown Market":
                    market_name = txt
                    market_url = link.get_attribute("href")
                elif not market_url:
                     market_url = link.get_attribute("href")
            except: pass
                 
        if market_url and not market_url.startswith("http"):
            market_url = "https://polymarket.com" + market_url
            
        status = "Open"
        if "Won" in full_text: status = "Won"
        elif "Lost" in full_text: status = "Lost"
        
        return {
            "Market": market_name,
            "URL": market_url,
            "Status": status,
            "Raw_Text": clean_text(full_text)
        }
    except Exception as e:
        return {"Error": str(e)}

def scrape_positions(user, limit, headless=False):
    url = f"https://polymarket.com/@{user}?tab=positions"
    output_dir = os.path.join(os.getcwd(), "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"polymarket_positions_{user}_{timestamp}.csv")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            print(f"--- Starting Scraper for {user} ---")
            print(f"Target: {url}")
            print("Navigating...")
            page.goto(url, timeout=60000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=30000)
            except:
                print("Warning: Page load timeout, but continuing...")
            
            print("Waiting 5s for hydration...")
            page.wait_for_timeout(5000)

            # 1. ACTIVE POSITIONS
            print("\n--- Scraping Active Positions ---")
            active_data = []

            # 1. ACTIVE POSITIONS
            print("\n--- Scraping Active Positions ---")
            active_data = []
            processed_rows = set()
            
            # Virtualized list handling: Scrape -> Scroll -> Repeat
            consecutive_no_new_data = 0
            
            # Ensure we start at the top
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)

            while True:
                # 1. Extract visible rows using robust selector
                rows = page.locator("div.py-3.border-b").all()
                current_new_count = 0
                
                for row in rows:
                    if not row.is_visible(): continue
                    
                    # Validation
                    txt = row.inner_text() or ""
                    try:
                        has_link = row.locator("a[href*='/event/']").count() > 0
                        is_valid = ("$" in txt or "¢" in txt or ("shares" in txt and ("Up" in txt or "Down" in txt))) and has_link
                    except: is_valid = False
                    
                    if not is_valid: continue

                    row_text = clean_text(txt)
                    
                    if row_text in processed_rows: continue
                    
                    processed_rows.add(row_text)
                    data = extract_position_data(row)
                    data["Type"] = "Active"
                    active_data.append(data)
                    current_new_count += 1
                
                print(f"  Extracted {current_new_count} new active positions (Total: {len(active_data)})...")
                
                if current_new_count > 0:
                    consecutive_no_new_data = 0
                else:
                    consecutive_no_new_data += 1

                # 2. Check for "Load More" button and clicked
                # Selector based on browser agent findings for Polymarket buttons
                try:
                    button_selector = "button:has-text('Load more'), button:has-text('Show more')"
                    show_more = page.locator(button_selector).first
                    if show_more.is_visible():
                        print("Found 'Load more' button, clicking...")
                        show_more.click()
                        page.wait_for_timeout(2000)
                        consecutive_no_new_data = 0 # Reset counter if we expanded the list
                except: pass

                # 3. Scroll Down
                # Get current scroll position and height
                scroll_info = page.evaluate("""() => {
                    return {
                        scrollTop: window.scrollY,
                        windowHeight: window.innerHeight,
                        scrollHeight: document.body.scrollHeight
                    }
                }""")
                
                scrollTop = scroll_info['scrollTop']
                windowHeight = scroll_info['windowHeight']
                scrollHeight = scroll_info['scrollHeight']
                
                if scrollTop + windowHeight >= scrollHeight:
                    # We are at the bottom
                    if consecutive_no_new_data >= 3:
                        print("Result: Reached bottom and no new data found for 3 iterations.")
                        break
                    else:
                        print(f"At bottom, checking for new data/lazy load... ({consecutive_no_new_data}/3)")
                        page.wait_for_timeout(2000)
                else:
                    # Scroll down by a portion of the screen (half height to ensure no skips)
                    page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
                    page.wait_for_timeout(1000)

            print(f"Total Active positions found: {len(active_data)}")

            # 2. CLOSED POSITIONS
            print("\n--- Scraping Closed Positions ---")
            
            try:
                closed_btn = page.locator("button").filter(has_text=re.compile(r"^Closed$")).first
                if not closed_btn.is_visible():
                     closed_btn = page.locator("button").filter(has_text="Closed").first
                
                closed_btn.click()
                print("Clicked Closed tab.")
                page.wait_for_timeout(3000) 
            except Exception as e:
                print(f"Error switching to Closed tab: {e}") 

            closed_data = []
            last_count = 0
            retries = 0
            
            # Simple scrolling loop for Closed items
            while len(closed_data) < limit:
                # Use same finding logic as Active
                current_rows_data = []
                rows = page.locator("div.py-3.border-b").all()
                print(f"DEBUG: Closed Loop - Found {len(rows)} potential row elements.")
                
                temp_processed = set()
                
                for row in rows:
                    if not row.is_visible(): continue
                    
                    # Validation
                    txt = row.inner_text() or ""
                    try:
                        has_link = row.locator("a[href*='/event/']").count() > 0
                        # Strict check for Closed: Must contain Won or Lost
                        is_valid = ("Won" in txt or "Lost" in txt) and ("$" in txt or "¢" in txt) and has_link
                    except: is_valid = False
                    
                    if is_valid:
                        t = clean_text(txt)
                        if t not in processed_rows and t not in temp_processed:
                            d = extract_position_data(row)
                            d["Type"] = "Closed"
                            current_rows_data.append(d)
                            temp_processed.add(t)

                # Add new unique ones
                if not current_rows_data:
                     # No new rows found, scroll
                     pass
                else:
                    for d in current_rows_data:
                        if len(closed_data) < limit:
                            closed_data.append(d)
                            processed_rows.add(d["Raw_Text"])
                
                current_count = len(closed_data)
                
                if current_count == last_count:
                    retries += 1
                    print(f"  No new items... ({retries}/3)")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(3000)
                    if retries >= 3: break
                else:
                    retries = 0
                    print(f"  Total Closed: {current_count} (Target: {limit})")
                    last_count = current_count
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                    
            # SAVE TO CSV
            all_data = active_data + closed_data
            
            if not all_data:
                print("No data extracted.")
                return

            keys = ["User", "Type", "Market", "Status", "URL", "Raw_Text", "Scrape_Time"]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for item in all_data:
                    row_out = {
                        "User": user,
                        "Type": item.get("Type"),
                        "Market": item.get("Market"),
                        "Status": item.get("Status"),
                        "URL": item.get("URL"),
                        "Raw_Text": item.get("Raw_Text"),
                        "Scrape_Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    writer.writerow(row_out)
                    
            print(f"Success! Saved {len(all_data)} rows to {output_file}")
            
        except Exception as e:
            print(f"Critical Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    args = parse_args()
    scrape_positions(args.user, args.limit, args.headless)
