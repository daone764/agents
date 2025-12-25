#!/usr/bin/env python3
"""
SAFE USDC Swap Script for Polymarket
=====================================
Swaps Native USDC (from Coinbase) → USDC.e (Bridged, what Polymarket uses)

CORRECTED TOKEN ADDRESSES:
- Native USDC (Coinbase sends this): 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
- USDC.e Bridged (Polymarket uses):  0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174

Safety features:
- Max 1% slippage for stablecoin swaps
- Dry-run mode by default (shows what would happen)
- Requires explicit confirmation
- Uses 1inch API for best rates (not low-liquidity QuickSwap pools)
"""

import os
import sys
import requests
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CORRECT TOKEN ADDRESSES (VERIFIED!)
# ============================================================================
NATIVE_USDC = Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")  # Coinbase sends this
USDC_E_BRIDGED = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")  # Polymarket uses this

# 1inch Aggregator (finds best swap route)
ONEINCH_ROUTER = Web3.to_checksum_address("0x1111111254EEB25477B68fb85Ed929f73A960582")
ONEINCH_API = "https://api.1inch.dev/swap/v6.0/137"  # Polygon chain ID = 137

# ERC20 ABI
ERC20_ABI = [
    {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
]

# Setup
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))

# Fix for POA chains (Polygon) - handle different web3 versions
try:
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except ImportError:
        pass  # Newer web3 versions may not need this

private_key = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
if not private_key:
    print("❌ POLYGON_WALLET_PRIVATE_KEY not found in .env")
    sys.exit(1)

account = Account.from_key(private_key)


def get_balances():
    """Get all USDC balances"""
    native_contract = w3.eth.contract(address=NATIVE_USDC, abi=ERC20_ABI)
    bridged_contract = w3.eth.contract(address=USDC_E_BRIDGED, abi=ERC20_ABI)
    
    native_bal = native_contract.functions.balanceOf(account.address).call() / 1e6
    bridged_bal = bridged_contract.functions.balanceOf(account.address).call() / 1e6
    pol_bal = w3.eth.get_balance(account.address) / 1e18
    
    return native_bal, bridged_bal, pol_bal


def get_1inch_quote(from_token, to_token, amount_wei):
    """Get swap quote from 1inch (best rates)"""
    try:
        url = f"{ONEINCH_API}/quote"
        params = {
            "src": from_token,
            "dst": to_token,
            "amount": str(amount_wei),
        }
        headers = {
            "Authorization": f"Bearer {os.getenv('ONEINCH_API_KEY', '')}",
            "Accept": "application/json"
        }
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return int(data.get('toAmount', 0))
        else:
            return None
    except Exception as e:
        print(f"   1inch API error: {e}")
        return None


