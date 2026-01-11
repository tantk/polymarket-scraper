import pandas as pd
import requests
import json
import time
from datetime import datetime

# Files
ENRICHED_CSV = "data/final/polymarket_jan5_jan6_enriched.csv"
REDEMPTIONS_CSV = "data/interim/polymarket_jan5_jan6_redemptions.csv"
OUTPUT_CSV = "data/interim/polymarket_jan5_jan6_detailed_pnl.csv"

# Gamma API
GAMMA_URL = "https://gamma-api.polymarket.com/markets"

def fetch_market_map(start_date="2026-01-04T00:00:00Z", end_date="2026-01-07T23:59:59Z"):
    """
    Fetches markets and maps TokenID -> (ConditionID, OutcomeIndex, MarketClosed).
    """
    print("Fetching Market Metadata from Gamma...")
    token_map = {}
    
    offset = 0
    while True:
        params = {
            "limit": 100,
            "offset": offset,
            "start_date_min": start_date,
            "end_date_min": start_date,
            "end_date_max": end_date
        }
        try:
            r = requests.get(GAMMA_URL, params=params, timeout=10)
            data = r.json()
            if not data:
                break
                
            for m in data:
                cond_id = m.get('conditionId')
                closed = m.get('closed', False)
                
                # Parse tokens to get Order (Index)
                # clobTokenIds is usually [Token0, Token1] corresponding to Outcome0, Outcome1
                raw_toks = m.get('clobTokenIds', '[]')
                if isinstance(raw_toks, str):
                    try:
                        tokens = json.loads(raw_toks)
                    except:
                        tokens = []
                else:
                    tokens = raw_toks
                    
                if tokens and cond_id:
                    for i, t in enumerate(tokens):
                        # Store tuple: (ConditionID, Index, Status)
                        token_map[t] = {"condition": cond_id, "index": str(i), "closed": closed, "title": m.get('question')}
                        
            offset += 100
            print(f"Mapped {len(token_map)} tokens... (Offset {offset})")
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error: {e}")
            break
            
    return token_map

def main():
    # 1. Load Data
    df_trades = pd.read_csv(ENRICHED_CSV)
    df_red = pd.read_csv(REDEMPTIONS_CSV)
    
    # 2. Build Precise Outcome Map: (ConditionID, IndexStr) -> IsWinner (Bool)
    outcome_map = {}
    print("Building Redemption Outcome Map...")
    
    for _, row in df_red.iterrows():
        cond = str(row['condition'])
        payout = float(row['payout'])
        idx_raw = row.get('indexSets', '[]')
        
        try:
            indices = json.loads(idx_raw)
        except:
            indices = []
            
        # Logic:
        # If Payout > 0: These indices are WINNERS. (Value 1.0)
        # If Payout == 0: These indices are LOSERS. (Value 0.0)
        is_winner = (payout > 0)
        
        for idx in indices:
            key = (cond, str(idx))
            outcome_map[key] = is_winner
            
    print(f"Mapped {len(outcome_map)} resolved outcomes from redemptions.")
    
    # 3. Build Token Map
    token_map = fetch_market_map()
    
    # 4. Enrich
    print("Enriching Trades with Precision...")
    enriched_rows = []
    
    for idx, row in df_trades.iterrows():
        tid = str(row['asset_id_raw'])
        market_info = token_map.get(tid)
        
        # Default Values
        status = "Unknown"
        final_price = 0.0 
        pnl_realized = 0.0
        
        cost = float(row['volume_usdc'])
        side = row['side']
        size = float(row['size'])
        
        if market_info:
            cond_id = market_info['condition']
            outcome_idx = market_info['index']
            is_closed = market_info['closed']
            
            # Precise Check via Outcome Map
            outcome_key = (cond_id, outcome_idx)
            
            if outcome_key in outcome_map:
                is_winner = outcome_map[outcome_key]
                if is_winner:
                    status = "Resolved_Winner"
                    final_price = 1.0
                else:
                    status = "Resolved_Loser"
                    final_price = 0.0
            elif is_closed:
                # Market Closed but User did NOT redeem this specific outcome?
                # Probably lost and didn't redeem? Or sold before?
                # If sold, they don't have it.
                # If held, they should have redeemed.
                # Conservative: If closed and not in redemption map, assume 0.
                status = "Closed_NoRedemption"
                final_price = 0.0
            else:
                status = "Open"
                # Use entry price or maybe 0.5? Sticking to market price (execution price) proxy.
                final_price = float(row['price']) 
        else:
            status = "Unmapped"
            final_price = 0.0
            
        # PnL Calculation
        if side == "BUY":
            current_val = size * final_price
            trade_pnl = current_val - cost
        else:
            # SELL: Revenue - ValueSold
            current_val = 0 
            trade_pnl = cost - (size * final_price) 
            
        row['status'] = status
        row['final_price_est'] = final_price
        row['estimated_pnl'] = trade_pnl
        enriched_rows.append(row)
        
    df_out = pd.DataFrame(enriched_rows)
    df_out.to_csv(OUTPUT_CSV, index=False)
    
    total_est_pnl = df_out['estimated_pnl'].sum()
    print(f"Total Estimated PnL (Enriched): ${total_est_pnl:,.2f}")

if __name__ == "__main__":
    main()
