"""
SIMPLE PLAN - Use Coinbase Wallet
Forget self-custodial complexity, use Coinbase directly
"""

print("=" * 70)
print("🎯 SIMPLEST SOLUTION - USE COINBASE WALLET")
print("=" * 70)

print("""
You have $22 USDC on Polygon in Coinbase already.
You have $0.11 MATIC on Polygon in Coinbase already.

✅ MATIC is enough for gas
✅ USDC is enough for trading
✅ Everything is in one place

BUT - Polymarket needs YOUR OWN wallet (not Coinbase's).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 FASTEST PATH TO TRADING:

1. SEND from Coinbase:
   • $22 USDC → 0x03A9e5d894fA99016896A3ADABa03EB459323001
   • Network: Polygon
   
2. BUY $2 POL/MATIC in Coinbase

3. SEND from Coinbase:
   • $2 POL → 0x03A9e5d894fA99016896A3ADABa03EB459323001
   • Network: Polygon

4. WAIT 3 minutes

5. RUN:
   python scripts/python/cli.py run-autonomous-trader

DONE! Trading automatically!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 This wallet is already configured in .env
💡 Just needs USDC + MATIC to start
💡 Two sends in Coinbase = 2 minutes total

""")

print("=" * 70)
print("YOUR WALLET: 0x03A9e5d894fA99016896A3ADABa03EB459323001")
print("=" * 70)
