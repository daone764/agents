"""
Emergency Transfer Script - Move funds from compromised wallet to new secure wallet
"""

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import os

load_dotenv()

# Compromised wallet
old_private_key = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
old_account = Account.from_key(old_private_key)

# New secure wallet (UPDATE THIS WITH YOUR NEW WALLET!)
NEW_WALLET_ADDRESS = "0x03A9e5d894fA99016896A3ADABa03EB459323001"

# Connect to Polygon
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))

# USDC contracts on Polygon
# Native USDC (Polymarket uses): 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
# USDC.e (Bridged, Coinbase sends): 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
NATIVE_USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_BRIDGED = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

# Which USDC contract to transfer? Set via env or default to BRIDGED (what Coinbase sends)
USDC_TO_TRANSFER = os.getenv('USDC_CONTRACT', USDC_BRIDGED)

# Minimal ERC-20 ABI for transfer
erc20_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

# Checksum addresses
USDC_TO_TRANSFER = w3.to_checksum_address(USDC_TO_TRANSFER)
NEW_WALLET_ADDRESS = w3.to_checksum_address(NEW_WALLET_ADDRESS)

# Detect which USDC type
usdc_type = "USDC.e (Bridged/Coinbase)" if USDC_TO_TRANSFER.lower() == USDC_BRIDGED.lower() else "USDC (Native/Polymarket)"

print("=" * 60)
print("🚨 EMERGENCY FUND TRANSFER")
print("=" * 60)
print(f"\nFrom (COMPROMISED): {old_account.address}")
print(f"To (NEW SECURE):     {NEW_WALLET_ADDRESS}")
print(f"Token: {usdc_type}")
print(f"Contract: {USDC_TO_TRANSFER}")
print()

# Check MATIC balance for gas
matic_balance = w3.eth.get_balance(old_account.address)
matic_human = w3.from_wei(matic_balance, 'ether')
print(f"💎 MATIC Balance: {matic_human:.4f} MATIC")

if matic_balance == 0:
    print("\n❌ NO MATIC FOR GAS FEES!")
    print("\n🔧 OPTIONS TO GET MATIC:")
    print("1. Polygon Faucet: https://faucet.polygon.technology/")
    print("2. Alchemy Faucet: https://www.alchemy.com/faucets/polygon-pos")
    print("3. Buy ~$1 of MATIC and send to:", old_account.address)
    print("\nOnce you have MATIC, run this script again.")
    exit(1)

# Check USDC balance
try:
    usdc_contract = w3.eth.contract(
        address=USDC_TO_TRANSFER,
        abi=erc20_abi
    )
    usdc_balance = usdc_contract.functions.balanceOf(old_account.address).call()
    decimals = usdc_contract.functions.decimals().call()
    usdc_human = usdc_balance / (10 ** decimals)
    
    print(f"💵 {usdc_type} Balance: {usdc_human:.2f} USDC")
    
    if usdc_balance == 0:
        print(f"\n⚠️  No {usdc_type} found to transfer!")
        print("The funds may already be moved or still propagating on blockchain.")
        exit(0)
    
    # Estimate gas
    gas_estimate = usdc_contract.functions.transfer(
        NEW_WALLET_ADDRESS, 
        usdc_balance
    ).estimate_gas({'from': old_account.address})
    
    gas_price = w3.eth.gas_price
    gas_cost = gas_estimate * gas_price
    gas_cost_matic = w3.from_wei(gas_cost, 'ether')
    
    print(f"\n⛽ Estimated gas cost: {gas_cost_matic:.6f} MATIC (${float(gas_cost_matic) * 0.8:.4f} USD)")
    
    if matic_balance < gas_cost:
        print(f"\n❌ Insufficient MATIC! Need {gas_cost_matic:.6f} but have {matic_human:.6f}")
        print("Get more MATIC and try again.")
        exit(1)
    
    # Confirm transfer
    print("\n" + "=" * 60)
    print("⚠️  READY TO TRANSFER")
    print("=" * 60)
    input(f"\nPress ENTER to transfer {usdc_human:.2f} USDC to new wallet...")
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(old_account.address)
    
    transfer_txn = usdc_contract.functions.transfer(
        NEW_WALLET_ADDRESS,
        usdc_balance
    ).build_transaction({
        'from': old_account.address,
        'gas': gas_estimate,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': 137
    })
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(transfer_txn, old_private_key)
    
    # Send transaction
    print("\n📤 Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for confirmation
    print("⏳ Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    
    if receipt['status'] == 1:
        print("\n✅ SUCCESS! Funds transferred safely!")
        print(f"View on Polygonscan: https://polygonscan.com/tx/{tx_hash.hex()}")
        print(f"\n🔒 Your funds are now safe at: {NEW_WALLET_ADDRESS}")
        print("\n⚠️  NEXT STEPS:")
        print("1. Update .env file with NEW private key")
        print("2. Delete the old compromised private key")
        print("3. Never share private keys again!")
    else:
        print("\n❌ Transaction failed!")
        print(f"Receipt: {receipt}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTips:")
    print("- Ensure the USDC contract is 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 (Polygon native USDC)")
    print("- Make sure both addresses are EIP-55 checksummed")
    print("- Confirm you have enough MATIC for gas to transfer USDC")
