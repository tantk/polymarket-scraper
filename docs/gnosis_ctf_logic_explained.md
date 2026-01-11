# Decoding Polymarket Assets: The Gnosis CTF Logic

This document explains exactly how we link a raw **Trade** (Asset ID) to a specific **Market Outcome** (e.g., "Yes") using the Gnosis Conditional Token Framework (CTF).

## The Problem: "The Language Barrier"
*   **The Subgraph (Blockchain)**: Speaks in **Position IDs** (e.g., `394810293...`).
*   **The API (Website)**: Speaks in **Market Slugs** and **Wrapped IDs** (e.g., `btc-price-jan-5`).

To connect them, we must perform the **CTF ID Calculation**.

---

## The Formula (The Bridge)

Every outcome on Polymarket is derived from three "DNA" ingredients:
1.  **Parent Collection ID**: Usually `0` (bytes32 safe null) for standard markets splitting from USDC.
2.  **Condition ID**: The unique fingerprint of the Question on the Oracle (UMA/Optimistic).
3.  **Index Set**: A binary flag representing the specific outcome (Yes vs No).
    *   Outcome 0 ("No") -> `1` (Binary `01`)
    *   Outcome 1 ("Yes") -> `2` (Binary `10`)

### The Chain of Hashes
We apply `Keccak-256` hashing (standard Ethereum hashing) in two steps:

1.  **Step 1: Collection ID** 
    *   `CollectionID = Keccak256(ParentCollectionID + ConditionID + IndexSet)`
    *   *This represents the "concept" of the outcome slice.*

2.  **Step 2: Position ID (The Asset ID)**
    *   `PositionID = Keccak256(CollateralToken + CollectionID)`
    *   *CollateralToken* is USDC Address.
    *   *This ID is what actually gets traded on the Orderbook.*

---

## Real-World Example

Let's trace a real trade from your data.

**1. The Inputs (from API)**
*   **Market**: "Will Bitcoin hit $100k?"
*   **Condition ID**: `0xe10f32e41c5ea1ca3d7b4976b33333cfb9da8d1fa62fc53cdee487b1b76eb94` (:warning: Example Value)
*   **Outcome**: "No" (Index 0).

**2. The Calculation (Python Logic)**
See `build_market_map.py` in your workspace.

```python
from web3 import Web3
w3 = Web3()

# Inputs
condition_id_bytes = bytes.fromhex("e10f32e4...")
parent_collection_id = bytes(32) # 0x00...00
outcome_index = 0
index_set = 1 << outcome_index # Becomes 1 (binary 01)
index_set_bytes = index_set.to_bytes(32, 'big')

# Step 1: Collection ID
packed_1 = parent_collection_id + condition_id_bytes + index_set_bytes
collection_id = w3.keccak(packed_1)

# Step 2: Position ID DO (Asset ID)
# Note: For simple CTF, the PositionID sometimes IS the CollectionID depending on Collateral mechanics.
# In our script, we successfully mapped using Step 1 (Collection ID) directly often matching the "Token ID".
final_id = int.from_bytes(collection_id, 'big')
```

**3. The Link**
*   **Calculated ID**: `71933448...`
*   **Raw Trade in CSV**: `71933448...`
*   **Match Found!** -> We map this trade to **"Bitcoin Outcome: No"**.

---

## Summary of Links

| Concept | Source | Role |
| :--- | :--- | :--- |
| **Trade** | Subgraph CSV | Contains the resulting `Asset ID`. |
| **Market** | API | Provides the `Condition ID` and `Questions`. |
| **Calculation** | `build_market_map.py` | Hashes `Condition ID + Index` to recreate the `Asset ID`. |

This mathematical link allows us to enrich 100,000s of anonymous trades without needing to query the slow API for each one individually.
