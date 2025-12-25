#!/usr/bin/env python3
"""Extract Ethereum private key from EC private key"""
import base64
from eth_account import Account
from web3 import Web3

# The EC private key from .env line 8
ec_key_pem = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKEVnjxUopzWi9lvyRuUhpH4aQVHGf7x4Ura56zsd49uoAoGCCqGSM49
AwEHoUQDQgAEtQkyanqaPzalblQqReF32s3uu+Uh4l7g5QfsAwRv8gSNxR2fV90F
Wzj0MnMq2O4bbye0ZxEMjsF2DCbyqaFrzQ==
-----END EC PRIVATE KEY-----"""

# Remove PEM headers and decode base64
pem_body = ec_key_pem.replace("-----BEGIN EC PRIVATE KEY-----", "")
pem_body = pem_body.replace("-----END EC PRIVATE KEY-----", "")
pem_body = pem_body.replace("\n", "").strip()

der_bytes = base64.b64decode(pem_body)

# The private key is at bytes 7-39 (32 bytes) in the DER structure
# DER format: 30 len 02 01 01 04 20 [32 bytes of private key]
private_key_bytes = der_bytes[7:39]
private_key_hex = private_key_bytes.hex()

print("=" * 70)
print("EXTRACTED ETHEREUM PRIVATE KEY")
print("=" * 70)
print(f"Private Key (hex): {private_key_hex}")
print()

# Test it
try:
    account = Account.from_key(private_key_hex)
    print(f"✅ Valid Ethereum key!")
    print(f"Address: {account.address}")
    print()
    
    # Check balance
    w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com/"))
    matic = w3.eth.get_balance(account.address) / 1e18
    
    # Check both USDC contracts
    usdc_native = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
    usdc_bridged = Web3.to_checksum_address("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")
    abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    
    native_contract = w3.eth.contract(address=usdc_native, abi=abi)
    bridged_contract = w3.eth.contract(address=usdc_bridged, abi=abi)
    
    usdc_native_bal = native_contract.functions.balanceOf(account.address).call() / 1e6
    usdc_bridged_bal = bridged_contract.functions.balanceOf(account.address).call() / 1e6
    
    print(f"MATIC: {matic:.6f}")
    print(f"USDC (native/Polymarket): ${usdc_native_bal:.2f}")
    print(f"USDC.e (bridged/Coinbase): ${usdc_bridged_bal:.2f}")
    print(f"Total USDC: ${usdc_native_bal + usdc_bridged_bal:.2f}")
    print("=" * 70)
    
    # Check if this is the wallet with $22
    if account.address.lower() == "0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6".lower():
        print("🎯 THIS IS THE WALLET WITH THE $22 USDC.e!")
    else:
        print(f"📍 This is address: {account.address}")
        print(f"   Target wallet: 0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6")
        
except Exception as e:
    print(f"❌ Error: {e}")
