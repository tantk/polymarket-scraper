import pandas as pd

# Load data
csv_file = "data/raw/polymarket_user_transactions.csv"
try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    df = pd.read_csv(f"c:\\dev\\work\\{csv_file}")

print(f"Loaded {len(df)} rows.")

# 1. Check Condition ID vs Market Slug
# Does one market slug always have the same condition ID?
print("\n--- Condition ID vs Market Slug ---")
slug_groups = df.groupby('market_slug')['condition_id'].nunique()
multi_condition_slugs = slug_groups[slug_groups > 1]
if len(multi_condition_slugs) == 0:
    print("SUCCESS: Each Market Slug maps to exactly ONE Condition ID.")
    print("Optimization: condition_id can be moved to a 'Markets' table.")
else:
    print(f"FAIL: {len(multi_condition_slugs)} slugs have multiple condition IDs.")
    print(multi_condition_slugs.head())

# 2. Check Asset ID vs (Market Slug + Outcome)
# Does a specific outcome in a specific market always have the same Asset ID?
print("\n--- Asset ID vs (Market Slug + Outcome) ---")
df['market_outcome_pair'] = df['market_slug'] + " | " + df['outcome']
pair_groups = df.groupby('market_outcome_pair')['asset_id'].nunique()
multi_asset_pairs = pair_groups[pair_groups > 1]

if len(multi_asset_pairs) == 0:
    print("SUCCESS: An Outcome in a Market maps to exactly ONE Asset ID.")
    print("Optimization: asset_id can be moved to a 'Markets/Outcomes' table.")
else:
    print(f"FAIL: {len(multi_asset_pairs)} pairs have multiple Asset IDs.")
    print(multi_asset_pairs.head())

# 3. Check Market Title vs Slug
print("\n--- Title vs Slug ---")
slug_title_groups = df.groupby('market_slug')['market_title'].nunique()
multi_title_slugs = slug_title_groups[slug_title_groups > 1]
if len(multi_title_slugs) == 0:
    print("SUCCESS: Slug maps to exactly ONE Title.")
else:
    print(f"FAIL: {len(multi_title_slugs)} slugs have multiple Titles.")

