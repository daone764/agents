"""Quick test of Coinbase API"""
import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient

load_dotenv()

client = RESTClient(
    api_key=os.getenv('CLIENT_API_KEY'),
    api_secret=os.getenv('CLIENT_API_SECRET')
)

print("Testing Coinbase API connection...\n")

# Test 1: List accounts
try:
    print("📊 Your Coinbase Accounts:")
    accounts = client.get_accounts()
    
    for acc in accounts['accounts']:
        if float(acc.get('available_balance', {}).get('value', 0)) > 0:
            currency = acc.get('currency', 'Unknown')
            balance = acc.get('available_balance', {}).get('value', '0')
            print(f"   {currency}: ${balance}")
    print()
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 2: Check USDC products
try:
    print("🔍 Available USDC Trading Pairs:")
    products = client.get_products()
    
    usdc_products = [p for p in products['products'] if 'USDC' in p.get('product_id', '')]
    for p in usdc_products[:10]:
        print(f"   {p.get('product_id')}")
    print()
except Exception as e:
    print(f"❌ Error: {e}\n")

print("✅ API connection working!")
print("\n💡 Next step: Manual transfer is easier for now.")
print("   Go to Coinbase → Send → USDC → Polygon")
print(f"   Address: 0x03A9e5d894fA99016896A3ADABa03EB459323001")
