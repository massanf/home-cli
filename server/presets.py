import json

from .hue import HueCode
from .state import save_snapshot, update_device_state, update_snapshot_device
from .switchbot import SwitchBotCode

GLOBAL_PRESETS = {}


def load_presets(filepath="config/presets.json"):
    global GLOBAL_PRESETS
    try:
        with open(filepath, "r") as f:
            GLOBAL_PRESETS = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Using empty presets.")
        GLOBAL_PRESETS = {}
    except json.JSONDecodeError as e:
        print(f"Error reading {filepath}: {e}")
        GLOBAL_PRESETS = {}


def apply_preset(name: str, dry_run: bool = False):
    if not GLOBAL_PRESETS:
        load_presets()

    if name not in GLOBAL_PRESETS:
        available = ", ".join(GLOBAL_PRESETS.keys())
        print(f"Error: Preset '{name}' not found. Available: {available}")
        return

    print(f"Applying preset: {name}{' (snapshot only, not home)' if dry_run else ''}")
    preset = GLOBAL_PRESETS[name]

    def _write(category, device, value):
        if dry_run:
            update_snapshot_device(category, device, value)
        else:
            update_device_state(category, device, value)

    if preset.get("switchbot"):
        sb_config = preset["switchbot"]
        if not dry_run:
            sb = SwitchBotCode()
        if sb_config.get("curtain"):
            state = sb_config["curtain"]
            if not dry_run:
                sb.set_curtain(state == "open")
            _write("switchbot", "curtain", state)
        if sb_config.get("globe"):
            state = sb_config["globe"]
            if not dry_run:
                sb.set_globe(state == "on")
            _write("switchbot", "globe", state)
        if sb_config.get("edison"):
            state = sb_config["edison"]
            if not dry_run:
                sb.set_edison(state == "on")
            _write("switchbot", "edison", state)
        if sb_config.get("ac"):
            ac = sb_config["ac"]
            if not dry_run:
                if not ac.get("on", True):
                    SwitchBotCode().set_ac(25, 1, 1, False)
                else:
                    sb.set_ac(
                        ac.get("temp", 25), ac.get("mode", 1), ac.get("fan", 1), True
                    )
            _write("switchbot", "ac", {"on": False} if not ac.get("on", True) else ac)

    if preset.get("hue"):
        hue_preset_name = preset["hue"]
        if not dry_run:
            HueCode().apply_preset(hue_preset_name)
        _write("hue", "preset", hue_preset_name)

    if not dry_run:
        save_snapshot()
