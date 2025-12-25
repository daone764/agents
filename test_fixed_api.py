"""Quick test of fixed API functions"""

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient

load_dotenv()

API_KEY = os.getenv('CLIENT_API_KEY')
API_SECRET = os.getenv('CLIENT_API_SECRET')

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

print("Testing fixed API functions...\n")

# Test get_accounts with fixed dict handling
print("=" * 70)
print("Getting account balances...")
print("=" * 70)

try:
    response = client.get_accounts()
    accounts = {}
    
    for account in response.accounts:
        currency = account.currency
        balance_dict = account.available_balance  # This is a dict
        available = float(balance_dict.get('value', 0))
        accounts[currency] = available
    
    print("\n✅ Success! Account balances:")
    for currency, balance in sorted(accounts.items()):
        if balance > 0:
            print(f"   {currency}: ${balance:.2f}" if currency in ['USD', 'USDC'] else f"   {currency}: {balance:.6f}")
    
    print(f"\nTotal accounts found: {len(accounts)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
