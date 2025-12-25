"""Check which wallet the .env private key belongs to"""

import os
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()

pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')

if pk:
    wallet = Account.from_key(pk)
    print("=" * 70)
    print("WALLET FROM .ENV PRIVATE KEY")
    print("=" * 70)
    print(f"\nAddress: {wallet.address}")
    print(f"Private Key: {pk}")
    
    print("\n" + "=" * 70)
    print("COMPARISON:")
    print("=" * 70)
    print(f"NEW wallet:  0x03A9e5d894fA99016896A3ADABa03EB459323001")
    print(f"OLD wallet:  0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6")
    print(f"This key is: {wallet.address}")
    
    if wallet.address.lower() == "0x03A9e5d894fA99016896A3ADABa03EB459323001".lower():
        print("\n✅ This is the NEW SECURE WALLET (never exposed)")
        print("💡 Safe to use for trading!")
    elif wallet.address.lower() == "0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6".lower():
        print("\n⚠️  This is the OLD EXPOSED WALLET")
        print("💡 Private key was posted publicly in our conversation")
    else:
        print("\n❓ This is a different wallet entirely")
else:
    print("No private key found in .env")
