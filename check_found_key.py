"""Check the wallet from the found private key"""

from eth_account import Account
from web3 import Web3

pk = "8ec188eda41d989429493f7e726b969701e4a115f76abc08485e5dec19030b35"
wallet = Account.from_key(pk)

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com/"))

# USDC contracts
native_usdc = Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359")
bridged_usdc = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

native_contract = w3.eth.contract(address=native_usdc, abi=abi)
bridged_contract = w3.eth.contract(address=bridged_usdc, abi=abi)

addr = wallet.address
matic = w3.eth.get_balance(addr) / 1e18
native = native_contract.functions.balanceOf(addr).call() / 1e6
bridged = bridged_contract.functions.balanceOf(addr).call() / 1e6

print("=" * 70)
print("FOUND WALLET")
print("=" * 70)
print(f"Address: {addr}")
print(f"Private Key: {pk}")
print()
print(f"MATIC:        {matic:.6f}")
print(f"Native USDC:  ${native:.2f}")
print(f"Bridged USDC: ${bridged:.2f}")
print(f"TOTAL USDC:   ${native + bridged:.2f}")
print("=" * 70)

if addr.lower() == "0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6".lower():
    print("✅ THIS IS THE OLD WALLET WITH $22!")
else:
    print(f"❓ This is a different wallet: {addr}")
    print(f"   OLD wallet: 0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6")
