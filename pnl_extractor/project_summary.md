# Project Summary: Polymarket PnL Extractor

## 1. Objective
The goal was to extract historical Profit & Loss (PnL) data from Polymarket user profiles. Initially, we attempted to do this via "Visual Scraping" (simulating mouse hovers), but we evolved the solution into a high-performance "Instant Extractor" by reverse-engineering the site's React state.

## 2. Technical Evolution

### Phase 1: Visual Scraping
*   **Approach**: Used Playwright to open the browser, hover over the PnL graph, and read the tooltip text.
*   **Limitations**: Slow (~30s per profile), prone to OCR/text errors, and dependent on screen resolution/rendering.

### Phase 2: Instant Extraction (The Breakthrough)
*   **Discovery**: We found that Polymarket pre-loads the *entire* PnL history into a global variable `window.__NEXT_DATA__` on page load.
*   **Solution**: Instead of hovering, we now inject a single line of JavaScript to "grab" this JSON object directly.
*   **Benefits**:
    *   **Speed**: <1 second per profile.
    *   **Accuracy**: Returns raw float values (e.g., `123.4567`) instead of rounded UI text.
    *   **Completeness**: Fetches 1D, 1W, 1M, and ALL history simultaneously.

### Phase 3: Robustness & Batching
*   **Features Added**:
    *   **Batch Mode**: Reads from `users_list.txt` to scrape hundreds of users in one go.
    *   **Smart URLs**: Automatically handles `https://polymarket.com/@username` and `0xAddress` parsing.
    *   **Reliability**: Switched checks from `networkidle` to `domcontentloaded` to prevent timeouts on heavy profiles (like `CRYINGLITTLEBABY`).
    *   **Environment**: Packaged with a `virtualenv`, `requirements.txt`, and a `batch runner` for one-click execution.

## 3. Final Tool Architecture
The tool is self-contained in `pnl_extractor/`.

*   **`extract_react_pnl.py`**: The core logic. Uses Playwright to transparently load pages and extract JSON.
*   **`run_extractor.bat`**: The entry point. Handles environment activation (`venv`) and runs the script.
*   **`users_list.txt`**: Configuration file for your list of targets.
*   **`silent_runner.vbs`**: Wrapper to run the tool invisibly (great for Task Scheduler).
*   **`extraction.log`**: Detailed logs of every run.

## 4. How to Use
1.  **Edit List**: Add profile links to `users_list.txt`.
2.  **Run**: Double-click `run_extractor.bat`.
3.  **Result**: Data ends up in `polymarket_full_history.csv`.

## 5. Deployment
This folder is portable. You can move it to a server or another drive.
For daily updates, schedule `silent_runner.vbs` in Windows Task Scheduler.
