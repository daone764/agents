from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account
import os

load_dotenv()

pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com/'))

# Try different USDC contracts
contracts = {
    'USDC (Polygon native)': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
}

abi = [{'constant':True,'inputs':[{'name':'_owner','type':'address'}],'name':'balanceOf','outputs':[{'name':'balance','type':'uint256'}],'type':'function'},{'constant':True,'inputs':[],'name':'decimals','outputs':[{'name':'','type':'uint8'}],'type':'function'}]

override = os.getenv('POLYGON_WALLET_ADDRESS') or os.getenv('Coinbase_WALLET_ADDRESS') or os.getenv('COINBASE_WALLET_ADDRESS')
address_to_check = override or acc.address
try:
    address_to_check = w3.to_checksum_address(address_to_check)
except Exception:
    pass

print(f"Checking wallet: {address_to_check}\n")

for name, addr in contracts.items():
    try:
        contract = w3.eth.contract(address=w3.to_checksum_address(addr), abi=abi)
        balance = contract.functions.balanceOf(address_to_check).call()
        decimals = contract.functions.decimals().call()
        balance_human = balance / (10 ** decimals)
        print(f"{name}: {balance_human:.2f} USDC")
        if balance > 0:
            print(f"  ✅ FOUND! Contract: {addr}")
    except Exception as e:
        print(f"{name}: Error - {e}")
