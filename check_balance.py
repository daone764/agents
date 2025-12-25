#!/usr/bin/env python3
"""
Check wallet balance on Polygon
"""

from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

# Your wallet
private_key = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
account = Account.from_key(private_key)

# Connect to Polygon
polygon_rpc = "https://polygon-rpc.com/"
w3 = Web3(Web3.HTTPProvider(polygon_rpc))

"""
USDC contracts on Polygon:
- Native USDC (Polymarket uses): 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
- USDC.e (Bridged, Coinbase sends): 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
"""
usdc_native = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
usdc_bridged = Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")
usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]

usdc_native_contract = w3.eth.contract(address=usdc_native, abi=usdc_abi)
usdc_bridged_contract = w3.eth.contract(address=usdc_bridged, abi=usdc_abi)

# Prefer read-only override if provided (e.g., Coinbase address)
display_address = os.getenv("POLYGON_WALLET_ADDRESS") or account.address
try:
    display_address = Web3.to_checksum_address(display_address)
except Exception:
    pass

matic_balance = w3.eth.get_balance(display_address)
usdc_native_bal = usdc_native_contract.functions.balanceOf(display_address).call()
usdc_bridged_bal = usdc_bridged_contract.functions.balanceOf(display_address).call()

# Convert to human-readable
matic_human = w3.from_wei(matic_balance, 'ether')
usdc_native_human = usdc_native_bal / 1_000_000
usdc_bridged_human = usdc_bridged_bal / 1_000_000
usdc_total = usdc_native_human + usdc_bridged_human

print("=" * 50)
print(f"📍 Wallet Address: {display_address}")
print("=" * 50)
print(f"💎 MATIC Balance: {matic_human:.4f} MATIC")
print(f"💵 USDC (native/Polymarket): {usdc_native_human:.2f} USDC")
print(f"💵 USDC.e (bridged/Coinbase): {usdc_bridged_human:.2f} USDC")
print(f"💰 Total USDC: {usdc_total:.2f} USDC")
print("=" * 50)

if usdc_total >= 4:
    print("✅ Your USDC has arrived! Ready to trade!")
    if usdc_bridged_human > 0 and usdc_native_human == 0:
        print("⚠️  Note: You have USDC.e (bridged). Polymarket uses native USDC.")
        print("   You may need to swap USDC.e → USDC on QuickSwap or Uniswap first.")
elif usdc_total > 0:
    print(f"⏳ Partial amount received. Expecting {4 - usdc_total:.2f} more USDC")
else:
    print("⏳ Waiting for USDC transfer...")
    print("   Check your Coinbase app for transaction status")