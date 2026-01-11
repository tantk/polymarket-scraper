import pandas as pd
import os

MAKER_FILE = "data/raw/polymarket_jan5_jan6_raw.csv"
TAKER_FILE = "data/interim/polymarket_jan5_jan6_taker.csv"
USER_ADDRESS_LOWER = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

def load_data():
    df_maker = pd.DataFrame()
    df_taker = pd.DataFrame()
    
    if os.path.exists(MAKER_FILE):
        try:
            df_maker = pd.read_csv(MAKER_FILE, names=["id", "timestamp", "timestamp_utc", "transactionHash", "maker", "taker", "makerAssetId", "takerAssetId", "makerAmountFilled", "takerAmountFilled"], header=0)
        except:
            pass
            
    if os.path.exists(TAKER_FILE):
         try:
            df_taker = pd.read_csv(TAKER_FILE, names=["id", "timestamp", "timestamp_utc", "transactionHash", "maker", "taker", "makerAssetId", "takerAssetId", "makerAmountFilled", "takerAmountFilled"], header=None) # No header in append mode usually? 
            # Wait, verify_limit check implies header? extract_subgraph_taker checks exists.
            # safe logic: header=None if appended? Let's check overlap later.
            # Best to read carefully.
            # My extract scripts wrote header only if new file.
            pass
         except:
            pass

    # Re-read properly assuming potential mixed headers or lack thereof
    # Actually, let's just concat everything and drop duplicates.
    dfs = []
    for f in [MAKER_FILE, TAKER_FILE]:
        if os.path.exists(f):
            # Try reading with header
            d = pd.read_csv(f)
            # If the first row looks like header, fine.
            if 'makerAssetId' not in d.columns:
                 # Maybe no header?
                 d = pd.read_csv(f, names=["id", "timestamp", "timestamp_utc", "transactionHash", "maker", "taker", "makerAssetId", "takerAssetId", "makerAmountFilled", "takerAmountFilled"])
            dfs.append(d)
            
    if not dfs:
        return pd.DataFrame()
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Deduplicate by ID
    # Convert ID to string to be safe
    full_df['id'] = full_df['id'].astype(str)
    
    before = len(full_df)
    full_df = full_df.drop_duplicates(subset=['id'])
    after = len(full_df)
    
    print(f"Loaded {before} events. Unique: {after}.")
    return full_df

def calculate_pnl():
    df = load_data()
    if df.empty:
        print("No data loaded.")
        return

    # Normalize Asset IDs (str)
    df['makerAssetId'] = df['makerAssetId'].astype(str)
    df['takerAssetId'] = df['takerAssetId'].astype(str)
    
    # Identify Money (Collateral)
    # Asset "0"
    
    total_spent = 0
    total_received = 0
    
    # Analysis per row
    count_spent = 0
    count_received = 0
    
    for idx, row in df.iterrows():
        maker = str(row['maker']).lower()
        taker = str(row['taker']).lower()
        
        # Determine User Role
        is_maker = (maker == USER_ADDRESS_LOWER)
        is_taker = (taker == USER_ADDRESS_LOWER)
        
        # Self-Match?
        if is_maker and is_taker:
            # User matched with self.
            # Net Cashflow for User: 
            #   User Give (as Maker): makerAssetId
            #   User Receive (as Maker): takerAssetId
            #   User Give (as Taker): takerAssetId
            #   User Receive (as Taker): makerAssetId
            # Net change = 0 for both assets. 
            # It's a wash trade (or moving liquidity pockets).
            # Profit impact = 0 (minus fees? Subgraph has 'fee' field? Not in my CSV export!)
            # Ignoring fees for now.
            continue
            
        # Logic: We strictly care about "Collateral Flow"
        
        # IF USER IS MAKER:
        if is_maker:
            # User GAVE makerAssetId.
            if row['makerAssetId'] == "0": 
                # User GAVE Money -> Spent
                amt = float(row['makerAmountFilled']) / 1e6
                total_spent += amt
                count_spent += 1
            
            # User RECEIVED takerAssetId.
            if row['takerAssetId'] == "0":
                # User RECEIVED Money -> Earned
                amt = float(row['takerAmountFilled']) / 1e6
                total_received += amt
                count_received += 1
                
        # IF USER IS TAKER:
        if is_taker:
            # User GAVE takerAssetId.
            if row['takerAssetId'] == "0":
                # User GAVE Money -> Spent
                amt = float(row['takerAmountFilled']) / 1e6
                total_spent += amt
                count_spent += 1
                
            # User RECEIVED makerAssetId.
            if row['makerAssetId'] == "0":
                # User RECEIVED Money -> Earned
                amt = float(row['makerAmountFilled']) / 1e6
                total_received += amt
                count_received += 1

    net_pnl = total_received - total_spent
    
    print("\n--- PnL Reconcilation (Jan 5-6) ---")
    print(f"Total Spent (Buy Cost):     ${total_spent:,.2f}  ({count_spent} trades)")
    print(f"Total Received (Sell Rev):  ${total_received:,.2f}  ({count_received} trades)")
    print(f"Net Realized Cashflow (Trades): ${net_pnl:,.2f}")
    
    # Redemptions
    REDEMPTION_FILE = "data/interim/polymarket_jan5_jan6_redemptions.csv"
    total_payout = 0
    if os.path.exists(REDEMPTION_FILE):
        try:
             df_red = pd.read_csv(REDEMPTION_FILE, names=["id", "timestamp", "timestamp_utc", "redeemer", "payout", "condition"], header=None)
             # Basic check if header exists or not
             # My extract script wrote header=False?
             # extract_redemptions: pd.DataFrame(columns=...).to_csv(output_file, index=False)
             # Then mode='a', header=False.
             # So FIRST write had header. 
             # Let's read with header=0.
             df_red = pd.read_csv(REDEMPTION_FILE)
             if 'payout' in df_red.columns:
                 # Payout is usually in units (likely same 6 decimals? or 1e6?)
                 # Introspection just said 'payout'.
                 # Usually USDC checks out.
                 market_payouts = df_red['payout'].astype(float)
                 total_payout = market_payouts.sum() / 1e6
        except Exception as e:
             print(f"Error reading redemptions: {e}")

    final_profit = net_pnl + total_payout
    print(f"Total Redemption Payouts:   ${total_payout:,.2f}")
    print(f"FINAL REALIZED PROFIT:      ${final_profit:,.2f}")
    
    print("\nNote: This calculation assumes all payouts and costs are in USDC (6 decimals).")

if __name__ == "__main__":
    calculate_pnl()
