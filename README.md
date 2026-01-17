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

## Contributing
This project was built with code generation and agentic AI assistance.
