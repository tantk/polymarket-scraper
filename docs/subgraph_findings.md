# Polymarket PnL Subgraph Findings

**Subgraph URL:** `https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn`

## Core Mechanism
The PnL subgraph tracks **Realized PnL** based on *secondary market trading* (selling shares back to the orderbook).

### Key Characteristics
1.  **Cumulative**: The `realizedPnl` value is a lifetime running total for the user.
    - To get PnL for a period, you must query: `PnL(EndBlock) - PnL(StartBlock)`.
2.  **Trade-Only**: It calculates PnL when a user *reduces* their position size via a trade.
    - Formula: `(SellPrice - AverageCostBasis) * QuantitySold`.
3.  **Missing Redemptions**: It **DOES NOT** account for payouts from market resolution (Redemptions).
    - If a user buys a "Yes" share for $0.60 and it resolves to "Yes" ($1.00), the $0.40 profit is realized via **Redemption**, not a trade.
    - The Subgraph sees this as a position that was never "sold", so `realizedPnl` remains unchanged.
    - **Impact**: This causes massive discrepancies for profitable traders who hold to expiry.

## Usage for Reconciliation
To use this subgraph effectively, you must:
1.  Query `realizedPnl` delta for the period.
2.  Independently fetch and sum **Redemption Payouts** for the same period.
3.  Sum `SubgraphTradePnL + RedemptionPnL`.

*Note: Even with this adjustment, discrepancies may exist due to Cost Basis accounting differences when positions are split between sales and redemptions.*
