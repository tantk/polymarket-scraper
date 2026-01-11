# Implementation Plan - Instant PnL Extractor

## Goal Description
Create a new script (`extract_react_pnl.py`) that extracts the **full PnL history** instantly from the Polymarket metadata (`window.__NEXT_DATA__`), bypassing the need for slow visual scraping (hovering).

## User Review Required
> [!NOTE]
> This method is significantly faster (1 second vs 30 seconds) and more accurate (raw data vs tooltip strings).

## Proposed Changes

### New Script
#### [NEW] [extract_react_pnl.py](file:///C:/Users/tanti/.gemini/antigravity/brain/76c9cedf-7dbf-4ff2-a1cf-76f6af4966d2/extract_react_pnl.py)
*   **Method**: Playwright `page.evaluate()`.
*   **Logic**:
    1.  Load Profile.
    2.  Execute JS: `return window.__NEXT_DATA__.props.pageProps.dehydratedState.queries`
    3.  Find query with key `['portfolio-pnl', ...]`.
    4.  Extract array of `{p: value, t: timestamp}`.
    5.  Convert `t` (Unix Timestamp) to Date.
    6.  Dump all points to CSV.
*   **Output**: `polymarket_full_history.csv`

## Verification Plan
1.  Run the script.
2.  Check CSV for 50+ data points (covering the full graph history).
