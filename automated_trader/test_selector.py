"""
Test the market selector to see why it's rejecting all markets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from automated_trader.market_selector import MarketSelector
from automated_trader import config
from agents.polymarket.gamma import GammaMarketClient
from agents.polymarket.polymarket import Polymarket

# Setup logging to see everything
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print(f"\n{'='*80}")
    print("Testing Market Selector with Current Config")
    print(f"{'='*80}")
    print(f"MIN_TOTAL_VOLUME: ${config.MIN_TOTAL_VOLUME:,}")
    print(f"MIN_24H_VOLUME: ${config.MIN_24H_VOLUME:,}")
    print(f"MIN_HOURS_TO_RESOLUTION: {config.MIN_HOURS_TO_RESOLUTION} ({config.MIN_HOURS_TO_RESOLUTION/24:.1f} days)")
    print(f"MAX_BID_ASK_SPREAD_PCT: {config.MAX_BID_ASK_SPREAD_PCT}")
    print(f"{'='*80}\n")
    
    gamma = GammaMarketClient()
    polymarket = Polymarket()
    selector = MarketSelector(gamma, polymarket)
    markets = selector.get_tradeable_markets()
    
    print(f"\n{'='*80}")
    print(f"RESULT: Found {len(markets)} tradeable markets")
    print(f"{'='*80}\n")
    
    if markets:
        print("Eligible markets:")
        for m in markets:
            print(f"  - {m.get('question', 'Unknown')[:60]}")
    else:
        print("No eligible markets found. Check logs above for rejection reasons.")

if __name__ == "__main__":
    main()
