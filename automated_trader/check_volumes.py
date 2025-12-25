import sys
sys.path.append('.')

from agents.polymarket.gamma import GammaMarketClient

gamma = GammaMarketClient()
markets = gamma.get_markets(querystring_params={
    "active": True,
    "closed": False,
    "limit": 10
})

print("\nMarkets with 24h volume:")
print("=" * 80)
for m in markets:
    vol_total = float(m.get("volume", 0))
    vol_24h = float(m.get("volume24hr", 0))
    question = m.get("question", "Unknown")[:50]
    
    if vol_total >= 150000:  # Our min total volume
        print(f"\n{question}...")
        print(f"  Total Volume: ${vol_total:,.0f}")
        print(f"  24h Volume: ${vol_24h:,.0f}")
        print(f"  Meets total vol?: {vol_total >= 150000}")
        print(f"  Meets 24h vol?: {vol_24h >= 10000}")
