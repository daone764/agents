from web3 import Web3
import sys

# Usage: python scripts/python/check_usdc_transfers.py <address> [blocks_back]
# Queries recent USDC Transfer events to the given address on Polygon.

RPC = 'https://polygon-rpc.com/'
USDC = Web3.to_checksum_address('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')

if len(sys.argv) < 2:
    print('Provide an address to check')
    sys.exit(1)

addr = Web3.to_checksum_address(sys.argv[1])
blocks_back = int(sys.argv[2]) if len(sys.argv) > 2 else 200_000

w3 = Web3(Web3.HTTPProvider(RPC))
from_block = max(0, w3.eth.block_number - blocks_back)

topic0 = Web3.keccak(text='Transfer(address,address,uint256)').hex()
topic2 = '0x' + '0'*24 + addr[2:].lower()

try:
    logs = w3.eth.get_logs({
        'address': USDC,
        'topics': [topic0, None, topic2],
        'fromBlock': from_block,
        'toBlock': 'latest'
    })
    print(f'Found {len(logs)} USDC transfers to {addr} from block {from_block} to latest')
    if logs:
        for i, lg in enumerate(logs[:10], 1):
            print(f'{i}. tx: {lg["transactionHash"].hex()} block: {lg["blockNumber"]}')
        if len(logs) > 10:
            print('... (showing first 10)')
except Exception as e:
    print('Log query error:', e)