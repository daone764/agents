#!/usr/bin/env python3
"""
Monitor wallet balance - checks every 30 seconds
"""

from web3 import Web3
from eth_account import Account
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Your wallet
private_key = os.getenv("POLYGON_WALLET_PRIVATE_KEY")
account = Account.from_key(private_key)

# Connect to Polygon
polygon_rpc = "https://polygon-rpc.com/"
w3 = Web3(Web3.HTTPProvider(polygon_rpc))

# USDC contract on Polygon (Native USDC - used by Coinbase)
usdc_address = "0x3c3499c542cEF5E3811e1192ce70d8cC03d5c3359"
usdc_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]

usdc_contract = w3.eth.contract(address=usdc_address, abi=usdc_abi)

print("🔍 Monitoring wallet balance...")
print(f"📍 Address: {account.address}")
print("⏰ Checking every 30 seconds for 10 minutes")
print("=" * 60)

# Monitor for 10 minutes (20 checks at 30 second intervals)
for i in range(20):
    try:
        # Get balances
        matic_balance = w3.eth.get_balance(account.address)
        usdc_balance = usdc_contract.functions.balanceOf(account.address).call()
        
        # Convert to human-readable
        matic_human = w3.from_wei(matic_balance, 'ether')
        usdc_human = usdc_balance / 1_000_000  # USDC has 6 decimals
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if usdc_human > 0:
            print(f"\n🎉 SUCCESS! [{timestamp}]")
            print("=" * 60)
            print(f"💵 USDC Balance: {usdc_human:.2f} USDC")
            print(f"💎 MATIC Balance: {matic_human:.4f} MATIC")
            print("=" * 60)
            print("✅ Your funds have arrived! Ready to trade!")
            print("\nRun this command to start trading:")
            print("python scripts/python/cli.py run-autonomous-trader")
            break
        else:
            print(f"⏳ [{timestamp}] Checking... USDC: {usdc_human:.2f} | MATIC: {matic_human:.4f}")
            
    except Exception as e:
        print(f"⚠️  Error checking balance: {e}")
    
    if i < 19:  # Don't sleep on last iteration
        time.sleep(30)
else:
    print("\n⏰ 10 minutes elapsed")
    print("Transaction might still be processing. Try running:")
    print("python check_balance.py")
