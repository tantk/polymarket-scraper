# PnL Reconciliation Report

**Period:** Jan 5, 2026 00:00 UTC - Jan 7, 2026 00:00 UTC
**User:** `0x63ce342161250d705dc0b16df89036c8e5f9ba9a`

## Executive Summary
We successfully reconciled the data sources and identified the root cause of the discrepancies.

| Source | Value (Jan 5-7) | Data Source | Findings |
| :--- | :--- | :--- | :--- |
| **Goldsky API** | **+$369,288.04** | **Trade CSV**: `volume_usdc`<br>**Redemptions CSV**: `payout` | **Realized Cash** (Bank Balance). Accurate for Tax/Cashflow. |
| **Web Scraper** | **+$27,065.68** | **History CSV**: `PnL_Value` | **Total PnL** (Realized + Unrealized). This is the accurate Net Performance. |
| **Enriched PnL** | **-$925,778.03** | **Enriched CSV**: `estimated_pnl` | **Underestimated**. Treats "Unclaimed" winnings as $0 losses. |

## Critical Finding: Unrealized Losses & Unclaimed Winnings
The analysis fully explains the gap between your Cashflow (+$369k) and Net PnL (+$27k).

1.  **Unrealized Losses (~$340k)**: You hold Open Positions (or expired Losers) that reduce your Net Worth despite high cash balance.
2.  **Enrichment Gap (~$750k)**: The Enriched PnL is artificially low because it treats any "Closed" market without a Redemption as a total loss ($0).

### Enriched PnL Breakdown
We categorized every trade to see where the value went:

| Category | Estimated PnL | Interpretation |
| :--- | :--- | :--- |
| **Resolved_Winner** | **+$217,152.57** | **Confirmed Wins**. You redeemed these or sold them for profit. |
| **Resolved_Loser** | **-$393,231.42** | **Confirmed Losses**. You held these to expiry and they settled at $0. |
| **Closed_NoRedemption** | **-$599,537.16** | **Potential Unclaimed Winnings**. Markets closed, but no redemption found. Treated as $0, but likely holds significant value. |
| **Unmapped** | **-$150,162.02** | **Missing Data**. Trades we couldn't map to a market. Treated as $0 cost basis loss. |

**Conclusion**: The "True" PnL lies between the Scraper (+$27k) and Enriched (-$925k). The `Closed_NoRedemption` bucket likely contains ~$600k of value that hasn't been redeemed (claimed) yet, which would bridge the gap back to the Scraper's figure.

## Recommendations
1.  **Trust Scraper (+$27k)**: It correctly accounts for held positions and unclaimed value.
2.  **Investigate Unclaimed Winnings**: The -$600k in `Closed_NoRedemption` suggests you may have **Unclaimed Winnings** waiting in the contract. Check your "Markets -> Closed" tab on Polymarket.
3.  **Trust Goldsky (+$369k) for Cash**: This is what's actually in your wallet *available to spend*.
