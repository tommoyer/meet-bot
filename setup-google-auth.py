#!/usr/bin/env python3

"""
Google API Authentication Setup Script
Run this script to set up Google API authentication for the Meet Bot.
"""

import json
import os
import sys
from pathlib import Path

def main():
    print("Google Meet Bot - Authentication Setup")
    print("=" * 40)
    
    config_dir = Path("/etc/meet-bot")
    if not config_dir.exists():
        print("Error: /etc/meet-bot directory does not exist. Run install.sh first.")
        sys.exit(1)
    
    print("\nChoose authentication method:")
    print("1. Service Account (Recommended for production)")
    print("2. OAuth2 (For development/testing)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        setup_service_account()
    elif choice == "2":
        setup_oauth2()
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

def setup_service_account():
    print("\nSetting up Service Account Authentication")
    print("-" * 40)
    
    print("\nSteps to create a service account:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Select or create a project")
    print("3. Enable the Google Meet API and Google Calendar API")
    print("4. Go to IAM & Admin > Service Accounts")
    print("5. Create a new service account")
    print("6. Download the JSON key file")
    
    json_path = input("\nEnter path to your service account JSON file: ").strip()
    
    if not os.path.exists(json_path):
        print(f"Error: File {json_path} does not exist.")
        return
    
    # Validate JSON
    try:
        with open(json_path, 'r') as f:
            service_account_data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in service_account_data:
                print(f"Error: Invalid service account file. Missing field: {field}")
                return
        
        if service_account_data['type'] != 'service_account':
            print("Error: JSON file is not a service account file.")
            return
            
    except json.JSONDecodeError:
        print("Error: Invalid JSON file.")
        return
    
    # Copy to destination
    dest_path = "/etc/meet-bot/service-account.json"
    os.system(f"cp '{json_path}' '{dest_path}'")
    os.system(f"chown root:meet-bot '{dest_path}'")
    os.system(f"chmod 640 '{dest_path}'")
    
    print(f"\nService account file installed to: {dest_path}")
    
    # Show calendar sharing instructions
    client_email = service_account_data['client_email']
    print(f"\nIMPORTANT: Share your Google Calendar with the service account:")
    print(f"Service Account Email: {client_email}")
    print("\nTo share your calendar:")
    print("1. Open Google Calendar")
    print("2. Click on 'Settings and sharing' for your calendar")
    print("3. Under 'Share with specific people', add the service account email")
    print("4. Give it 'Make changes to events' permission")

def setup_oauth2():
    print("\nSetting up OAuth2 Authentication")
    print("-" * 30)
    
    print("\nSteps to create OAuth2 credentials:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Select or create a project")
    print("3. Enable the Google Meet API and Google Calendar API")
    print("4. Go to APIs & Services > Credentials")
    print("5. Create OAuth 2.0 Client IDs")
    print("6. Download the JSON file")
    
    json_path = input("\nEnter path to your OAuth2 credentials JSON file: ").strip()
    
    if not os.path.exists(json_path):
        print(f"Error: File {json_path} does not exist.")
        return
    
    # Copy to destination
    dest_path = "/etc/meet-bot/oauth-credentials.json"
    os.system(f"cp '{json_path}' '{dest_path}'")
    os.system(f"chown root:meet-bot '{dest_path}'")
    os.system(f"chmod 640 '{dest_path}'")
    
    print(f"\nOAuth2 credentials installed to: {dest_path}")
    print("\nNote: You'll need to run the OAuth flow to get initial tokens.")
    print("This is more complex for server deployments. Service Account is recommended.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root (use sudo)")
        sys.exit(1)
    main()