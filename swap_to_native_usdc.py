#!/usr/bin/env python3
"""
⚠️  DEPRECATED - DO NOT USE THIS SCRIPT! ⚠️
============================================
This script had INCORRECT token addresses and caused ~$17 loss due to bad swap.

USE INSTEAD: swap_usdc_safe.py

The addresses below were WRONG:
- USDC_BRIDGED was actually Native USDC
- USDC_NATIVE was actually USDC.e Bridged

CORRECT ADDRESSES:
- Native USDC (Coinbase sends): 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
- USDC.e Bridged (Polymarket):  0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
"""

import sys
print("=" * 70)
print("🚨 THIS SCRIPT IS DEPRECATED AND DANGEROUS!")
print("=" * 70)
print()
print("This script had WRONG token addresses and lost ~$17 to bad swap.")
print()
print("Please use the SAFE version instead:")
print("   python swap_usdc_safe.py")
print()
print("=" * 70)
sys.exit(1)

# OLD BROKEN CODE BELOW - DO NOT USE
from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

# Setup
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))
# Fix for POA chains (Polygon)
from web3.middleware import ExtraDataToPOAMiddleware
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

private_key = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
account = Account.from_key(private_key)

# Token addresses
USDC_BRIDGED = Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")  # USDC.e
USDC_NATIVE = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")    # Native USDC

# QuickSwap Router V2
QUICKSWAP_ROUTER = Web3.to_checksum_address("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")

# ERC20 ABI (minimal)
ERC20_ABI = [
    {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"}
]

# QuickSwap Router ABI (minimal)
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

print("=" * 70)
print("🔄 USDC.e → Native USDC Swap on QuickSwap")
print("=" * 70)

# Get balances
usdc_bridged_contract = w3.eth.contract(address=USDC_BRIDGED, abi=ERC20_ABI)
usdc_native_contract = w3.eth.contract(address=USDC_NATIVE, abi=ERC20_ABI)

balance_bridged = usdc_bridged_contract.functions.balanceOf(account.address).call()
balance_native = usdc_native_contract.functions.balanceOf(account.address).call()

print(f"\n📊 Current Balances:")
print(f"   USDC.e (bridged): ${balance_bridged / 1e6:.2f}")
print(f"   USDC (native):    ${balance_native / 1e6:.2f}")

if balance_bridged == 0:
    print("\n❌ No USDC.e to swap!")
    exit(0)

# Keep $1 USDC.e as buffer, swap the rest
swap_amount = balance_bridged - int(1 * 1e6)  # Keep $1
if swap_amount <= 0:
    print("\n⚠️  Balance too low to swap (need > $1)")
    exit(0)

print(f"\n💱 Swapping ${swap_amount / 1e6:.2f} USDC.e → Native USDC")
print(f"   (Keeping $1.00 USDC.e as buffer)")

# Step 1: Approve router to spend USDC.e
print("\n1️⃣ Approving QuickSwap Router...")
router_contract = w3.eth.contract(address=QUICKSWAP_ROUTER, abi=ROUTER_ABI)

current_allowance = usdc_bridged_contract.functions.allowance(account.address, QUICKSWAP_ROUTER).call()
if current_allowance < swap_amount:
    approve_tx = usdc_bridged_contract.functions.approve(
        QUICKSWAP_ROUTER,
        swap_amount
    ).build_transaction({
        'from': account.address,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
    approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
    print(f"   Approval tx: {approve_hash.hex()}")
    print(f"   Waiting for confirmation...")
    w3.eth.wait_for_transaction_receipt(approve_hash)
    print(f"   ✅ Approved!")
else:
    print(f"   ✅ Already approved")

# Step 2: Get expected output
print("\n2️⃣ Calculating swap output...")
path = [USDC_BRIDGED, USDC_NATIVE]
amounts_out = router_contract.functions.getAmountsOut(swap_amount, path).call()
expected_output = amounts_out[1]
min_output = int(expected_output * 0.995)  # 0.5% slippage tolerance

print(f"   Expected output: ${expected_output / 1e6:.2f} USDC")
print(f"   Min output (0.5% slippage): ${min_output / 1e6:.2f} USDC")

# Step 3: Execute swap
print("\n3️⃣ Executing swap...")
deadline = w3.eth.get_block('latest')['timestamp'] + 300  # 5 minutes

swap_tx = router_contract.functions.swapExactTokensForTokens(
    swap_amount,
    min_output,
    path,
    account.address,
    deadline
).build_transaction({
    'from': account.address,
    'gas': 300000,
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(account.address),
})

signed_swap = w3.eth.account.sign_transaction(swap_tx, private_key)
swap_hash = w3.eth.send_raw_transaction(signed_swap.raw_transaction)

print(f"   Swap tx: {swap_hash.hex()}")
print(f"   Waiting for confirmation...")
receipt = w3.eth.wait_for_transaction_receipt(swap_hash)

if receipt['status'] == 1:
    print(f"   ✅ Swap successful!")
else:
    print(f"   ❌ Swap failed!")
    exit(1)

# Check new balances
new_balance_bridged = usdc_bridged_contract.functions.balanceOf(account.address).call()
new_balance_native = usdc_native_contract.functions.balanceOf(account.address).call()

print("\n" + "=" * 70)
print("✅ SWAP COMPLETE!")
print("=" * 70)
print(f"📊 New Balances:")
print(f"   USDC.e (bridged): ${new_balance_bridged / 1e6:.2f}")
print(f"   USDC (native):    ${new_balance_native / 1e6:.2f}")
print(f"\n🎉 You now have ${new_balance_native / 1e6:.2f} native USDC ready for Polymarket!")
print("=" * 70)
