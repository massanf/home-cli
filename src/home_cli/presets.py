import json
from .switchbot import SwitchBotCode
from .hue import HueCode
from .state_manager import update_device_state, load_snapshot, save_snapshot, update_last_active, get_time_since_last_active

# Global Presets Definition
GLOBAL_PRESETS = {}

def load_presets(filepath='presets.json'):
    global GLOBAL_PRESETS
    try:
        with open(filepath, 'r') as f:
            GLOBAL_PRESETS = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. using empty presets.")
        GLOBAL_PRESETS = {}
    except json.JSONDecodeError as e:
        print(f"Error reading {filepath}: {e}")
        GLOBAL_PRESETS = {}

def apply_global_preset(name: str):
    if not GLOBAL_PRESETS:
        load_presets()
        
    # Special Toggle Logic
    if name == 'off':
        # Check cooldown
        elapsed = get_time_since_last_active()
        if elapsed < 900: # 15 minutes = 900 seconds
            print(f"Skipping 'off' command: Active for {int(elapsed)}s (Minimum 900s).")
            return

        print("Turning OFF lights...")
        # Note: We do NOT save snapshot here. 
        # Snapshot represents the state "before" turning off.
        # It should have been saved by the previous commands.
        
        # Turn off SwitchBot Lights
        sb = SwitchBotCode()
        sb.set_globe(False)
        update_device_state("switchbot", "globe", "off")
        sb.set_light(False)
        update_device_state("switchbot", "light", "off")
        
        # Turn off Hue
        hue = HueCode()
        hue.apply_preset("off")
        update_device_state("hue", "preset", "off")
        return

    if name == 'on':
        print("Restoring ON state from snapshot...")
        update_last_active() # Mark as active
        
        snapshot = load_snapshot()
        if not snapshot:
            print("No snapshot found. Applying default 'on' preset.")
            # Fallback to normal 'on' preset if defined
            # If not defined, we might default to hardcoded "morning" or similar
            if 'on' in GLOBAL_PRESETS:
                 # apply_global_preset('on') recursive call avoided by direct lookup
                 # But we can just use the logic below if we didn't return.
                 # Let's just recurse once safely or handle it.
                 # Actually, if we just fall through to 'if name not in GLOBAL_PRESETS',
                 # and 'on' IS in GLOBAL_PRESETS, it works.
                 pass 
            else:
                 return # Nothing to do
        else:
            # Restore SwitchBot Lights
            sb = SwitchBotCode()
            sb_vals = snapshot.get("switchbot", {})
            
            if "globe" in sb_vals:
                state = sb_vals["globe"]
                print(f"  [Restoring] Globe -> {state}")
                sb.set_globe(state == "on")
                update_device_state("switchbot", "globe", state)
            
            if "light" in sb_vals:
                state = sb_vals["light"]
                print(f"  [Restoring] IR Light -> {state}")
                sb.set_light(state == "on")
                update_device_state("switchbot", "light", state)
                
            # Restore Hue
            hue_vals = snapshot.get("hue", {})
            if "preset" in hue_vals:
                preset_name = hue_vals["preset"]
                print(f"  [Restoring] Hue -> {preset_name}")
                hue = HueCode()
                hue.apply_preset(preset_name)
                update_device_state("hue", "preset", preset_name)
            
            # After restore, the CURRENT state matches the snapshot.
            # We don't strictly need to save_snapshot() again, but it doesn't hurt.
            return

    if name not in GLOBAL_PRESETS:
        print(f"Error: Preset '{name}' not found.")
        print("Available presets:", ", ".join(GLOBAL_PRESETS.keys()))
        return

    print(f"Applying Global Preset: {name}")
    preset = GLOBAL_PRESETS[name]
    
    # 1. Apply SwitchBot Settings
    if "switchbot" in preset and preset["switchbot"]:
        sb = SwitchBotCode()
        sb_config = preset["switchbot"]
        
        if "curtain" in sb_config and sb_config["curtain"]:
            state = sb_config["curtain"]
            print(f"  [SwitchBot] Curtain -> {state}")
            sb.set_curtain(state == "open")
            update_device_state("switchbot", "curtain", state)

        if "globe" in sb_config and sb_config["globe"]:
             state = sb_config["globe"]
             print(f"  [SwitchBot] Globe -> {state}")
             sb.set_globe(state == "on")
             update_device_state("switchbot", "globe", state)
             
        if "light" in sb_config and sb_config["light"]:
             state = sb_config["light"]
             print(f"  [SwitchBot] IR Light -> {state}")
             sb.set_light(state == "on")
             update_device_state("switchbot", "light", state)

        if "ac" in sb_config and sb_config["ac"]:
            ac = sb_config["ac"]
            if not ac.get("on", True):
                 print(f"  [SwitchBot] AC -> OFF")
                 sb.set_ac(25, 1, 1, False) # Params don't matter if off, but required by method signature
                 update_device_state("switchbot", "ac", {"on": False})
            else:
                print(f"  [SwitchBot] AC -> {ac}")
                sb.set_ac(
                    ac.get("temp", 25),
                    ac.get("mode", 1),
                    ac.get("fan", 1),
                    True
                )
                update_device_state("switchbot", "ac", ac)

    # 2. Apply Hue Settings
    if "hue" in preset and preset["hue"]:
        hue_preset_name = preset["hue"]
        print(f"  [Hue] Applying preset -> {hue_preset_name}")
        hue = HueCode()
        # For "off", we might strictly want to turn them off if no "off" preset exists in hue.py
        # But for now let's assume 'off' exists or logic is handled
        if hue_preset_name == "off":
             # Special case if we want to force off without a preset definition
             # But best to add 'off' to hue.py presets
             hue.apply_preset("off") # Requires 'off' in hue.py PRESETS
        else:
             hue.apply_preset(hue_preset_name)
        
        update_device_state("hue", "preset", hue_preset_name)

    # Save snapshot after successful application of a normal preset
    update_last_active()
    save_snapshot()
