"""Debug Coinbase API response structure"""

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient
import json

load_dotenv()

API_KEY = os.getenv('CLIENT_API_KEY')
API_SECRET = os.getenv('CLIENT_API_SECRET')

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)

print("Testing API response structures...\n")

# Test 1: Get accounts
print("=" * 70)
print("TEST 1: Get Accounts")
print("=" * 70)
try:
    response = client.get_accounts()
    print(f"Response type: {type(response)}")
    print(f"Response dir: {[x for x in dir(response) if not x.startswith('_')]}")
    
    if hasattr(response, 'accounts'):
        print(f"\nAccounts type: {type(response.accounts)}")
        if response.accounts:
            first_account = response.accounts[0]
            print(f"First account type: {type(first_account)}")
            print(f"First account dir: {[x for x in dir(first_account) if not x.startswith('_')]}")
            
            # Try to access properties
            print(f"\nFirst account details:")
            if hasattr(first_account, 'currency'):
                print(f"  Currency: {first_account.currency}")
            if hasattr(first_account, 'available_balance'):
                balance = first_account.available_balance
                print(f"  Balance type: {type(balance)}")
                print(f"  Balance dir: {[x for x in dir(balance) if not x.startswith('_')]}")
                if hasattr(balance, 'value'):
                    print(f"  Balance value: {balance.value}")
                if hasattr(balance, 'currency'):
                    print(f"  Balance currency: {balance.currency}")
    
    print("\n✅ Accounts test complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Get products
print("\n" + "=" * 70)
print("TEST 2: Get Products")
print("=" * 70)
try:
    response = client.get_products()
    print(f"Response type: {type(response)}")
    print(f"Response dir: {[x for x in dir(response) if not x.startswith('_')]}")
    
    if hasattr(response, 'products'):
        products = response.products
        print(f"\nProducts type: {type(products)}")
        if products:
            # Look for USDC product
            for product in products[:10]:  # First 10
                if hasattr(product, 'product_id'):
                    pid = product.product_id
                    if 'USDC' in pid or 'USD' in pid:
                        print(f"\nFound: {pid}")
                        print(f"  Type: {type(product)}")
                        print(f"  Dir: {[x for x in dir(product) if not x.startswith('_')]}")
    
    print("\n✅ Products test complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Payment methods
print("\n" + "=" * 70)
print("TEST 3: Get Payment Methods")
print("=" * 70)
try:
    response = client.get_payment_methods()
    print(f"Response type: {type(response)}")
    print(f"Response dir: {[x for x in dir(response) if not x.startswith('_')]}")
    
    if hasattr(response, 'payment_methods'):
        methods = response.payment_methods
        print(f"\nPayment methods type: {type(methods)}")
        if methods:
            first_method = methods[0]
            print(f"First method type: {type(first_method)}")
            print(f"First method dir: {[x for x in dir(first_method) if not x.startswith('_')]}")
    
    print("\n✅ Payment methods test complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
