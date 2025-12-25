import sys
sys.path.append('.')

from agents.polymarket.gamma import GammaMarketClient

gamma = GammaMarketClient()
markets = gamma.get_markets(querystring_params={
    "active": True,
    "closed": False,
    "limit": 10
})

print("\nMarkets with spread data:")
print("=" * 80)
for m in markets:
    question = m.get("question", "Unknown")[:50]
    spread = m.get("spread", 0)
    best_bid = m.get("bestBid", 0)
    best_ask = m.get("bestAsk", 0)
    volume = float(m.get("volume", 0))
    
    if volume >= 100000:  # Our min total volume
        print(f"\n{question}...")
        print(f"  Spread: {spread}")
        print(f"  Best Bid: {best_bid}")
        print(f"  Best Ask: {best_ask}")
        print(f"  Spread %: {float(spread) * 100:.2f}%")
