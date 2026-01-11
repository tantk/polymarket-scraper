import requests
import json
import time

# Polymarket Gamma API (Public)
API_URL = "https://gamma-api.polymarket.com/events"
MARKETS_URL = "https://gamma-api.polymarket.com/markets"

def build_map():
    print("Fetching Market Metadata...")
    
    # We need to cover markets from Jan 5-6.
    # We can use /markets and filter? Or use pagination.
    # User trades "Bitcoin", "Ethereum".
    # Let's search for "Bitcoin" and "Ethereum" markets first to get high coverage.
    
    # Remove keyword filter, just get recent closed markets
    # User trades 15m markets, they expire continuously.
    # Latest 2000 markets should cover the last few days easily.
    
    # Filter by date window (Jan 5 - Jan 7) to catch user's markets
    # API supports ISO strings.
    
    offset = 0
    asset_map = {}
    
    # Try to import Web3 for ID calc
    try:
        from web3 import Web3
        w3 = Web3()
        HAS_WEB3 = True
    except ImportError:
        HAS_WEB3 = False
        print("Web3 not found. Cannot calculate Position IDs. Mapping might be incomplete.")

    def calc_position_id(condition_id_hex, outcome_idx):
        # CTF Logic:
        # Parent Collection = 0 (Splitting from Collateral)
        # Condition ID = condition_id
        # Index Set = 1 << outcome_idx
        # Collection ID = keccak(parent, condition, indexSet)
        # Position ID = keccak(Collateral, CollectionID)
        # Wait, usually MakerAsset IS the Position Token (ERC1155).
        # Position Token ID is the Collection ID? No.
        # CTF Token ID is the Collection ID for the specific outcome slice?
        # Actually, for "Join/Split", the ID processed is the Collection ID (if checking balance).
        # But ERC1155 transfer uses `id`. which IS the Collection ID (or Position ID).
        
        # Let's try standard packing:
        # collectionId = keccak256(abi.encodePacked(conditionId, indexSet))
        # Assuming parent is implied or mixed?
        # Standard Gnosis: https://docs.gnosis.io/conditionaltokens/docs/devguide01/
        # collectionId = keccak256(abi.encodePacked(parentCollectionId, conditionId, indexSet))
        # For base markets, parentCollectionId = 0x0...0
        
        try:
            parent = bytes(32) # 0x0
            cond = bytes.fromhex(condition_id_hex[2:])
            idx_set = 1 << outcome_idx
            # indexSet is uint256?
            idx_set_bytes = idx_set.to_bytes(32, 'big')
            
            # Pack: parent + cond + idx_set
            packed = parent + cond + idx_set_bytes
            collection_id = w3.keccak(packed)
            
            # This collection_id IS the Token ID for the outcome.
            return str(int.from_bytes(collection_id, 'big'))
        except Exception as e:
            # print(f"Calc error: {e}")
            return None

    while True:
        params = {
            "limit": 100,
            "offset": offset,
            "closed": "true",
            "order": "endDate",
            "ascending": "true",
            "end_date_min": "2026-01-05T00:00:00Z",
            "end_date_max": "2026-01-07T00:00:00Z"
        }
        try:
            r = requests.get(MARKETS_URL, params=params, timeout=10)
            data = r.json()
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
            continue

        if not data:
            break
            
        for m in data:
            title = m.get('question', 'Unknown')
            slug = m.get('slug', '')
            
            # 1. Map via clobTokenIds (Wrapped/Gamma IDs)
            raw_tokens = m.get('clobTokenIds', '[]')
            tokens = []
            if isinstance(raw_tokens, str):
                try:
                    tokens = json.loads(raw_tokens)
                except:
                    pass
            elif isinstance(raw_tokens, list):
                tokens = raw_tokens
                
            raw_outcomes = m.get('outcomes', '[]')
            outcomes = []
            if isinstance(raw_outcomes, str):
                 try:
                     outcomes = json.loads(raw_outcomes)
                 except:
                     pass
            elif isinstance(raw_outcomes, list):
                 outcomes = raw_outcomes

            # Add clobTokenIds to Map
            if len(tokens) == len(outcomes) and len(tokens) > 0:
                 for i, tk in enumerate(tokens):
                     asset_map[tk] = {"title": title, "slug": slug, "outcome": outcomes[i]}
            
            # 2. Map via Calculated Position IDs (CTF Subgraph IDs)
            condition_id = m.get('conditionId')
            if HAS_WEB3 and condition_id and outcomes:
                for i, out_label in enumerate(outcomes):
                    # Calculate ID for this outcome index
                    # Binary: 0=No? 1=Yes? 
                    # Usually outcomes=["Yes", "No"] -> Index 0=Yes? 
                    # Actually Polymarket outcomes are usually ["Yes", "No"] or ["No", "Yes"]?
                    # Check clobTokenIds order?
                    # I will map Index `i` to `outcomes[i]`.
                    
                    pos_id = calc_position_id(condition_id, i)
                    if pos_id:
                        asset_map[pos_id] = {"title": title, "slug": slug, "outcome": out_label}
        
        print(f"Fetching Jan 5-7 markets... Offset: {offset}, Map Size: {len(asset_map)}")
        
        offset += 100
        # No safety break for now, date filter limits strictness
        if offset > 10000: break
        time.sleep(0.2)

    # Save map
    with open("data/raw/asset_map.json", "w") as f:
        json.dump(asset_map, f, indent=2)
        
    print(f"Saved mapping for {len(asset_map)} assets.")

if __name__ == "__main__":
    build_map()
