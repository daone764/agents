#!/usr/bin/env python3
"""
Convert PEM private key to hex format for web3.py
"""

from eth_account import Account
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import binascii

def pem_to_hex_private_key(pem_key):
    """Convert PEM EC private key to hex format"""

    # Remove the PEM header/footer and decode
    pem_data = pem_key.strip()
    pem_data = pem_data.replace("-----BEGIN EC PRIVATE KEY-----", "").replace("-----END EC PRIVATE KEY-----", "")
    pem_data = pem_data.replace("\n", "").strip()

    # Decode from base64
    der_data = binascii.a2b_base64(pem_data)

    # Load the private key
    private_key = serialization.load_der_private_key(
        der_data,
        password=None,
        backend=default_backend()
    )

    # Get the private key value
    private_value = private_key.private_numbers().private_value

    # Convert to hex and remove '0x' prefix
    hex_key = hex(private_value)[2:]

    # Ensure it's 64 characters (32 bytes) with leading zeros if needed
    hex_key = hex_key.zfill(64)

    return hex_key

# Your PEM private key from Coinbase
pem_key = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKEVnjxUopzWi9lvyRuUhpH4aQVHGf7x4Ura56zsd49uoAoGCCqGSM49
AwEHoUQDQgAEtQkyanqaPzalblQqReF32s3uu+Uh4l7g5QfsAwRv8gSNxR2fV90F
Wzj0MnMq2O4bbye0ZxEMjsF2DCbyqaFrzQ==
-----END EC PRIVATE KEY-----"""

try:
    hex_key = pem_to_hex_private_key(pem_key)
    print(f"🔑 Hex Private Key: {hex_key}")

    # Verify the key works by creating an account
    account = Account.from_key(hex_key)
    print(f"📍 Wallet Address: {account.address}")
    print("✅ Private key conversion successful!")

except Exception as e:
    print(f"❌ Error converting private key: {e}")
    print("Please make sure the PEM key is correct and complete.")