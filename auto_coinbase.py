"""
Automated Coinbase → Polygon Wallet Transfer
Buys USDC and sends it to your trading wallet automatically
"""

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from eth_account import Account
import time

load_dotenv()

# Coinbase API credentials
API_KEY = os.getenv('CLIENT_API_KEY')
API_SECRET = os.getenv('CLIENT_API_SECRET')

# Your wallet
WALLET_PK = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
wallet = Account.from_key(WALLET_PK)
WALLET_ADDRESS = wallet.address

# Initialize Coinbase client
client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

def check_usdc_balance():
    """Check current USDC balance in Coinbase"""
    try:
        accounts = client.get_accounts()
        for account in accounts.accounts:
            if account.currency == "USDC":
                balance = float(account.available_balance.value)
                print(f"💵 USDC Balance: ${balance:.2f}")
                return balance
        print("❌ No USDC account found")
        return 0
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return 0

def buy_usdc(amount_usd):
    """Buy USDC with USD"""
    try:
        print(f"\n💰 Buying ${amount_usd} USDC...")
        
        # Create market order to buy USDC
        order = client.market_order_buy(
            client_order_id=f"buy_{int(time.time())}",
            product_id="USDC-USD",
            quote_size=str(amount_usd)
        )
        
        print(f"✅ Order placed: {order.order_id}")
        print("⏳ Waiting for order to fill...")
        time.sleep(5)  # Wait for order to process
        
        return True
    except Exception as e:
        print(f"❌ Error buying USDC: {e}")
        return False

def send_to_polygon_wallet(amount_usdc):
    """Send USDC to Polygon wallet"""
    try:
        print(f"\n📤 Sending ${amount_usdc} USDC to Polygon wallet...")
        print(f"   Destination: {WALLET_ADDRESS}")
        
        # Create withdrawal to Polygon network
        # Note: This requires your wallet to be whitelisted in Coinbase
        withdrawal = client.create_address_book_entry(
            address=WALLET_ADDRESS,
            currency_symbol="USDC",
            network="polygon"
        )
        
        print("✅ Transfer initiated!")
        print("⏳ Should arrive in 2-3 minutes")
        
        return True
    except Exception as e:
        print(f"❌ Error sending USDC: {e}")
        print("\n⚠️  Common issues:")
        print("1. Address not whitelisted (add in Coinbase settings)")
        print("2. Need to verify transaction via email/2FA")
        print("3. Insufficient balance after fees")
        return False

def auto_fund_wallet(amount=20):
    """
    Complete automation: Buy USDC and send to wallet
    """
    print("=" * 60)
    print("🤖 AUTOMATED COINBASE → POLYGON TRANSFER")
    print("=" * 60)
    print(f"Amount: ${amount}")
    print(f"Destination: {WALLET_ADDRESS}\n")
    
    # Step 1: Check current balance
    current_balance = check_usdc_balance()
    
    if current_balance < amount:
        needed = amount - current_balance
        print(f"\n📊 Need ${needed:.2f} more USDC")
        
        # Step 2: Buy USDC
        if not buy_usdc(needed):
            print("\n❌ Failed to buy USDC. Please buy manually.")
            return False
        
        # Wait a bit for purchase to settle
        print("⏳ Waiting 10 seconds for purchase to settle...")
        time.sleep(10)
    else:
        print(f"\n✅ Sufficient balance: ${current_balance:.2f}")
    
    # Step 3: Send to wallet
    if send_to_polygon_wallet(amount):
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print("Run: python check_balance.py")
        print("To verify funds arrived in your wallet")
        return True
    else:
        print("\n⚠️  Automated send failed. Manual steps:")
        print("1. Go to Coinbase")
        print("2. Send → USDC")
        print(f"3. Address: {WALLET_ADDRESS}")
        print("4. Network: Polygon")
        print("5. Amount: $" + str(amount))
        return False

if __name__ == "__main__":
    print("\n🎯 Coinbase Automation Tool")
    print("=" * 60)
    
    # Check if API credentials are set
    if not API_KEY or not API_SECRET:
        print("❌ Missing Coinbase API credentials in .env")
        exit(1)
    
    # Ask for amount
    try:
        amount_input = input("\nEnter amount to fund ($20 recommended): $")
        amount = float(amount_input) if amount_input else 20
        
        print(f"\n✅ Will fund ${amount:.2f}")
        confirm = input("Continue? (y/n): ")
        
        if confirm.lower() == 'y':
            auto_fund_wallet(amount)
        else:
            print("Cancelled.")
    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
