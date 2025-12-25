"""
One-Click Weekly Deposit: Coinbase → Polygon Wallet
Automatically buys USDC and transfers to your trading wallet
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
try:
    client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
except Exception as e:
    print(f"❌ Failed to initialize Coinbase client: {e}")
    sys.exit(1)

def get_accounts():
    """Get all Coinbase accounts with balances"""
    try:
        response = client.get_accounts()
        accounts = {}
        
        # Handle response - Account objects with dict balance
        for account in response.accounts:
            currency = account.currency
            # available_balance is a dict with 'value' and 'currency' keys
            balance_dict = account.available_balance
            available = float(balance_dict.get('value', 0))
            accounts[currency] = available
            
        return accounts
    except Exception as e:
        print(f"❌ Error fetching accounts: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_payment_methods():
    """Get available payment methods - Note: Advanced Trade API doesn't expose this"""
    try:
        # The Advanced Trade API doesn't have payment methods endpoint
        # This is only available in older Coinbase API
        print("💡 Payment methods API not available in Advanced Trade")
        return []
    except Exception as e:
        print(f"❌ Error fetching payment methods: {e}")
        return []

def buy_usdc_market_order(amount_usd):
    """
    Buy USDC using market order on Coinbase Advanced Trade
    Note: Requires USD balance in account first
    """
    try:
        print(f"\n💰 Placing market order for ${amount_usd} USDC...")
        
        # Place market order to buy USDC with USD
        order = client.market_order_buy(
            client_order_id=f"polymarket_{int(time.time())}",
            product_id="USDC-USD",  # Buy USDC using USD
            quote_size=str(amount_usd)  # Amount in USD to spend
        )
        
        print(f"✅ Order placed!")
        print(f"   Order ID: {order.order_id if hasattr(order, 'order_id') else 'Unknown'}")
        print("⏳ Waiting for order to fill...")
        time.sleep(5)
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Order failed: {error_str}")
        
        # Handle specific errors
        if "insufficient" in error_str.lower():
            print("💡 Insufficient USD balance")
            print("   Transfer USD to Coinbase first")
        elif "product" in error_str.lower():
            print("💡 USDC-USD trading pair not available")
        
        return False

def create_crypto_address(address, currency="USDC", network="polygon"):
    """
    Add crypto address to Coinbase address book
    Required before sending
    """
    try:
        response = client.create_address_book_entry(
            address=address,
            currency_symbol=currency,
            name=f"Polymarket Wallet ({network})",
            network=network
        )
        return True
    except Exception as e:
        error_str = str(e)
        # Address might already exist - that's OK
        if "already exists" in error_str.lower() or "duplicate" in error_str.lower():
            return True
        print(f"⚠️  Address book error: {e}")
        return False

def send_usdc_to_polygon(amount):
    """Send USDC from Coinbase to Polygon wallet"""
    try:
        print(f"\n📤 Sending ${amount} USDC to Polygon...")
        print(f"   Address: {WALLET_ADDRESS}")
        
        # Ensure address is in address book
        create_crypto_address(WALLET_ADDRESS)
        
        # Create withdrawal
        response = client.create_crypto_withdrawal(
            address=WALLET_ADDRESS,
            amount=str(amount),
            currency_symbol="USDC",
            network="polygon"
        )
        
        print("✅ Transfer initiated!")
        print("⏳ Should arrive in 2-3 minutes")
        print(f"   Transaction ID: {response.id if hasattr(response, 'id') else 'Unknown'}")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Send failed: {error_str}")
        
        # Handle specific errors
        if "whitelist" in error_str.lower() or "address book" in error_str.lower():
            print("\n💡 SOLUTION:")
            print("1. Go to Coinbase Settings → Security")
            print("2. Add this address to whitelist:")
            print(f"   {WALLET_ADDRESS}")
            print("3. Verify via email")
            print("4. Run this script again")
        elif "insufficient" in error_str.lower():
            print("💡 Insufficient USDC balance")
        elif "2fa" in error_str.lower() or "verification" in error_str.lower():
            print("💡 Check your email/phone for verification code")
        
        return False

