import sys
sys.path.append('.')

from agents.polymarket.gamma import GammaMarketClient
from agents.polymarket.polymarket import Polymarket
import json

gamma = GammaMarketClient()
polymarket = Polymarket()

# Get one market
markets = gamma.get_markets(querystring_params={
    "active": True,
    "closed": False,
    "limit": 1
})

if markets:
    market = markets[0]
    print(f"Market: {market.get('question')}")
    
    clob_token_ids = market.get('clobTokenIds', [])
    if isinstance(clob_token_ids, str):
        clob_token_ids = json.loads(clob_token_ids)
    
    print(f"\nCLOB Token IDs: {clob_token_ids}")
    
    if clob_token_ids and len(clob_token_ids) >= 2:
        yes_token = clob_token_ids[0]
        print(f"\nGetting order book for YES token: {yes_token[:20]}...")
        
        try:
            order_book = polymarket.get_orderbook(yes_token)
            print(f"\nOrder book type: {type(order_book)}")
            print(f"Order book dir: {dir(order_book)}")
            print(f"\nOrder book: {order_book}")
        except Exception as e:
            print(f"Error: {e}")
