import os
import json
import random
import string
from datetime import datetime
from web3 import Web3
from eth_account import Account

# ✅ Connect to Ethereum
INFURA_URL = "https://sepolia.infura.io/v3/dbd98afea6fb4530a5287014acde156b"
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

print("🔍 Checking Ethereum Connection...")
if web3.is_connected():
    print("✅ Connected to Ethereum network")
else:
    raise ConnectionError("❌ Failed to connect to Ethereum network")

# ✅ Contract Details
contract_address = "0x3C81142536140f536c0D737d2c87EA4b4278CF0e"
private_key = os.getenv('PRIVATE_KEY')

print("🔍 Checking Private Key...")
if not private_key:
    raise ValueError("❌ PRIVATE_KEY environment variable not set or empty")
else:
    print("✅ Private key loaded")

account = Account.from_key(private_key)

# ✅ Load compiled contract ABI
print("🔍 Loading Contract ABI...")
try:
    with open("contract_abi.json", "r") as f:
        contract_abi = json.load(f)
    print("✅ Contract ABI loaded successfully")
except Exception as e:
    print("❌ Error loading contract ABI:", str(e))
    exit(1)

contract = web3.eth.contract(address=contract_address, abi=contract_abi)
print(f"✅ Using Contract at Address: {contract_address}")

# ✅ Function to generate a unique alphanumeric ID
def generate_unique_id():
    return "UID-" + ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def register_user():
    name = input("Enter name: ")
    email = input("Enter email: ")
    phone = input("Enter phone number: ")

    unique_id = generate_unique_id()
    print(f"🆔 Generated Unique ID: {unique_id}")

    # ✅ Ensure contract function parameters match Solidity function signature
    print("🔍 Preparing transaction to add identity to blockchain...")

    try:
        tx = contract.functions.addIdentity(unique_id, name, email, phone).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': web3.to_wei('80', 'gwei')
        })
        
        print("✅ Transaction built successfully")

        # ✅ Sign and send transaction
        signed_txn = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        print(f"🔗 Transaction sent! Hash: {tx_hash.hex()}")
        print("⏳ Waiting for transaction confirmation...")

        # ✅ Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt.status == 1:
            print("✅ User registered successfully on blockchain!")
        else:
            print("❌ Transaction failed! Check transaction on Etherscan:", f"https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
            return

    except Exception as e:
        print("❌ Error in transaction:", str(e))
        return

    # ✅ Check if user is stored in contract
    print("🔍 Verifying if user data is stored in contract...")

    try:
        stored_name, stored_email, stored_phone = contract.functions.getIdentity(unique_id).call()
        print(f"✅ Stored Data - Name: {stored_name}, Email: {stored_email}, Phone: {stored_phone}")

        if not stored_name:
            print("❌ User data was NOT stored in the contract! Check transaction logs.")
            return
    except Exception as e:
        print("❌ Error retrieving user from contract:", str(e))
        return

    # ✅ Log the registration
    print("📝 Logging registration...")
    try:
        with open("user_logs.txt", "a") as log:
            log.write(f"{datetime.now()} - Registered User: {name}, Email: {email}, Phone: {phone}, Unique ID: {unique_id}\n")
        print("✅ Registration logged successfully")
    except Exception as e:
        print("❌ Error writing to log file:", str(e))

if __name__ == "__main__":
    register_user()

