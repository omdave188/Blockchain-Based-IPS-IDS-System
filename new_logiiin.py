import os
import json
import smtplib
from datetime import datetime
from web3 import Web3
from email.mime.text import MIMEText
from eth_account import Account

# ✅ Connect to Ethereum
INFURA_URL = "https://sepolia.infura.io/v3/dbd98afea6fb4530a5287014acde156b"
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

if not web3.is_connected():
    raise ConnectionError("❌ Failed to connect to Ethereum network")

# ✅ Contract Details
contract_address = "0x3C81142536140f536c0D737d2c87EA4b4278CF0e"
private_key = os.getenv('PRIVATE_KEY')
if not private_key:
    raise ValueError("❌ PRIVATE_KEY environment variable not set")

account = Account.from_key(private_key)

# ✅ Load compiled contract ABI
try:
    with open("contract_abi.json", "r") as f:
        contract_abi = json.load(f)
except Exception as e:
    raise ValueError("❌ Error loading contract ABI: " + str(e))

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# ✅ Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise ValueError("❌ EMAIL_ADDRESS or EMAIL_PASSWORD environment variable not set")

# ✅ Function to send OTP via email
def send_email(receiver_email, otp):
    try:
        msg = MIMEText(f"Hello,\n\nYour OTP for login is: {otp}\n\nPlease use this code to complete your login.\n\nBest Regards,\nYour App Team")
        msg["Subject"] = "🔐 Your OTP for Login"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = receiver_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, receiver_email, msg.as_string())
    except Exception as e:
        print("❌ Failed to send email:", str(e))

# ✅ Login function
def login_user():
    unique_id = input("Enter your Unique ID: ")
    
    try:
        name, email, phone = contract.functions.getIdentity(unique_id).call()
        if not name:
            print("❌ User not found!")
            log_attempt(unique_id, "N/A", "Failed (User not found)")
            return
    except Exception as e:
        log_attempt(unique_id, "", f"Failed (Error retrieving user: {str(e)})")
        return

    # ✅ Generate OTP on blockchain
    try:
        tx = contract.functions.generateOTP(unique_id).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': web3.to_wei('90', 'gwei')
        })

        signed_txn = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        log_attempt(unique_id, name, f"Failed (Error generating OTP: {str(e)})")
        return

    # ✅ Retrieve OTP from blockchain
    try:
        otp = contract.functions.getOTP(unique_id).call()
        if not otp:
            log_attempt(unique_id, name, "Failed (OTP retrieval failed)")
            return
    except Exception as e:
        log_attempt(unique_id, name, f"Failed (Error retrieving OTP: {str(e)})")
        return

    # ✅ Send OTP via email (OTP is not displayed in console)
    send_email(email, otp)
    
    # ✅ Ask user for OTP input
    entered_otp = input("Enter the OTP sent to your email: ").strip()

    # ✅ Validate OTP
    try:
        is_valid = contract.functions.validateOTP(unique_id, int(entered_otp)).call()
        if is_valid:
            print("✅ Login Successful! 🎉")
            log_status = "Successful"
        else:
            print("❌ Invalid OTP! Login Failed.")
            log_status = "Failed (Invalid OTP)"
    except Exception as e:
        log_status = f"Failed (Error validating OTP: {str(e)})"

    # ✅ Log the login attempt
    log_attempt(unique_id, name, log_status)

# ✅ Function to log login attempts in the same log file as registration
def log_attempt(unique_id, name, status):
    try:
        with open("user_logs.txt", "a") as log:
            log.write(f"{datetime.now()} - Login Attempt: User: {name if name else 'N/A'}, Unique ID: {unique_id}, Status: {status}\n")
    except Exception as e:
        print("❌ Error writing to log file:", str(e))

if __name__ == "__main__":
    login_user()

