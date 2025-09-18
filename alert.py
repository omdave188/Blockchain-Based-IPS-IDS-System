import os
import time
import socket
import json
import smtplib
import psutil
import platform
import requests
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from collections import defaultdict

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ADMIN_EMAIL = "om.d1@ahduni.edu.in"  # Replace with the admin's email
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # Your email
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Your email app password

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise ValueError("❌ EMAIL_ADDRESS or EMAIL_PASSWORD environment variable not set")

# Function to send alert email
def send_alert_email(unique_id, timestamp):
    system_info = get_system_info()

    subject = "🚨 Security Alert: Multiple Failed Login Attempts!"
    body = f"""
    *Alert! 🚨*  
    The system has detected *3 consecutive failed login attempts* for the following Unique ID:  
    - **Unique ID:** {unique_id}  
    - **Timestamp:** {timestamp}  

    📌 **System Information:**  
    {system_info}

    Please investigate immediately.  
    """

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ADMIN_EMAIL

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
        print(f"✅ Alert email sent to admin for Unique ID: {unique_id}")
    except Exception as e:
        print("❌ Failed to send alert email:", str(e))

#  Function to get system details
def get_system_info():
    try:
        # ✅ Hostname and Local IP Address
        hostname = socket.gethostname()
        local_ip = "Unknown"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except:
                pass

        # ✅ Public IP Address (using multiple sources for redundancy)
        public_ip = "Unknown"
        try:
            public_ip = requests.get("https://api64.ipify.org?format=text", timeout=5).text.strip()
        except:
            try:
                public_ip = requests.get("https://ifconfig.me/ip", timeout=5).text.strip()
            except:
                public_ip = "❌ Could not fetch Public IP"

        # ✅ MAC Address (using psutil for better accuracy)
        mac_address = "Unknown"
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac_address = addr.address
                    break
        
        # ✅ OS and User Info
        os_info = f"{platform.system()} {platform.release()}"
        user = os.getlogin()

        # ✅ Get location info
        location_info = "N/A"
        isp = "N/A"
        try:
            geo_data = requests.get(f"https://ipinfo.io/{public_ip}/json", timeout=5).json()
            location_info = f"{geo_data.get('city', 'Unknown')}, {geo_data.get('region', 'Unknown')}, {geo_data.get('country', 'Unknown')}"
            isp = geo_data.get("org", "Unknown ISP")
        except:
            location_info = "❌ Could not fetch location"
            isp = "❌ Could not fetch ISP"

        # ✅ Get system uptime (Fix timedelta error)
        uptime_seconds = time.time() - psutil.boot_time()
        uptime = str(timedelta(seconds=int(uptime_seconds)))

        return f"""
        🖥 **System Details**  
        - **Hostname:** {hostname}  
        - **Local IP Address:** {local_ip}  
        - **Public IP Address:** {public_ip}  
        - **MAC Address:** {mac_address}  
        - **Operating System:** {os_info}  
        - **Logged-in User:** {user}  
        - **Location:** {location_info}  
        - **ISP:** {isp}  
        - **System Uptime:** {uptime}  
        """
    except Exception as e:
        return f"⚠️ Error fetching system details: {e}"


#  Monitor log file for failed attempts
def monitor_log_file(log_file):
    print("🔍 Monitoring log file for failed login attempts...")

    failed_attempts_cache = defaultdict(list)  # Store last 3 attempts for each Unique ID
    alerted_attempts = set()  # Track attempts already alerted
    file_position = 0  # Start reading from the end of the file

    while True:
        try:
            with open(log_file, "r") as log:
                log.seek(file_position)  # Continue reading from last position
                new_lines = log.readlines()
                file_position = log.tell()  # Update the file position

            # ✅ Process only new lines added to the log file
            for line in new_lines:
                if "Status: Failed" in line:
                    parts = line.split(", ")
                    unique_id = parts[1].split(": ")[1]  # Extract Unique ID
                    timestamp = parts[0].split(" - ")[0]  # Extract Timestamp

                    failed_attempts_cache[unique_id].append(line)
                    if len(failed_attempts_cache[unique_id]) > 3:
                        failed_attempts_cache[unique_id].pop(0)  # Keep only last 3 attempts

                    # ✅ Check if last 3 attempts are all failed and not alerted yet
                    if (
                        len(failed_attempts_cache[unique_id]) == 3 and
                        all("Status: Failed" in entry for entry in failed_attempts_cache[unique_id]) and
                        unique_id not in alerted_attempts
                    ):
                        send_alert_email(unique_id, timestamp)
                        alerted_attempts.add(unique_id)  # Mark as alerted
                        failed_attempts_cache[unique_id].clear()  # Clear to wait for next set of 3

            time.sleep(5)  # Check log file every 5 seconds
        except Exception as e:
            print("❌ Error reading log file:", str(e))
            time.sleep(10)  # Wait 10 seconds before retrying in case of error

if __name__ == "__main__":
    LOG_FILE = "user_logs.txt"  # Ensure this file is correctly named
    monitor_log_file(LOG_FILE)

