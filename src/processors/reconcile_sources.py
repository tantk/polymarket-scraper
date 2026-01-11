import pandas as pd
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# Files
GOLDSKY_ENRICHED = "data/final/polymarket_jan5_jan6_enriched.csv"
GOLDSKY_REDEMPTIONS = "data/interim/polymarket_jan5_jan6_redemptions.csv"
SCRAPER_FILE = "data/final/polymarket_full_history.csv"
SUBGRAPH_RESULT = "data/raw/pnl_subgraph_result.json"

# Timestamps
START_TS = 1767571200 # Jan 5 00:00
END_TS = 1767744000   # Jan 7 00:00

def get_goldsky_pnl():
    """
    Calculates PnL from Enriched Trade Data + Redemptions.
    PnL = (Sell Volume - Buy Volume) + Redemption Payouts
    Note: 'volume_usdc' in enriched is strictly the value transacted.
    We need to check 'side'.
    """
    print("--- Source 1: Goldsky API (Orderbook + Activity) ---")
    
    # 1. Trades
    try:
        df_trades = pd.read_csv(GOLDSKY_ENRICHED)
        
        # Filter for time range (just in case file has more)
        # Assuming file is already filtered, but let's be safe if we have 'timestamp_utc'
        # Convert to datetime
        df_trades['dt'] = pd.to_datetime(df_trades['timestamp_utc'])
        # Filter: >= Jan 5 AND < Jan 7
        mask = (df_trades['dt'] >= datetime.utcfromtimestamp(START_TS)) & (df_trades['dt'] < datetime.utcfromtimestamp(END_TS))
        df_trades = df_trades[mask]
        
        # Calculate Realized PnL from Trading
        # If BUY: Cash Outflow (-usdc_size)
        # If SELL: Cash Inflow (+usdc_size)
        # Note: The enriched file usually has 'side' as 'BUY' or 'SELL'.
        # IF ONLY 'BUY' exists (as seen in some scrapes if user is always taker buying?), we need to check.
        # Enriched file schema check from previous View:
        # Columns: timestamp_utc, market_title, outcome, side, price, size, volume_usdc, ...
        # Sample rows showed 'BUY'.
        
        spent = df_trades[df_trades['side'] == 'BUY']['volume_usdc'].sum()
        received = df_trades[df_trades['side'] == 'SELL']['volume_usdc'].sum()
        
        trade_pnl = received - spent
        print(f"Trades: Bought ${spent:,.2f}, Sold ${received:,.2f} -> Net: ${trade_pnl:,.2f}")
        
    except Exception as e:
        print(f"Error reading trades: {e}")
        trade_pnl = 0
        
    # 2. Redemptions
    # Redemptions are PURE PROFIT (Cash Inflow) effectively, as the cost was the 'Buy'.
    try:
        # Redemptions file has no header in creation script? 
        # extract_redemptions.py wrote header first: ["id", "timestamp", "timestamp_utc", "redeemer", "payout", "condition"]
        df_red = pd.read_csv(GOLDSKY_REDEMPTIONS)
        
        # Filter strict time range
        df_red['dt'] = pd.to_datetime(df_red['timestamp_utc'])
        mask = (df_red['dt'] >= datetime.utcfromtimestamp(START_TS)) & (df_red['dt'] < datetime.utcfromtimestamp(END_TS))
        df_red = df_red[mask]
        
        redemption_payout = df_red['payout'].astype(float).sum() / 1e6 # Base units usually 1e6 for USDC?
        # Check raw values in file.
        # If extract_redemptions didn't normalize, raw values are huge integers (6 decimals).
        # Let's peek at a value (heuristic). If > 1,000,000 for a normal trade, it's 6 decimals.
        # Safe bet is / 1e6.
        
        print(f"Redemptions: ${redemption_payout:,.2f} (Count: {len(df_red)})")
        
    except Exception as e:
        print(f"Error reading redemptions: {e}")
        redemption_payout = 0
        
    total_goldsky = trade_pnl + redemption_payout
    return total_goldsky

