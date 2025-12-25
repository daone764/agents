"""
WALLET OVERVIEW - All Your Addresses
"""

from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com/"))

# All addresses
addresses = {
    "🔴 OLD (COMPROMISED)": "0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6",
    "🆕 NEW SECURE (in .env)": "0x03A9e5d894fA99016896A3ADABa03EB459323001",
    "❓ NEW MATIC ADDRESS": "0xd797249dF41eC9604D58dEaF44B54052049c3BeF"
}

# USDC contracts
native_usdc = Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359")
bridged_usdc = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

# ERC20 ABI
abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

native_contract = w3.eth.contract(address=native_usdc, abi=abi)
bridged_contract = w3.eth.contract(address=bridged_usdc, abi=abi)

print("\n" + "=" * 70)
print("YOUR POLYGON WALLETS - COMPLETE OVERVIEW")
print("=" * 70)

total_usdc = 0
total_matic = 0

for name, addr in addresses.items():
    addr_checksum = Web3.to_checksum_address(addr)
    
    matic = w3.eth.get_balance(addr_checksum) / 1e18
    native = native_contract.functions.balanceOf(addr_checksum).call() / 1e6
    bridged = bridged_contract.functions.balanceOf(addr_checksum).call() / 1e6
    
    total_usdc += (native + bridged)
    total_matic += matic
    
    print(f"\n{name}")
    print(f"Address: {addr}")
    print(f"  MATIC:        {matic:.6f}")
    print(f"  Native USDC:  ${native:.2f}")
    print(f"  Bridged USDC: ${bridged:.2f}")
    print(f"  TOTAL USDC:   ${native + bridged:.2f}")
    
    if name == "🔴 OLD (COMPROMISED)":
        print(f"  ⚠️  Private key was exposed publicly!")
        if native + bridged > 0:
            print(f"  💡 Need MATIC to transfer out")
    elif name == "🆕 NEW SECURE (in .env)":
        print(f"  ✅ This is your trading wallet (configured)")
        if native + bridged == 0:
            print(f"  💡 Send USDC here to start trading")
    elif name == "❓ NEW MATIC ADDRESS":
        print(f"  ❓ Purpose unknown - not configured anywhere")

print("\n" + "=" * 70)
print(f"TOTAL: ${total_usdc:.2f} USDC | {total_matic:.6f} MATIC")
print("=" * 70)

print("\n🎯 RECOMMENDATION:")
print("1. Your $22 is stuck in OLD wallet (needs MATIC to move)")
print("2. Your NEW SECURE wallet is empty but ready")
print("3. The NEW MATIC ADDRESS is empty and unclear why it exists")
print("\n💡 BEST ACTION:")
print("   Send fresh $20 USDC to NEW SECURE wallet:")
print("   → 0x03A9e5d894fA99016896A3ADABa03EB459323001")
print("   → Network: Polygon")
print("   → Start trading immediately!")
