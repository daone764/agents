"""
🎯 PROPER SETUP GUIDE - $20 Fresh Start
"""

print("""
╔════════════════════════════════════════════════════════════════╗
║           💰 BUY $20 USDC & START TRADING                      ║
╚════════════════════════════════════════════════════════════════╝

STEP 1: Buy USDC on Coinbase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Open Coinbase app/website
2. Click "Buy"
3. Select "USDC"
4. Amount: $20
5. Payment: Use debit card (instant) or bank (3-5 days)
6. Complete purchase

💡 TIP: Debit card is instant, bank transfer takes days


STEP 2: Send to Your Secure Wallet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Once you have USDC in Coinbase:

1. Go to your USDC balance
2. Click "Send"
3. Paste this address (copy exactly):

   0x03A9e5d894fA99016896A3ADABa03EB459323001

4. IMPORTANT: Select "Polygon" network
   (NOT Ethereum! Polygon is cheaper)
   
5. Amount: $19 (keep $1 for any Coinbase fees)
6. Review & Send
7. Wait 2-3 minutes for arrival


STEP 3: Verify Funds Arrived
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run this command to check:

   python check_balance.py

Should show ~$19 USDC


STEP 4: Start AI Trading! 🤖
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Once funds arrive, start the autonomous trader:

   python scripts/python/cli.py run-autonomous-trader

The AI will:
✅ Scan all markets
✅ Analyze news & data
✅ Find profitable opportunities
✅ Place smart bets automatically
✅ Manage risk across portfolio


╔════════════════════════════════════════════════════════════════╗
║  CRITICAL: Always select "Polygon" network when sending!      ║
║  Wrong network = lost funds!                                   ║
╚════════════════════════════════════════════════════════════════╝

Your Secure Wallet Address (save this):
0x03A9e5d894fA99016896A3ADABa03EB459323001

Private key is safely stored in your .env file
NEVER share the private key with anyone!

""")

from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()
pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)

print("=" * 64)
print("✅ System Ready!")
print("=" * 64)
print(f"Wallet: {acc.address}")
print("Status: Configured and ready to trade")
print("Waiting for: Your $20 USDC to arrive")
print("=" * 64)
print("\n💡 While you wait, browse markets at: http://localhost:8000")
print("   (Run: python -m uvicorn scripts.python.server:app --reload)")
