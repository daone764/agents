"""Check the new MATIC address balance"""

from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com/"))

# New MATIC address from .env
new_matic_addr = Web3.to_checksum_address("0xd797249dF41eC9604D58dEaF44B54052049c3BeF")

# USDC contracts
native_usdc = Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359")
bridged_usdc = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

# ERC20 ABI
abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

# Check balances
matic_bal = w3.eth.get_balance(new_matic_addr) / 1e18

native_contract = w3.eth.contract(address=native_usdc, abi=abi)
native_bal = native_contract.functions.balanceOf(new_matic_addr).call() / 1e6

bridged_contract = w3.eth.contract(address=bridged_usdc, abi=abi)
bridged_bal = bridged_contract.functions.balanceOf(new_matic_addr).call() / 1e6

print("=" * 70)
print(f"NEW MATIC ADDRESS: {new_matic_addr}")
print("=" * 70)
print(f"MATIC:        {matic_bal:.6f}")
print(f"Native USDC:  ${native_bal:.2f}")
print(f"Bridged USDC: ${bridged_bal:.2f}")
print("=" * 70)

if matic_bal > 0:
    print(f"\n✅ You have {matic_bal:.6f} MATIC here!")
    print("💡 This can be used to pay for gas fees")
else:
    print("\n⚠️  No MATIC in this address yet")
