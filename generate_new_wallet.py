from eth_account import Account

# Generate a new secure wallet
new_account = Account.create()

print("🔐 NEW SECURE WALLET:")
print(f"Address: {new_account.address}")
print(f"Private Key: {new_account.key.hex()}")
print()
print("⚠️ SAVE THIS PRIVATE KEY SECURELY!")
print("⚠️ NEVER SHARE IT WITH ANYONE!")
print("⚠️ This is your new wallet - update your .env file")
