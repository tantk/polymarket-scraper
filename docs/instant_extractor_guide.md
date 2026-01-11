# How to Use the Instant PnL Extractor

This script (`extract_react_pnl.py`) captures the **full PnL history** instantly from the page's memory, avoiding slow graph hovering.

## 1. Prerequisites
Same as the scraper:
```bash
pip install playwright
playwright install chromium
```

## 2. Basic Usage (Full Dump)
To extract the entire history to a CSV:
```bash
python extract_react_pnl.py
```
*   **Result**: `polymarket_full_history.csv` containing thousands of hourly/daily checkpoints.

## 3. Date Filtering (Custom Range)
To verify specific dates (like Jan 5 - Jan 7):
```bash
python extract_react_pnl.py --start-date 2026-01-05 --end-date 2026-01-07
```

## 4. Why is this better?
*   **Speed**: Takes ~2 seconds vs ~40 seconds.
*   **Accuracy**: Gets the raw mathematical values (e.g. `46154.355`) instead of rounded tooltip text.
*   **Completeness**: Can fetch 100% of your history in one go.

## 5. Troubleshooting
*   **"Profile not found"**: Check spelling of user address.
*   **"No PnL query found"**: Private profile or page layout changed. Use `--show-browser` to inspect.
