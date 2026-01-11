# Antigravity Workspace Rules: Polymarket Scraper Project

# [SYSTEM_COMMAND: ALWAYS_READ_ON_START]
# Project Constitution: Polymarket User Transaction Analysis

## 0. Project Overview & Context
- **Core Objective:** Analyze and extract user transaction data from Polymarket.
- **Data Sources:** Subgraph queries, RPC nodes, and Goldsky API.
- **Primary Metrics:** PNL (Profit and Loss), volume, redemption history, and user activity patterns.
- **Success Criteria:** Accurate, deduplicated CSV/JSON exports organized in the `data/` directory.

## 1. Execution & Security Policies
- **Terminal Policy:** RESTRICTED
- **Creation Permissions (Auto):** You may use `New-Item`, `mkdir`, `touch`, and `python` (subject to Rule 1.1) without confirmation to build the workspace.
- **Restricted Operations (Require Confirmation):** - **Move Operations:** `Move-Item`, `mv`.
    - **Destructive Operations:** `Remove-Item`, `rm`, `del`.
- **Protocol for Restricted Actions:**
    1. Identify the files involved.
    2. State the destination (for moves) or the reason (for removals).
    3. Wait for my explicit "Approve" before executing.

### 1.1 Python Script Safety Audit
- **Pre-Execution Scan:** Before running any `.py` script, the agent MUST scan the source code for destructive calls.
- **Flag for Confirmation if:** The script contains `os.remove`, `os.rmdir`, `shutil.rmtree`, `shutil.move`, or `subprocess`/`os.system` calls that target files outside of `data/interim/`.
- **Logic Disclosure:** Before executing a script, provide a 1-sentence summary of its intent (e.g., "This script fetches raw logs and writes to data/raw/").

## 2. Reporting & Session Persistence
- **Naming Convention:** On initialization, create `logs/findings_YYYY-MM-DD_HH-mm.md`.
- **Continuity:** Read the most recent log file in `logs/` before starting any new task to resume state.
- **Data Capture:** Document all URLs, timestamps, and raw JSON data findings immediately.
- **Redirection Rule:** Never use `>` to the project root. Always redirect output to `data/raw/` or `logs/`.

## 3. Performance & Stability Overrides
- **Multimedia Artifacts:** DISABLED.
- **Memory Purge:** Every 25 steps, summarize progress to the current log and clear the active conversation context.
- **Context Thresholds:** - At **Step 80**: Issue a warning about IDE stability.
    - At **Step 100**: Save a `CHECKPOINT.json` and request a session restart.

## 4. Workspace Hygiene & File Architecture
- **Medallion Data Pattern:** Save data ONLY to `data/raw/`, `data/interim/`, or `data/final/`. 
- **Automated Maintenance:** - **Archiving:** Automatically move log files older than 24 hours to `logs/archived/`.
    - **Cleanup Trigger:** If the root directory exceeds 5 non-configuration files, pause and execute a reorganization.

## 5. Project Map (Reorganized Jan 2026)

### Source Code ('src/')
- **'extractors/'**: Scripts that fetch raw data from external sources (Goldsky, Polymarket API, Web Scraper).
    - 'extract_polymarket_activity.py', 'extract_react_pnl.py', 'extract_redemptions.py', 'extract_subgraph.py', 'scrape_polymarket_pnl.py', 'build_market_map.py'
- **'processors/'**: Logic for enriching, reconciling, and transforming raw data.
    - 'enrich_data.py', 'enrich_pnl.py', 'reconcile_pnl.py', 'reconcile_sources.py'
- **'utils/'**: Helper methods and shared utilities.
    - 'printfiles.py', 'get_block_range.py'

### Data Architecture ('data/')
- **'raw/'**: Immutable raw extracts (JSON/CSV) from APIs/Subgraphs.
    - 'polymarket_user_transactions.csv', 'polymarket_jan5_jan6_raw.csv', 'market_sample.json'
- **'interim/'**: Partially processed or normalized data.
    - 'polymarket_jan5_jan6_taker.csv', 'polymarket_jan5_jan6_redemptions.csv', 'polymarket_jan5_jan6_detailed_pnl.csv'
- **'final/'**: Enriched, cleaned, and reporting-ready datasets.
    - 'polymarket_full_history.csv', 'polymarket_jan5_jan6_enriched.csv'

### Validation ('tests/')
- Ad-hoc checks and integrity tests.
    - 'check_*.py', 'test_*.py'

### Documentation ('docs/')
- Markdown guides, reports, and plans.
    - 'scraper_guide.md', 'reconciliation_report.md'
