import pandas as pd
import json
import os

RAW_FILE = "polymarket_jan5_jan6_raw.csv" # Maker
TAKER_FILE = "polymarket_jan5_jan6_taker.csv" # Taker
MAP_FILE = "asset_map.json"
OUTPUT_FILE = "polymarket_jan5_jan6_enriched.csv"
USER_ADDRESS_LOWER = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"

def enrich():
    print("Loading data...")
    # Load Map
    asset_map = {}
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, "r") as f:
            asset_map = json.load(f)
            
    # Load Events
    dfs = []
    for f in [RAW_FILE, TAKER_FILE]:
        if os.path.exists(f):
            try:
                d = pd.read_csv(f)
                # Ensure no string headers in data
                d = d[d['makerAmountFilled'] != 'makerAmountFilled']
                dfs.append(d)
            except:
                pass

    if not dfs:
        print("No data found.")
        return

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=['id'])
    
    print(f"Enriching {len(df)} events...")
    
    enriched_rows = []
    
    for idx, row in df.iterrows():
        # Logic to find attributes
        m_asset = str(row['makerAssetId'])
        t_asset = str(row['takerAssetId'])
        m_amt = float(row['makerAmountFilled'])
        t_amt = float(row['takerAmountFilled'])
        
        # Identify USDC side (Asset "0")
        # If maker is 0 -> Maker is BUYING Outcome (Spending USDC)
        # If taker is 0 -> Taker is BUYING Outcome (Spending USDC)
        
        usdc_amt = 0.0
        outcome_amt = 0.0
        outcome_asset_id = ""
        side = "UNKNOWN" # Buy/Sell from User Perspective?
        
        maker_addr = str(row['maker']).lower()
        taker_addr = str(row['taker']).lower()
        is_user_maker = (maker_addr == USER_ADDRESS_LOWER)
        
        # Case A: Maker Asset is USDC ("0")
        if m_asset == "0":
            usdc_amt = m_amt
            outcome_amt = t_amt
            outcome_asset_id = t_asset
            # Maker (User?) gave USDC -> User BOUGHT
            if is_user_maker:
                side = "BUY"
            else:
                side = "SELL" # User is Taker, receiving USDC (Selling)
                
        # Case B: Taker Asset is USDC ("0")
        elif t_asset == "0":
            usdc_amt = t_amt
            outcome_amt = m_amt
            outcome_asset_id = m_asset
            # Taker gave USDC -> Taker BOUGHT.
            # If User is Maker (receiving USDC) -> User SOLD.
            if is_user_maker:
                side = "SELL"
            else:
                side = "BUY" # User is Taker (Giving USDC)
        
        # Case C: Cross-Token Trade? (Rare on Polymarket, usually against USDC)
        else:
            # Maybe two outcome tokens? Merge?
            side = "MERGE/SWAP"
            outcome_asset_id = m_asset # Just pick one to map
            
        # Calculate Price & Size
        # Size = Outcome Amount (Atomic units? usually 1e6 for Polymarket CTF?)
        # USDC = 1e6 decimals.
        # Conditional Tokens also 1e6? Usually yes.
        
        size = outcome_amt / 1e6
        volume = usdc_amt / 1e6
        
        price = 0.0
        if size > 0:
            price = volume / size
            
        # Lookup Map
        market_info = asset_map.get(outcome_asset_id, {})
        if not market_info:
             # Try Hex version?
             try:
                 hex_id = hex(int(outcome_asset_id))
                 market_info = asset_map.get(hex_id, {})
             except:
                 pass
        
        # If still not found, search map for decimal version if map has decimal keys?
        # My map builder saved keys as provided by API (strings, often decimal).
        
        title = market_info.get('title', 'Unknown Market')
        outcome_label = market_info.get('outcome', '?')
        slug = market_info.get('slug', '')
        
        new_row = {
            "timestamp_utc": row['timestamp_utc'],
            "market_title": title,
            "outcome": outcome_label,
            "side": side,
            "price": round(price, 4),
            "size": round(size, 2),
            "volume_usdc": round(volume, 2),
            "asset_id_raw": outcome_asset_id,
            "transaction_hash": row['transactionHash']
        }
        enriched_rows.append(new_row)
        
    df_out = pd.DataFrame(enriched_rows)
    df_out.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {OUTPUT_FILE} with {len(df_out)} rows.")
    
    # Preview
    print("\nSample Enriched Data:")
    print(df_out[['timestamp_utc', 'market_title', 'side', 'price', 'size']].head(10))

if __name__ == "__main__":
    enrich()
