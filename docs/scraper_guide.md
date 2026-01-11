# How to Use the Polymarket PnL Scraper

This script (`scrape_polymarket_pnl.py`) allows you to extract historical Profit & Loss (PnL) data directly from a Polymarket user profile graph.

## 1. Prerequisites (Installation)

The script uses **Playwright**, a powerful browser automation tool. You need to install it and its browser drivers.

Run these commands in your terminal:

```bash
# Install Python library
pip install playwright

# Install browser binaries (Chromium)
playwright install chromium
```

## 2. Running the Scraper

The script is a command-line tool. You can specify the user, dates, and whether to show the browser.

### Basic Usage (Jan 5 - Jan 7)
```bash
python scrape_polymarket_pnl.py --start-date 2026-01-05 --end-date 2026-01-07
```

### Specifying a Different User
You can scrape any user by their Wallet Address or Profile Username.
```bash
python scrape_polymarket_pnl.py --user 0x8dxd --start-date 2026-01-01 --end-date 2026-01-10
# OR
python scrape_polymarket_pnl.py --user 0x123...abc --start-date 2026-01-01 --end-date 2026-01-10
```

### Visual Mode (Watch the Browser)
To see what the bot is doing (useful for debugging or just watching it scan), remove the headless flag:
```bash
# The script defaults to headless=True. 
# To SHOW the browser, enable the flag (depending on implementation):
python scrape_polymarket_pnl.py --show-browser
```

### Saving to CSV
By default, the script appends results to `polymarket_pnl_data.csv`.
You can specify a custom file:
```bash
python scrape_polymarket_pnl.py --output my_pnl_history.csv --start-date ...
```
The CSV includes: User, Date, PnL Value, and Scrape Timestamp.

## 3. Troubleshooting

*   **"User not found"**: Double-check the wallet address or username.
*   **"Could not find PnL graph"**: The profile might be private, empty, or the page took too long to load. Try running with `--show-browser` to see what happened.
*   **Empty Results**: If no data points are found, try widening the date range slightly or checking if the "1W" button was successfully clicked (visible in `--show-browser` mode).
