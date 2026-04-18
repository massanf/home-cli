import json
import os
import time

STATE_FILE = 'data/state.json'
SNAPSHOT_FILE = 'data/snapshot.json'

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load state: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

def update_device_state(category, device, value):
    current_state = load_state()
    if category not in current_state:
        current_state[category] = {}
    current_state[category][device] = value
    save_state(current_state)

def get_device_state(category, device):
    state = load_state()
    return state.get(category, {}).get(device)

def save_snapshot(data=None):
    if data is None:
        data = load_state()
    try:
        with open(SNAPSHOT_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("State snapshot saved.")
    except Exception as e:
        print(f"Error saving snapshot: {e}")

def load_snapshot():
    try:
        if os.path.exists(SNAPSHOT_FILE):
            with open(SNAPSHOT_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load snapshot: {e}")
    return {}

def update_last_active():
    state = load_state()
    state['last_active_timestamp'] = time.time()
    save_state(state)

def get_time_since_last_active():
    state = load_state()
    last_ts = state.get('last_active_timestamp')
    if last_ts is None:
        return float('inf')
    return time.time() - last_ts
