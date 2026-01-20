# Home CLI 🏠

A unified home automation CLI for **SwitchBot** and **Philips Hue** devices.  
Vibe-coded with **Antigravity**. 🚀

## Features ✨

*   **Global Presets**: Define scenes (e.g., "morning", "theatre_mode") in `presets.json` and apply them across both Hue and SwitchBot ecosystems simultaneously.
*   **Smart Toggle (On/Off)**:
    *   **Continuous Snapshotting**: State is saved automatically on every command.
    *   **Debounce Protection**: Prevents motion sensors from turning lights off if they were just turned on (<15 mins).
    *   **State Restoration**: `home-cli on` restores the *exact* state of lights/appliances before they were turned off.
*   **Advanced AC Control**:
    *   Restore last used settings.
    *   Relative temperature control (`--temp +1`, `--temp -1`).
    *   Status checks (`--status`) without modifying state.
*   **State Persistence**: All device states are tracked in `state.json` ensuring the CLI knows the "truth" even across restarts.

## Installation 🛠️

### Prerequisites
*   Python >= 3.12
*   [Poetry](https://python-poetry.org/)

### Setup

1.  **Install Dependencies**:
    ```bash
    poetry install
    ```

2.  **Configure Secrets**:
    Create a `secrets.json` file in the root directory:
    ```json
    {
        "hue": {
            "bridge_ip": "YOUR_BRIDGE_IP",
            "username": "YOUR_HUE_USERNAME"
        },
        "switchbot": {
            "token": "YOUR_SWITCHBOT_TOKEN",
            "secret": "YOUR_SWITCHBOT_SECRET"
        }
    }
    ```
    *Tip: You can use the provided `hue_setup.py` helper to discover your bridge and generate a username.*

3.  **Configure Presets**:
    Edit `presets.json` to define your custom scenes (e.g., `morning`, `work`, `movie`).

## Usage 🚀

### Global Commands
```bash
# Apply a preset
poetry run home-cli morning
poetry run home-cli theatre-mode

# Turn everything off (smart toggle)
poetry run home-cli off

# Restore everything to previous state
poetry run home-cli on
```

### Individual Control

**Philips Hue:**
```bash
poetry run home-cli hue --on
poetry run home-cli hue --preset dim
```

**SwitchBot AC:**
```bash
# Turn ON (restores last settings)
poetry run home-cli switchbot ac --on

# Check Status
poetry run home-cli switchbot ac --status

# Adjust Temperature
poetry run home-cli switchbot ac --temp 24
poetry run home-cli switchbot ac --temp +1

# Set Mode (1:Auto, 2:Cool, 3:Dry, 4:Fan, 5:Heat)
poetry run home-cli switchbot ac --mode 2
```

**Other Devices:**
```bash
poetry run home-cli switchbot globe on
poetry run home-cli switchbot curtain close
```

## HomeKit Integration 🏠

This project includes a built-in **Flask API Server** and a local **Homebridge** instance to expose all devices to Apple HomeKit.

### Features
*   **Siri / Home App Control**: Control Hue, SwitchBot, and Scenes from your iPhone or Mac.
*   **AC Thermostat**: Full thermostat UI for your AC (Heat/Cool/Auto/Temp).
*   **Preset Buttons**: Trigger your `presets.json` scenes (e.g., "Bar Mode") directly from HomeKit buttons.
*   **Real-time State**: Two-way sync ensures HomeKit always shows the correct status.

### Setup

1.  **Start the API Server** (Terminal 1):
    ```bash
    poetry run home-cli server
    # Runs on http://localhost:5001
    ```

2.  **Start Homebridge** (Terminal 2):
    ```bash
    ./start_homebridge.sh
    # Installs dependencies and runs Homebridge on port 51827
    ```

3.  **Pair with iPhone**:
    *   Open **Home** App.
    *   Tap **+** > **Add Accessory**.
    *   Scan the QR code shown in Terminal 2.

### Troubleshooting
*   **Port 5001**: The API server uses port 5001 to avoid conflicts with AirPlay (port 5000).
*   **Responsiveness**: Accessories are polled every 2s for fast updates.

## Contributing
This project was built with code generation and agentic AI assistance.