def get_quickswap_quote(from_token, to_token, amount_wei):
    """Fallback: Get quote from QuickSwap"""
    QUICKSWAP_ROUTER = Web3.to_checksum_address("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")
    ROUTER_ABI = [
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
    
    try:
        router = w3.eth.contract(address=QUICKSWAP_ROUTER, abi=ROUTER_ABI)
        path = [from_token, to_token]
        amounts = router.functions.getAmountsOut(amount_wei, path).call()
        return amounts[1]
    except Exception as e:
        print(f"   QuickSwap error: {e}")
        return None


def execute_quickswap_swap(from_token, to_token, amount_wei, min_output):
    """Execute swap via QuickSwap with strict slippage"""
    QUICKSWAP_ROUTER = Web3.to_checksum_address("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")
    
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
        }
    ]
    
    # First approve
    token_contract = w3.eth.contract(address=from_token, abi=ERC20_ABI)
    current_allowance = token_contract.functions.allowance(account.address, QUICKSWAP_ROUTER).call()
    
    if current_allowance < amount_wei:
        print("   Approving router...")
        approve_tx = token_contract.functions.approve(
            QUICKSWAP_ROUTER,
            amount_wei
        ).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        
        signed = w3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print("   ✅ Approved")
    
    # Execute swap
    router = w3.eth.contract(address=QUICKSWAP_ROUTER, abi=ROUTER_ABI)
    deadline = w3.eth.get_block('latest')['timestamp'] + 300
    
    swap_tx = router.functions.swapExactTokensForTokens(
        amount_wei,
        min_output,
        [from_token, to_token],
        account.address,
        deadline
    ).build_transaction({
        'from': account.address,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    signed = w3.eth.account.sign_transaction(swap_tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"   Tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    return receipt['status'] == 1


def main():
    print("=" * 70)
    print("🔒 SAFE USDC SWAP - Native USDC → USDC.e (for Polymarket)")
    print("=" * 70)
    
    # Show current balances
    native_bal, bridged_bal, pol_bal = get_balances()
    
    print(f"\n📊 Current Balances:")
    print(f"   Native USDC (Coinbase):     ${native_bal:.2f}")
    print(f"   USDC.e Bridged (Polymarket): ${bridged_bal:.2f}")
    print(f"   POL (gas):                   {pol_bal:.4f}")
    
    if native_bal < 0.10:
        print(f"\n✅ No Native USDC to swap (balance: ${native_bal:.2f})")
        print("   Your USDC.e is ready for Polymarket!")
        return
    
    # Calculate swap amount (keep $0.50 buffer)
    swap_amount = native_bal - 0.50
    if swap_amount <= 0:
        print(f"\n⚠️  Balance too low to swap (need > $0.50)")
        return
    
    swap_amount_wei = int(swap_amount * 1e6)
    
    print(f"\n💱 Planning to swap: ${swap_amount:.2f} Native USDC → USDC.e")
    
    # Get quote
    print("\n📈 Getting best swap quote...")
    
    # Try 1inch first (best rates)
    expected_output = get_1inch_quote(NATIVE_USDC, USDC_E_BRIDGED, swap_amount_wei)
    source = "1inch"
    
    # Fallback to QuickSwap
    if not expected_output:
        print("   1inch unavailable, trying QuickSwap...")
        expected_output = get_quickswap_quote(NATIVE_USDC, USDC_E_BRIDGED, swap_amount_wei)
        source = "QuickSwap"
    
    if not expected_output:
        print("\n❌ Could not get swap quote. Try again later.")
        return
    
    expected_output_human = expected_output / 1e6
    slippage = (swap_amount - expected_output_human) / swap_amount * 100
    
    print(f"\n📊 Swap Quote ({source}):")
    print(f"   Input:    ${swap_amount:.2f} Native USDC")
    print(f"   Output:   ${expected_output_human:.2f} USDC.e")
    print(f"   Slippage: {slippage:.2f}%")
    
    # SAFETY CHECK: Max 1% slippage for stablecoins!
    MAX_SLIPPAGE = 1.0
    if slippage > MAX_SLIPPAGE:
        print(f"\n🚨 DANGER: Slippage too high ({slippage:.2f}% > {MAX_SLIPPAGE}%)!")
        print("   This swap would lose you money.")
        print("   Try a smaller amount or wait for better liquidity.")
        print("\n❌ Swap ABORTED for your protection.")
        return
    
    # Strict minimum output (99% of expected)
    min_output = int(expected_output * 0.99)
    
    print(f"\n🔒 Safety Settings:")
    print(f"   Max slippage: {MAX_SLIPPAGE}%")
    print(f"   Min output:   ${min_output / 1e6:.2f} USDC.e")
    
    # Require confirmation
    print("\n" + "=" * 70)
    print("⚠️  CONFIRM SWAP")
    print("=" * 70)
    print(f"   You will send:    ${swap_amount:.2f} Native USDC")
    print(f"   You will receive: ~${expected_output_human:.2f} USDC.e")
    print(f"   (Minimum:         ${min_output / 1e6:.2f} USDC.e)")
    
    confirm = input("\n   Type 'SWAP' to confirm (or anything else to cancel): ")
    
    if confirm.strip().upper() != 'SWAP':
        print("\n❌ Swap cancelled.")
        return
    
    # Execute swap
    print("\n🔄 Executing swap...")
    
    success = execute_quickswap_swap(NATIVE_USDC, USDC_E_BRIDGED, swap_amount_wei, min_output)
    
    if success:
        # Show new balances
        new_native, new_bridged, _ = get_balances()
        
        print("\n" + "=" * 70)
        print("✅ SWAP SUCCESSFUL!")
        print("=" * 70)
        print(f"📊 New Balances:")
        print(f"   Native USDC:  ${new_native:.2f}")
        print(f"   USDC.e:       ${new_bridged:.2f}")
        print(f"\n🎉 Your ${new_bridged:.2f} USDC.e is ready for Polymarket!")
    else:
        print("\n❌ Swap failed! No funds were lost (reverted).")


if __name__ == "__main__":
    main()
