import requests
import time
import json
import sys

def discover_bridge():
    print("Discovering Hue Bridge...")
    try:
        response = requests.get('https://discovery.meethue.com/')
        data = response.json()
        if len(data) > 0:
            ip = data[0]['internalipaddress']
            print(f"Found Bridge at {ip}")
            return ip
    except Exception as e:
        print(f"Error discovering bridge: {e}")
    
    print("Could not discover bridge automatically.")
    print("Please check your router for the IP of 'Philips-hue' or similar.")
    return input("Enter Bridge IP manually: ")

def register_user(bridge_ip):
    print("\n--- REGISTRATION ---")
    print("Please go to your Philips Hue Bridge and PRESS THE BIG CENTER BUTTON.")
    print("You have 30 seconds...")
    
    for i in range(30):
        sys.stdout.write(f"\rWaiting... {30-i}s")
        sys.stdout.flush()
        
        try:
            # Try to register
            payload = {"devicetype": "my_home_automation_app#mac_user"}
            response = requests.post(f"http://{bridge_ip}/api", json=payload)
            data = response.json()
            
            # Check for success
            if isinstance(data, list) and 'success' in data[0]:
                username = data[0]['success']['username']
                print(f"\n\nSUCCESS! User registered.")
                print(f"USERNAME (API KEY): {username}")
                return username
            
            # Check for link button error (expected until button is pressed)
            if isinstance(data, list) and 'error' in data[0]:
                if data[0]['error']['type'] != 101: # 101 is 'link button not pressed'
                    print(f"\nUnknown error: {data}")
        except Exception as e:
            print(f"\nError connecting to bridge: {e}")
            
        time.sleep(1)
        
    print("\nTimed out. Please run the script again and press the button.")
    return None

def save_secrets(ip, username):
    try:
        with open('secrets.json', 'r') as f:
            secrets = json.load(f)
    except FileNotFoundError:
        secrets = {}
        
    secrets['hue_bridge_ip'] = ip
    secrets['hue_username'] = username
    
    with open('secrets.json', 'w') as f:
        json.dump(secrets, f, indent=4)
    print("\nSaved credentials to secrets.json")

if __name__ == "__main__":
    ip = discover_bridge()
    if ip:
        username = register_user(ip)
        if username:
            save_secrets(ip, username)