def get_scraper_pnl():
    """
    Reads daily PnL snapshot.
    Finds value at Jan 5 start and Jan 7 start (or closest records).
    """
    print("\n--- Source 2: Web Scraper (Profile PnL) ---")
    try:
        df = pd.read_csv(SCRAPER_FILE)
        # Schema: Timestamp, Date_Readable, PnL_Value, User, Timeframe, Scrape_Time
        # We want 'ALL' timeframe or 1D? PnL logic is usually cumulative in 'ALL'.
        # Or we can sum '1D' or '1W' values?
        # Best approach: Use 'ALL' value at End - 'ALL' value at Start.
        
        df = df[df['Timeframe'] == 'ALL'].sort_values('Timestamp')
        
        # Find closest timestamp <= START_TS
        # Actually, we want the PnL State AT Jan 5 00:00.
        # The file has daily snapshots.
        # If we have 2026-01-05 02:00:00, that's close enough.
        
        # Filter for range
        start_rec = df.iloc[(df['Timestamp'] - START_TS).abs().argsort()[:1]]
        end_rec = df.iloc[(df['Timestamp'] - END_TS).abs().argsort()[:1]]
        
        if start_rec.empty or end_rec.empty:
            print("Insufficient data.")
            return 0
            
        pnl_start = float(start_rec['PnL_Value'].values[0])
        pnl_end = float(end_rec['PnL_Value'].values[0])
        
        ts_start = start_rec['Date_Readable'].values[0]
        ts_end = end_rec['Date_Readable'].values[0]
        
        print(f"Snapshot Start ({ts_start}): ${pnl_start:,.2f}")
        print(f"Snapshot End   ({ts_end}):   ${pnl_end:,.2f}")
        
        return pnl_end - pnl_start
        
    except Exception as e:
        print(f"Error reading scraper: {e}")
        return 0

def get_subgraph_pnl():
    print("\n--- Source 3: PnL Subgraph (Block Time Travel) ---")
    try:
        if not os.path.exists(SUBGRAPH_RESULT):
            print("Result file not found. Run fetch_pnl_blocks.py first.")
            return 0
            
        with open(SUBGRAPH_RESULT, 'r') as f:
            data = json.load(f)
            
        print(f"Block {data['start_block']} -> {data['end_block']}")
        print(f"Value: ${data['pnl_start']:,.2f} -> ${data['pnl_end']:,.2f}")
        return data['net_profit']
    except Exception as e:
        print(f"Error: {e}")
        return 0

def main():
    print("=== PnL Reconciliation Report ===\n")
    
    pnl_1 = get_goldsky_pnl()
    pnl_2 = get_scraper_pnl()
    pnl_3 = get_subgraph_pnl()
    
    print("\n=== FINAL COMPARISON (Jan 5 - Jan 7) ===")
    print(f"{'Source':<25} | {'Net Profit':>15} | {'Delta vs Basis':>15}")
    print("-" * 60)
    print(f"{'1. Goldsky API (Calc)':<25} | ${pnl_1:>14,.2f} | {'BASIS':>15}")
    print(f"{'2. Web Scraper':<25} | ${pnl_2:>14,.2f} | ${pnl_2 - pnl_1:>14,.2f}")
    print(f"{'3. PnL Subgraph':<25} | ${pnl_3:>14,.2f} | ${pnl_3 - pnl_1:>14,.2f}")
    print("-" * 60)
    
    # Match Analysis
    diff_subgraph = abs(pnl_3 - pnl_1)
    if diff_subgraph < 100:
        print("\n✅ Goldsky Transaction Data matches Subgraph PnL closely.")
    else:
        print("\n⚠️ Significant discrepancy between Transaction Data and Subgraph.")
        print("Possible causes: Missing fees in calculation, missing redemptions, or time zone misalignment.")

if __name__ == "__main__":
    main()
