"""Quick balance check for both wallets"""

import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Setup
rpc = "https://polygon-rpc.com/"
w3 = Web3(Web3.HTTPProvider(rpc))

# Wallets
new_wallet = "0x03A9e5d894fA99016896A3ADABa03EB459323001"
old_wallet = "0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6"

# USDC contracts (both types)
native_usdc = Web3.to_checksum_address("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359")
bridged_usdc = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

# ERC20 ABI (minimal)
abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

def check_balance(wallet_addr, usdc_addr, name):
    contract = w3.eth.contract(address=usdc_addr, abi=abi)
    balance = contract.functions.balanceOf(wallet_addr).call()
    return balance / 1e6  # 6 decimals

print("=" * 70)
print("WALLET BALANCES")
print("=" * 70)

print(f"\n🆕 NEW WALLET: {new_wallet}")
native_bal = check_balance(new_wallet, native_usdc, "Native USDC")
bridged_bal = check_balance(new_wallet, bridged_usdc, "Bridged USDC")
matic_bal = w3.eth.get_balance(new_wallet) / 1e18
print(f"   Native USDC:  ${native_bal:.2f}")
print(f"   Bridged USDC: ${bridged_bal:.2f}")
print(f"   MATIC:        {matic_bal:.4f}")
print(f"   TOTAL USDC:   ${native_bal + bridged_bal:.2f}")

print(f"\n🔴 OLD WALLET: {old_wallet}")
native_bal_old = check_balance(old_wallet, native_usdc, "Native USDC")
bridged_bal_old = check_balance(old_wallet, bridged_usdc, "Bridged USDC")
matic_bal_old = w3.eth.get_balance(old_wallet) / 1e18
print(f"   Native USDC:  ${native_bal_old:.2f}")
print(f"   Bridged USDC: ${bridged_bal_old:.2f}")
print(f"   MATIC:        {matic_bal_old:.4f}")
print(f"   TOTAL USDC:   ${native_bal_old + bridged_bal_old:.2f}")

print("\n" + "=" * 70)
total = native_bal + bridged_bal + native_bal_old + bridged_bal_old
print(f"TOTAL ACROSS ALL WALLETS: ${total:.2f}")
print("=" * 70)
