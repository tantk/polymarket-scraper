# How to Use the Instant PnL Extractor

This script (`extract_react_pnl.py`) captures the **full PnL history** instantly from the page's memory, avoiding slow graph hovering.

## 1. Prerequisites
Same as the scraper:
```bash
pip install playwright
playwright install chromium
```

## 2. Basic Usage
### Mode A: Single User (or Link)
Extract for one profile (you can paste the full URL):
```bash
python extract_react_pnl.py --user https://polymarket.com/profile/0x8dxd
```

### Mode B: Batch File (Cron Job)
Extract for many users from a text/csv/json file:
```bash
python extract_react_pnl.py --input-file users_list.txt
```
*Supported formats:*
*   **TXT**: One user/link per line.
*   **CSV**: First column is user/link.
*   **JSON**: List of strings `["user1", "user2"]`.

## 3. Date Filtering
Filter any mode by date:
```bash
python extract_react_pnl.py --user 0x... --start-date 2026-01-05
```

## 4. Why is this better?
*   **Speed**: Takes ~2 seconds vs ~40 seconds.
*   **Accuracy**: Gets the raw mathematical values (e.g. `46154.355`) instead of rounded tooltip text.
*   **Completeness**: Can fetch 100% of your history in one go.

## 5. Troubleshooting
*   **"Profile not found"**: Check spelling of user address.
*   **"No PnL query found"**: Private profile or page layout changed. Use `--show-browser` to inspect.
