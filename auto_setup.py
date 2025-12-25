"""
FULLY AUTOMATED SETUP
Uses Coinbase API to fund your trading wallet automatically
"""

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from eth_account import Account
import time
import sys

load_dotenv()

# Configuration
API_KEY = os.getenv('CLIENT_API_KEY')
API_SECRET = os.getenv('CLIENT_API_SECRET')
WALLET_PK = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
wallet = Account.from_key(WALLET_PK)
WALLET_ADDRESS = wallet.address

# Initialize client
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

print("=" * 70)
print("🤖 FULLY AUTOMATED POLYMARKET SETUP")
print("=" * 70)
print(f"Trading Wallet: {WALLET_ADDRESS}")
print()

def get_balance(currency):
    """Get balance for a specific currency"""
    try:
        response = client.get_accounts()
        for account in response.accounts:
            if account.currency == currency:
                balance_dict = account.available_balance
                return float(balance_dict.get('value', 0))
        return 0
    except Exception as e:
        print(f"❌ Error getting {currency} balance: {e}")
        return 0

def send_crypto(currency, amount, network="polygon"):
    """Send crypto to trading wallet"""
    try:
        print(f"\n📤 Sending {amount} {currency} to trading wallet...")
        
        response = client.create_crypto_withdrawal(
            address=WALLET_ADDRESS,
            amount=str(amount),
            currency_symbol=currency,
            network=network
        )
        
        print(f"✅ {currency} sent!")
        tx_id = response.id if hasattr(response, 'id') else 'Unknown'
        print(f"   TX ID: {tx_id}")
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Send failed: {error_str}")
        
        if "whitelist" in error_str.lower() or "address" in error_str.lower():
            print(f"\n💡 ACTION NEEDED:")
            print(f"1. Go to Coinbase → Settings → Security")
            print(f"2. Add to address book/whitelist:")
            print(f"   Address: {WALLET_ADDRESS}")
            print(f"   Network: Polygon")
            print(f"   Currency: {currency}")
            print(f"3. Verify via email")
            print(f"4. Run this script again")
            return False
        
        return False

def buy_matic(amount_usd=2):
    """Buy MATIC/POL"""
    try:
        print(f"\n💰 Buying ${amount_usd} MATIC/POL...")
        
        # Try POL-USD first (new name)
        try:
            order = client.market_order_buy(
                client_order_id=f"polymarket_matic_{int(time.time())}",
                product_id="POL-USD",
                quote_size=str(amount_usd)
            )
            print(f"✅ POL bought!")
            time.sleep(5)
            return True
        except:
            # Try MATIC-USD
            order = client.market_order_buy(
                client_order_id=f"polymarket_matic_{int(time.time())}",
                product_id="MATIC-USD",
                quote_size=str(amount_usd)
            )
            print(f"✅ MATIC bought!")
            time.sleep(5)
            return True
            
    except Exception as e:
        print(f"❌ Buy failed: {e}")
        print(f"\n💡 MANUAL: Buy $2 MATIC/POL in Coinbase app")
        return False

def main():
    # Step 1: Check Coinbase balances
    print("📊 Checking Coinbase balances...")
    usdc_balance = get_balance("USDC")
    matic_balance = get_balance("MATIC")
    pol_balance = get_balance("POL")
    
    # POL is the new name for MATIC
    total_matic = matic_balance + pol_balance
    
    print(f"   USDC: ${usdc_balance:.2f}")
    print(f"   MATIC/POL: {total_matic:.6f}")
    
    if usdc_balance < 1:
        print("\n❌ Need at least $1 USDC in Coinbase")
        print("💡 Buy USDC in Coinbase first")
        return False
    
    # Step 2: Send USDC
    if not send_crypto("USDC", usdc_balance):
        return False
    
    # Step 3: Buy MATIC if needed
    if total_matic < 0.5:  # Need at least 0.5 MATIC
        print(f"\n💡 Need more MATIC for gas (have {total_matic:.6f})")
        if not buy_matic(2):
            return False
        time.sleep(10)  # Wait for buy to settle
        
        # Refresh balance
        matic_balance = get_balance("MATIC")
        pol_balance = get_balance("POL")
        total_matic = matic_balance + pol_balance
    
    # Step 4: Send MATIC/POL
    # Send whichever we have more of
    if pol_balance > matic_balance:
        if not send_crypto("POL", pol_balance):
            return False
    elif matic_balance > 0:
        if not send_crypto("MATIC", matic_balance):
            return False
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print(f"\n⏳ Waiting 3 minutes for transfers to arrive...")
    
    for i in range(180, 0, -30):
        print(f"   {i} seconds remaining...")
        time.sleep(30)
    
    print("\n🚀 STARTING AUTONOMOUS TRADER...")
    print("\nRun this command:")
    print("   python scripts/python/cli.py run-autonomous-trader")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n⚠️  Automated setup incomplete")
            print("See instructions above to complete manually")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
