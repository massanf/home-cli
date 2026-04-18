import json

from .hue import HueCode
from .state import load_snapshot, save_snapshot, update_device_state, update_last_active
from .switchbot import SwitchBotCode

GLOBAL_PRESETS = {}

def load_presets(filepath='config/presets.json'):
    global GLOBAL_PRESETS
    try:
        with open(filepath, 'r') as f:
            GLOBAL_PRESETS = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Using empty presets.")
        GLOBAL_PRESETS = {}
    except json.JSONDecodeError as e:
        print(f"Error reading {filepath}: {e}")
        GLOBAL_PRESETS = {}

def apply_global_preset(name: str):
    if not GLOBAL_PRESETS:
        load_presets()

    if name == 'off':
        save_snapshot()
        print("Turning OFF lights...")
        sb = SwitchBotCode()
        sb.set_globe(False)
        update_device_state("switchbot", "globe", "off")
        sb.set_edison(False)
        update_device_state("switchbot", "edison", "off")
        hue = HueCode()
        hue.apply_preset("off")
        update_device_state("hue", "preset", "off")
        return

    if name == 'on':
        print("Restoring ON state from snapshot...")
        update_last_active()
        snapshot = load_snapshot()
        if not snapshot:
            print("No snapshot found.")
            return
        sb = SwitchBotCode()
        sb_vals = snapshot.get("switchbot", {})
        if "globe" in sb_vals:
            state = sb_vals["globe"]
            sb.set_globe(state == "on")
            update_device_state("switchbot", "globe", state)
        if "edison" in sb_vals:
            state = sb_vals["edison"]
            sb.set_edison(state == "on")
            update_device_state("switchbot", "edison", state)
        hue_vals = snapshot.get("hue", {})
        if "preset" in hue_vals:
            preset_name = hue_vals["preset"]
            HueCode().apply_preset(preset_name)
            update_device_state("hue", "preset", preset_name)
        return

    if name not in GLOBAL_PRESETS:
        available = ', '.join(GLOBAL_PRESETS.keys())
        print(f"Error: Preset '{name}' not found. Available: {available}")
        return

    print(f"Applying preset: {name}")
    preset = GLOBAL_PRESETS[name]

    if preset.get("switchbot"):
        sb = SwitchBotCode()
        sb_config = preset["switchbot"]
        if sb_config.get("curtain"):
            state = sb_config["curtain"]
            sb.set_curtain(state == "open")
            update_device_state("switchbot", "curtain", state)
        if sb_config.get("globe"):
            state = sb_config["globe"]
            sb.set_globe(state == "on")
            update_device_state("switchbot", "globe", state)
        if sb_config.get("edison"):
            state = sb_config["edison"]
            sb.set_edison(state == "on")
            update_device_state("switchbot", "edison", state)
        if sb_config.get("ac"):
            ac = sb_config["ac"]
            if not ac.get("on", True):
                SwitchBotCode().set_ac(25, 1, 1, False)
                update_device_state("switchbot", "ac", {"on": False})
            else:
                sb.set_ac(ac.get("temp", 25), ac.get("mode", 1), ac.get("fan", 1), True)
                update_device_state("switchbot", "ac", ac)

    if preset.get("hue"):
        hue_preset_name = preset["hue"]
        HueCode().apply_preset(hue_preset_name)
        update_device_state("hue", "preset", hue_preset_name)

    update_last_active()
    save_snapshot()
