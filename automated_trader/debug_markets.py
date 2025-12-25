"""
Quick script to debug market data structure and see what's available
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.polymarket.gamma import GammaMarketClient
from agents.polymarket.polymarket import Polymarket
import json

def main():
    print("Initializing clients...")
    gamma = GammaMarketClient()
    
    print("Fetching markets...")
    markets = gamma.get_markets(querystring_params={
        "active": True,
        "closed": False,
        "limit": 10
    })
    
    print(f"\n{'='*80}")
    print(f"Found {len(markets)} markets")
    print(f"{'='*80}\n")
    
    if markets:
        print("First market structure:")
        print(json.dumps(markets[0], indent=2, default=str))
        
        print("\n\nMarket keys available:")
        print(markets[0].keys())
        
        print("\n\nFirst 3 markets summary:")
        for i, market in enumerate(markets[:3], 1):
            print(f"\n{i}. Market ID: {market.get('condition_id', 'N/A')}")
            print(f"   Question: {market.get('question', 'N/A')}")
            print(f"   Volume: ${float(market.get('volume', 0)):,.0f}")
            print(f"   24h Volume: ${float(market.get('volume_24h', 0)):,.0f}")
            print(f"   Active: {market.get('active', 'N/A')}")
            print(f"   Closed: {market.get('closed', 'N/A')}")
            print(f"   End Date: {market.get('end_date_iso', 'N/A')}")
            print(f"   Outcomes: {market.get('outcomes', 'N/A')}")
    else:
        print("No markets returned!")

if __name__ == "__main__":
    main()
