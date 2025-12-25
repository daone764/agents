from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account
import os

load_dotenv()

# Try multiple RPC endpoints
rpcs = [
    'https://polygon.llamarpc.com',
    'https://rpc-mainnet.matic.network',
    'https://polygon-rpc.com/'
]

pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)

# Try both USDC contracts
usdc_contracts = {
    'USDC (bridged)': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'USDC (native)': '0x3c3499c542cEF5E3811e1192ce70d8cC03d5c3359'
}
usdc_abi = [{'constant':True,'inputs':[{'name':'_owner','type':'address'}],'name':'balanceOf','outputs':[{'name':'balance','type':'uint256'}],'type':'function'}]

print(f"Wallet: {acc.address}\n")

for rpc in rpcs:
    try:
        print(f"Trying {rpc}...")
        w3 = Web3(Web3.HTTPProvider(rpc))
        
        for name, address in usdc_contracts.items():
            usdc = w3.eth.contract(address=address, abi=usdc_abi)
            bal = usdc.functions.balanceOf(acc.address).call()
            usdc_human = bal / 1_000_000
            print(f"  {name}: {usdc_human:.2f} USDC")
            if usdc_human > 0:
                print(f"  🎉 FUNDS FOUND in {name}!")
        print()
    except Exception as e:
        print(f"✗ {rpc}: {e}\n")
