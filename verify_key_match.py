#!/usr/bin/env python3
"""Verify which address the current private key controls"""
from eth_account import Account
import os
from dotenv import load_dotenv

load_dotenv()

pk = os.getenv('POLYGON_WALLET_PRIVATE_KEY')
acc = Account.from_key(pk)

print(f"Private key controls: {acc.address}")
print(f"Expected (OLD wallet): 0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6")
print(f"Match: {acc.address.lower() == '0xd6d39c2b53599Dfb6bf237E1B04e5a3191d6d6B6'.lower()}")