def one_click_deposit(amount=20, auto_buy=True):
    """
    One-click deposit: Buy USDC and send to Polygon
    
    Args:
        amount: Amount in USD to deposit
        auto_buy: If True, buy USDC first. If False, use existing balance.
    """
    print("=" * 70)
    print("🤖 ONE-CLICK WEEKLY DEPOSIT")
    print("=" * 70)
    print(f"Amount: ${amount}")
    print(f"Destination: {WALLET_ADDRESS}")
    print(f"Network: Polygon")
    print()
    
    # Step 1: Check current balances
    print("📊 Checking balances...")
    accounts = get_accounts()
    
    if not accounts:
        print("❌ Could not fetch accounts. Check API credentials.")
        return False
    
    usd_balance = accounts.get('USD', 0)
    usdc_balance = accounts.get('USDC', 0)
    
    print(f"   USD:  ${usd_balance:.2f}")
    print(f"   USDC: ${usdc_balance:.2f}")
    
    # Step 2: Buy USDC if needed
    if usdc_balance < amount:
        if auto_buy:
            needed = amount - usdc_balance
            print(f"\n💡 Need ${needed:.2f} more USDC")
            
            # Check if we have USD to buy with
            if usd_balance < needed:
                print(f"\n❌ Insufficient USD balance: ${usd_balance:.2f}")
                print(f"   Need: ${needed:.2f}")
                print("\n📱 MANUAL STEPS:")
                print("1. Add funds to Coinbase (bank transfer or debit)")
                print("2. Wait for funds to clear")
                print("3. Run this script again")
                return False
            
            if not buy_usdc_market_order(needed):
                print("\n❌ Automated buy failed")
                print("\n📱 MANUAL ALTERNATIVE:")
                print("1. Open Coinbase app")
                print("2. Convert → USD to USDC")
                print(f"3. Amount: ${needed:.2f}")
                print("4. Run this script again")
                return False
            
            # Wait for purchase to settle
            print("⏳ Waiting 15 seconds for purchase to settle...")
            time.sleep(15)
        else:
            print(f"\n❌ Insufficient USDC balance: ${usdc_balance:.2f}")
            print(f"   Need: ${amount:.2f}")
            return False
    else:
        print(f"\n✅ Sufficient USDC balance: ${usdc_balance:.2f}")
    
    # Step 3: Send to Polygon wallet
    if send_usdc_to_polygon(amount):
        print("\n" + "=" * 70)
        print("✅ DEPOSIT COMPLETE!")
        print("=" * 70)
        print("\n🎯 Next steps:")
        print("1. Wait 2-3 minutes for arrival")
        print("2. Run: python check_balance.py")
        print("3. Start trading: python scripts/python/cli.py run-autonomous-trader")
        return True
    else:
        print("\n" + "=" * 70)
        print("⚠️  AUTOMATED SEND FAILED - USE MANUAL METHOD")
        print("=" * 70)
        print("\n📱 Manual steps (2 minutes):")
        print("1. Open Coinbase app/website")
        print("2. Go to USDC balance")
        print("3. Click 'Send'")
        print(f"4. Paste address: {WALLET_ADDRESS}")
        print("5. Select 'Polygon' network (IMPORTANT!)")
        print(f"6. Amount: ${amount}")
        print("7. Send & verify")
        return False

def weekly_deposit_flow():
    """Interactive flow for weekly deposits"""
    print("\n" + "=" * 70)
    print("💰 WEEKLY DEPOSIT AUTOMATION")
    print("=" * 70)
    
    # Ask for amount
    try:
        amount_input = input("\nEnter weekly deposit amount (default $20): $")
        amount = float(amount_input) if amount_input.strip() else 20.0
        
        if amount < 1 or amount > 1000:
            print("❌ Amount must be between $1 and $1000")
            return
        
        print(f"\n📋 Summary:")
        print(f"   Amount: ${amount:.2f}")
        print(f"   Destination: {WALLET_ADDRESS}")
        print(f"   Network: Polygon")
        
        confirm = input("\n✅ Confirm deposit? (y/n): ")
        
        if confirm.lower() != 'y':
            print("❌ Cancelled")
            return
        
        # Execute deposit
        success = one_click_deposit(amount, auto_buy=True)
        
        if success:
            print("\n🎉 Setup complete for weekly deposits!")
            print("\n💡 To automate weekly:")
            print("   Just run: python one_click_deposit.py")
            print("   (or schedule this script to run weekly)")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    print("\n🎯 Polymarket Auto-Deposit Tool")
    
    # Validate configuration
    if not API_KEY or not API_SECRET:
        print("❌ Missing Coinbase API credentials")
        print("💡 Add CLIENT_API_KEY and CLIENT_API_SECRET to .env")
        sys.exit(1)
    
    if not WALLET_PK:
        print("❌ Missing wallet private key")
        sys.exit(1)
    
    # Run interactive flow
    weekly_deposit_flow()
