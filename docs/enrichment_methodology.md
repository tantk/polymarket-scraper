# PnL Enrichment Methodology

**File Created:** `polymarket_jan5_jan6_detailed_pnl.csv`
**Source Script:** `enrich_pnl.py`

## Objective
To estimate the Profit & Loss (PnL) for individual trades by accurately identifying "Winner" vs "Loser" tokens, even when multiple outcomes were traded for the same market.

## Inputs
1.  **Trade Data**: `polymarket_jan5_jan6_enriched.csv`
2.  **Redemption Data**: `polymarket_jan5_jan6_redemptions.csv` (Now includes `indexSets`).

## Solved: The Double Counting Risk
**Previous Issue**: Ambiguity in matching trades to redemptions led to valuing *all* tokens of a redeemed condition as Winners.
**Resolution**: We implemented **Precise Outcome Matching**.

### 1. Token Index Mapping
We use the Gamma API to map each `TokenID` to its specific **Outcome Index** (0, 1, etc.) within the market condition.

### 2. Redemption Index Parsing
We parse the `indexSets` field from the Redemption event.
-   If `payout > 0`, the indices in `indexSet` are **Confirmed Winners**.
-   If `payout == 0`, the indices in `indexSet` are **Confirmed Losers**.

### 3. Precise Matching Logic
For each trade:
1.  Identify the `TokenID` and its `OutcomeIndex` (e.g., Index 1).
2.  Find the Redemption event for that Market Condition.
3.  Check if `OutcomeIndex` exists in the Redemption's `indexSets`.
    -   **Match Found**:
        -   If Redemption Payout > 0: **Status = Resolved_Winner** (Value $1.00).
        -   If Redemption Payout == 0: **Status = Resolved_Loser** (Value $0.00).
    -   **No Match**:
        -   If Market Closed: **Status = Closed_NoRedemption** (Value $0.00).
        -   If Market Open: **Status = Open** (Value estimated at Cost/Market Price).

## Result
This methodology eliminates the double-counting error. A "Hedge" (Buy Yes + Buy No) where "Yes" wins will now correctly show:
-   **Yes Trade**: Winner ($1.00) -> Profit.
-   **No Trade**: Loser ($0.00) -> Loss.
The Net PnL correctly reflects the hedged outcome.

## 4. Handling Sold Positions
A common concern is whether the script "Double Counts" profit if a user sells a Winning Token before redemption.
**Verified Logic**: The script correctly handles this via **Opportunity Cost** mathematics.

### Scenario: Selling a Winner Early
-   User Buys "Yes" @ $0.40.
-   User Sells "Yes" @ $0.90. (Profit = $0.50).
-   Market Resolves "Yes" ($1.00).

### Script Calculation
The script sees the condition was redeemed (by others or the market closed as Yes), so it marks the token as a **Winner** ($1.00).
1.  **Buy Row**: `(Value $1.00 - Cost $0.40)` = **+$0.60** (Unrealized Potential Profit).
2.  **Sell Row**: `(CashReceived $0.90 - ValueSold $1.00)` = **-$0.10** (Opportunity Cost / "Money left on table").
3.  **Net PnL**: `+$0.60 - $0.10` = **+$0.50**.

**Conclusion**: The script does NOT add a full redemption PnL for sold tokens. Instead, the negative PnL on the Sell row cancels out the extra unrealized gain on the Buy row, mathematically arriving at the exact realized cash profit.
