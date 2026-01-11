# Polymarket Transaction Extraction Schema

Based on the analysis, we can normalize the data into two tables to significantly reduce redundancy.

## 1. Main Transaction Table (Stream)
These fields are non-redundant and specific to each individual trade event.

| Column Name | Description |
| :--- | :--- |
| `timestamp_unix` | Unix timestamp of the activity. (UTC time is derived from this) |
| `market_slug` | **Foreign Key** link to Market Reference. |
| `outcome` | Prediction outcome (`Up` / `Down`). |
| `price` | Execution price per share. |
| `size` | Number of shares. |
| `usdc_size` | Total value in USDC. |
| `transaction_hash` | Polygon transaction ID. |

## 2. Market Reference Table (Lookup)
These fields are constant for each Market/Outcome and should be stored **once** per market, not repeated for every trade.

| Column Name | Description | Relation |
| :--- | :--- | :--- |
| `market_slug` | **Primary Key**. Unique identifier string. | |
| `market_title` | Name of the market. | 1:1 with Slug |
| `condition_id` | Unique market condition ID. | 1:1 with Slug |
| `asset_id_up` | Token ID for the "Up" outcome. | 1:1 with Slug+Outcome |
| `asset_id_down` | Token ID for the "Down" outcome. | 1:1 with Slug+Outcome |

## Redundant Fields (Exclude completely)
| Excluded Field | Reason |
| :--- | :--- |
| `timestamp_utc` | Derived from `timestamp_unix`. |
| `side` | Constant **BUY** for this strategy. |
| `pseudonym` | Constant. |
| `proxyWallet` | Constant. |
| `icon` | Derived/Repetitive. |
| `block_number` | Expensive to fetch. |
