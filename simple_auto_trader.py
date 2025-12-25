"""
Simplified Autonomous Trader for Windows
Works without jq dependency and RAG complexity
"""
from agents.polymarket.polymarket import Polymarket
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def simple_auto_trader():
    """
    Improved autonomous trader that:
    1. Gets active markets
    2. Filters out markets that have already resolved or are past their timeframe
    3. Looks for genuine mispricings with good liquidity
    4. Suggests trades based on value and timing
    """
    pm = Polymarket()
    
    print("\nSimple Autonomous Trader Starting...\n")
    
    # Get active markets
    print("Fetching markets...")
    markets = pm.get_all_markets()
    
    if not markets:
        print("No active markets found")
        return
    
    print(f"Found {len(markets)} active markets\n")
    
    # Check balance
    usdc_balance = pm.get_usdc_balance()
    
    print(f"Wallet Balance: ${usdc_balance:.2f} USDC\n")
    
    if usdc_balance < 1:
        print("Insufficient USDC balance for trading (need at least $1)")
        return
    
    # Analyze markets with better logic
    print("Analyzing Markets (filtering for good opportunities):\n")
    current_time = datetime.now()
    opportunities = []
    
    for market in markets[:20]:  # Check more markets
        try:
            # Parse market details
            end_date_str = market.end.split('T')[0] if 'T' in market.end else market.end
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            # Skip markets that have already ended or end very soon
            days_until_end = (end_date - current_time).days
            if days_until_end < 7:  # Skip if less than a week left
                continue
            
            # Parse outcomes and prices
            outcomes = eval(market.outcomes) if isinstance(market.outcomes, str) else market.outcomes
            prices = [float(p) for p in eval(market.outcome_prices)]
            
            # Only consider markets with reasonable spreads
            if market.spread > 0.05:  # Skip high spread markets (>5%)
                continue
            
            yes_price = prices[0]
            no_price = prices[1]
            
            # Look for genuine opportunities where one side is underpriced
            # But NOT markets where it's obvious what will happen
            
            # Strategy 1: Look for balanced markets (30-70% range) with slight mispricings
            if 0.30 <= yes_price <= 0.70 and 0.30 <= no_price <= 0.70:
                # These are uncertain markets - good for trading
                if yes_price < 0.45:  # Yes seems underpriced
                    edge = 0.50 - yes_price
                    opportunity = {
                        'market': market,
                        'recommendation': 'Yes',
                        'price': yes_price,
                        'edge': edge,
                        'confidence': min(edge * 150, 85),  # Cap at 85%
                        'reasoning': f"Balanced market with Yes slightly underpriced. {days_until_end} days until resolution.",
                        'token_id': eval(market.clob_token_ids)[0],
                        'days_left': days_until_end
                    }
                    opportunities.append(opportunity)
                    
                elif no_price < 0.45:  # No seems underpriced
                    edge = 0.50 - no_price
                    opportunity = {
                        'market': market,
                        'recommendation': 'No',
                        'price': no_price,
                        'edge': edge,
                        'confidence': min(edge * 150, 85),
                        'reasoning': f"Balanced market with No slightly underpriced. {days_until_end} days until resolution.",
                        'token_id': eval(market.clob_token_ids)[1],
                        'days_left': days_until_end
                    }
                    opportunities.append(opportunity)
            
            # Strategy 2: Look for extreme mispricings where the unlikely outcome has decent odds
            # (e.g., something at 5% that should be 15%)
            elif yes_price < 0.10 and days_until_end > 30:  # Long-shot with time
                # Only recommend if there's genuine uncertainty, not obvious losers
                opportunity = {
                    'market': market,
                    'recommendation': 'Yes',
                    'price': yes_price,
                    'edge': 0.15 - yes_price,  # Assume it should be at least 15%
                    'confidence': 40,  # Low confidence on long-shots
                    'reasoning': f"Long-shot opportunity - {days_until_end} days for things to change. High risk, high reward.",
                    'token_id': eval(market.clob_token_ids)[0],
                    'days_left': days_until_end
                }
                opportunities.append(opportunity)
                
        except Exception as e:
            continue
    
    # Sort opportunities by edge (best value first)
    opportunities.sort(key=lambda x: x['edge'], reverse=True)
    
    if not opportunities:
        print("No good trading opportunities found.")
        print("Most markets are either:")
        print("  - Too close to expiration")
        print("  - Have wide spreads (low liquidity)")
        print("  - Are efficiently priced with no edge")
        print("\nTry again later when new markets are created!")
        return
    
    # Show top 3 opportunities
    print(f"Found {len(opportunities)} potential opportunities. Showing top 3:\n")
    
    for i, opp in enumerate(opportunities[:3], 1):
        market = opp['market']
        print(f"{i}. {market.question}")
        print(f"   Ends: {market.end} ({opp['days_left']} days left)")
        print(f"   Spread: {market.spread:.4f}")
        print(f"   RECOMMENDATION: Buy {opp['recommendation']}")
        print(f"   Current Price: ${opp['price']:.4f}")
        print(f"   Edge: {opp['edge']:.4f} ({opp['confidence']:.0f}% confidence)")
        print(f"   Reasoning: {opp['reasoning']}")
        
        # Calculate suggested amount (5% of balance for balanced markets, 2% for long-shots)
        if opp['confidence'] > 60:
            suggested_amount = min(usdc_balance * 0.05, 3.0)
        else:
            suggested_amount = min(usdc_balance * 0.02, 1.0)
        
        print(f"   Suggested Amount: ${suggested_amount:.2f} USDC")
        print(f"   Token ID: {opp['token_id']}")
        print(f"\n   To execute:")
        print(f"   python scripts/python/cli.py place-market-order-by-token {opp['token_id']} {suggested_amount:.2f}")
        print()
    
    print("\nNote: These are algorithmic suggestions. Always do your own research!")
    print("Consider: news, fundamentals, and whether the market pricing makes sense.")


if __name__ == "__main__":
    simple_auto_trader()
