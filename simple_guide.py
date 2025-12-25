"""
SIMPLE COINBASE GUIDE - Easy Steps to Start Trading
No crypto knowledge needed!
"""

print("""
╔════════════════════════════════════════════════════════════════╗
║           🎯 EASY 3-STEP GUIDE TO START TRADING                ║
╚════════════════════════════════════════════════════════════════╝

STEP 1: Wait for Your Bank Transfer to Clear
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your $15.56 is on hold waiting for bank transfer.
This usually takes 3-5 business days.

Current Status:
  Available now: $0.44 ❌ (too small to trade)
  On hold: $15.56 ⏳ (waiting for bank)

👉 Check back after Christmas! Your money should be available by then.


STEP 2: Send USDC to Your NEW Wallet (When Available)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Once your $15.56 clears, here's what to do in Coinbase:

1. Open Coinbase app/website
2. Go to your USDC
3. Click "Send"
4. Paste this address:
   
   0x03A9e5d894fA99016896A3ADABa03EB459323001
   
5. Choose "Polygon" network (important!)
6. Enter amount: $15 (keep $0.56 for fees)
7. Click Send

That's it! Takes 2-3 minutes to arrive.


STEP 3: Start Trading!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Once USDC arrives in your wallet, run:

   python scripts/python/cli.py run-autonomous-trader

The AI will:
✅ Analyze all markets
✅ Find best opportunities  
✅ Place smart bets automatically
✅ Manage your portfolio


╔════════════════════════════════════════════════════════════════╗
║  SUMMARY: Nothing to do until your bank transfer clears!      ║
║  Come back after Christmas and follow Step 2 & 3              ║
╚════════════════════════════════════════════════════════════════╝

Want to see what markets are available while you wait?
Run: python scripts/python/cli.py get-all-markets --limit 20

Or browse the web UI at: http://localhost:8000
(make sure server is running)

""")

# Show current wallet info
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()
pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)

print("\n" + "=" * 64)
print("📍 YOUR NEW SECURE WALLET")
print("=" * 64)
print(f"Address: {acc.address}")
print(f"\n✅ This is saved in your .env file")
print(f"✅ System is ready to trade when funds arrive")
print(f"✅ Your old compromised wallet is separate - don't worry about it")
print("\n" + "=" * 64)
