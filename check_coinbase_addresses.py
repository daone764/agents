"""Check Coinbase wallet addresses"""

from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com/"))

# Coinbase addresses from .env
coinbase_matic = Web3.to_checksum_address("0xd797249dF41eC9604D58dEaF44B54052049c3BeF")
coinbase_usdc_addr = Web3.to_checksum_address("0xC4494E464974931f1eA0E4A46Dc724dAd08CA808")

# USDC contracts
native_usdc = Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359")
bridged_usdc = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

# ERC20 ABI
abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

native_contract = w3.eth.contract(address=native_usdc, abi=abi)
bridged_contract = w3.eth.contract(address=bridged_usdc, abi=abi)

print("=" * 70)
print("COINBASE WALLET ADDRESSES")
print("=" * 70)

print(f"\n1️⃣ COINBASE MATIC ADDRESS:")
print(f"   {coinbase_matic}")
matic_bal = w3.eth.get_balance(coinbase_matic) / 1e18
native_bal = native_contract.functions.balanceOf(coinbase_matic).call() / 1e6
bridged_bal = bridged_contract.functions.balanceOf(coinbase_matic).call() / 1e6
print(f"   MATIC: {matic_bal:.6f}")
print(f"   Native USDC: ${native_bal:.2f}")
print(f"   Bridged USDC: ${bridged_bal:.2f}")

print(f"\n2️⃣ COINBASE USDC ADDRESS:")
print(f"   {coinbase_usdc_addr}")
matic_bal2 = w3.eth.get_balance(coinbase_usdc_addr) / 1e18
native_bal2 = native_contract.functions.balanceOf(coinbase_usdc_addr).call() / 1e6
bridged_bal2 = bridged_contract.functions.balanceOf(coinbase_usdc_addr).call() / 1e6
print(f"   MATIC: {matic_bal2:.6f}")
print(f"   Native USDC: ${native_bal2:.2f}")
print(f"   Bridged USDC: ${bridged_bal2:.2f}")

print("\n" + "=" * 70)
print("⚠️  IMPORTANT PROBLEM")
print("=" * 70)
print("""
These addresses are COINBASE's wallets (custodial).
- You see them in Coinbase for receiving funds
- Coinbase controls the private keys, NOT you
- You CANNOT use these for Polymarket trading

WHY?
The trading bot needs to SIGN TRANSACTIONS with a private key.
These Coinbase addresses don't have accessible private keys.

YOUR OPTIONS:
1. ✅ Use NEW secure wallet (NOT exposed):
   0x03A9e5d894fA99016896A3ADABa03EB459323001
   Private key is in .env (line 4)
   
2. ❌ OLD exposed wallet:
   0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6
   Has $22 but private key was exposed publicly
   
3. ✅ Generate brand new wallet:
   Fresh wallet, never exposed anywhere

RECOMMENDATION: Use option 1 (NEW secure wallet)
It was NEVER exposed - it's safe!
""")
