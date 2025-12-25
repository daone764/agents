from web3 import Web3
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))

print("=" * 60)
print("Checking your wallet...")
print("=" * 60)
print(f"Address: {acc.address}\n")

# Check MATIC
matic = w3.eth.get_balance(acc.address)
matic_human = w3.from_wei(matic, 'ether')
print(f"💎 MATIC: {matic_human:.6f} MATIC")

# Check both USDC contracts
contracts = {
    'USDC.e (Polymarket uses this)': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'Native USDC (Coinbase sent)': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',  # lowercase to try
}

abi = [
    {'constant':True,'inputs':[{'name':'_owner','type':'address'}],'name':'balanceOf',
     'outputs':[{'name':'balance','type':'uint256'}],'type':'function'},
    {'constant':True,'inputs':[],'name':'decimals',
     'outputs':[{'name':'','type':'uint8'}],'type':'function'}
]

for name, addr in contracts.items():
    try:
        contract = w3.eth.contract(address=addr, abi=abi)
        balance = contract.functions.balanceOf(acc.address).call()
        decimals = contract.functions.decimals().call()
        balance_human = balance / (10 ** decimals)
        print(f"💵 {name}: {balance_human:.2f} USDC")
        if balance > 0:
            print(f"   ✅ Contract: {addr}")
    except Exception as e:
        pass

print("\n" + "=" * 60)
print("DIAGNOSIS:")
print("=" * 60)

if matic_human == 0:
    print("❌ No MATIC for gas fees")
    print("   → Can't trade or move funds without MATIC")
    print("   → Need ~$0.10 worth of MATIC")
    print("\n💡 OPTIONS:")
    print("1. Wait 24hrs for faucet to work")
    print("2. Buy $1 MATIC on Coinbase, send here")
    print("3. Wait for bank transfer, use fresh wallet")
else:
    print("✅ Have MATIC - can trade!")
    
print("=" * 60)
