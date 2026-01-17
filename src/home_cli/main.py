import argparse
import sys
import json
# from home.switchbot import SwitchBotCode
# from home.hue import HueCode
# Relative imports for package execution
from .switchbot import SwitchBotCode
from .hue import HueCode
from .state_manager import update_device_state, load_snapshot, save_snapshot, update_last_active, get_time_since_last_active

# Global Presets Definition
# Each preset can define states for any number of devices.
# If a device is omitted or set to None, it remains unchanged.
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
                 preset = GLOBAL_PRESETS['on']
                 # We need to manually apply logic here if we recurse, 
                 # or just proceed to apply_global_preset('on') logic? 
                 # Actually, better to just let it fall through if we want 'on' to be a preset?
                 # But 'on' is special restore logic.
                 # Let's just apply the preset directly here to avoid loop.
                 apply_global_preset('on') 
                 return
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

def main():
    parser = argparse.ArgumentParser(description="Home Automation CLI")
    
    # We want to support both:
    # 1. home-cli <preset>  (e.g. "morning", "off")
    # 2. home-cli <category> <command> (e.g. "switchbot globe on")
    
    # Strategy: Use subcommands for 'hue' and 'switchbot'. 
    # If the first argument isn't one of them (and isn't -h/--list), assume it's a global preset.

    if len(sys.argv) > 1 and sys.argv[1] in ['hue', 'switchbot']:
        subparsers = parser.add_subparsers(dest="command", help="Device category", required=True)

        # --- HUE ---
        hue_parser = subparsers.add_parser("hue", help="Control Philips Hue Lights")
        hue_parser.add_argument("--preset", type=str, help="Apply a hue preset (scene) to all lights")
        hue_parser.add_argument("--list", action="store_true", help="List all lights and current state")
        hue_parser.add_argument("--on", action="store_true", help="Turn all lights on")
        hue_parser.add_argument("--off", action="store_true", help="Turn all lights off")

        # --- SWITCHBOT ---
        sb_parser = subparsers.add_parser("switchbot", help="Control SwitchBot Devices")
        sb_sub = sb_parser.add_subparsers(dest="sb_device", help="SwitchBot Device", required=True)

        # Globe
        globe_p = sb_sub.add_parser("globe", help="Control Globe Light")
        globe_p.add_argument("state", choices=["on", "off"], help="Turn on or off")

        # Curtain
        curtain_p = sb_sub.add_parser("curtain", help="Control Curtains")
        curtain_p.add_argument("state", choices=["open", "close"], help="Open or Close")
        
        # IR Light
        light_p = sb_sub.add_parser("light", help="Control IR Light")
        light_p.add_argument("state", choices=["on", "off"], help="Turn on or off")

        # AC
        ac_p = sb_sub.add_parser("ac", help="Control Air Conditioner")
        ac_p.add_argument("--temp", type=str, help="Temperature (e.g. 25, +1, -1)")
        ac_p.add_argument("--mode", type=int, choices=[1, 2, 3, 4, 5], help="Mode: 1(auto), 2(cool), 3(dry), 4(fan), 5(heat)")
        ac_p.add_argument("--fan", type=int, choices=[1, 2, 3, 4], help="Fan Speed: 1(auto), 2(low), 3(med), 4(high)")
        ac_p.add_argument("--off", action="store_true", help="Turn off AC")
        ac_p.add_argument("--on", action="store_true", help="Turn on AC (restore last state)")
        ac_p.add_argument("--status", action="store_true", help="Show current AC state")

        args = parser.parse_args()

        if args.command == "hue":
            hue = HueCode()
            if args.list:
                lights = hue.get_lights()
                print(json.dumps(lights, indent=2))
                return # Don't snapshot on list
            elif args.preset:
                print(f"Applying Hue Preset: {args.preset}")
                hue.apply_preset(args.preset)
                update_device_state("hue", "preset", args.preset)
            elif args.on:
                print("Turning Hue ON")
                hue.apply_preset("on") # Assuming 'on' preset exists or generic on
                update_device_state("hue", "preset", "on") 
            elif args.off:
                print("Turning Hue OFF")
                hue.apply_preset("off")
                update_device_state("hue", "preset", "off")
            else:
                hue_parser.print_help()
                return # Don't snapshot if help shown
            
            # Save state after Hue change
            update_last_active()
            save_snapshot()

        elif args.command == "switchbot":
            sb = SwitchBotCode()
            if args.sb_device == "globe":
                state = (args.state == "on")
                sb.set_globe(state)
                print(f"Globe set to {args.state}")
                update_device_state("switchbot", "globe", args.state)
                
            elif args.sb_device == "curtain":
                open_state = (args.state == "open")
                sb.set_curtain(open_state)
                print(f"Curtains set to {args.state}")
                update_device_state("switchbot", "curtain", args.state)
                
            elif args.sb_device == "light":
                state = (args.state == "on")
                sb.set_light(state)
                print(f"IR Light set to {args.state}")
                update_device_state("switchbot", "light", args.state)
                
            elif args.sb_device == "ac":
                from .state_manager import get_device_state
                current_ac_state = get_device_state("switchbot", "ac") or {}
                
                # Defaults
                target_temp = current_ac_state.get("temp", 25)
                target_mode = current_ac_state.get("mode", 5) # Default to 5 (Heat)
                target_fan = current_ac_state.get("fan", 1) # Default to 1 (auto)
                
                if args.status:
                    is_on = current_ac_state.get("on", False)
                    if is_on:
                         temp = current_ac_state.get("temp", "?")
                         mode = current_ac_state.get("mode", "?")
                         fan = current_ac_state.get("fan", "?")
                         print(f"AC ON: {temp}C, Mode {mode}, Fan {fan}")
                    else:
                         print("AC OFF")
                    return # Don't snapshot on status check

                if args.off:
                    # Turn OFF
                    sb.set_ac(target_temp, target_mode, target_fan, False)
                    print("AC turned OFF")
                    new_state = current_ac_state.copy()
                    new_state["on"] = False
                    update_device_state("switchbot", "ac", new_state)
                    return # Don't snapshot if just turning off? actually user wanted "last used". 
                           # If we turn it off, we might want to say it's off.
                           # But "on" logic below restores it.
                           # Let's save the state as "off". 
                
                else:
                    # Turn ON or Modify
                    
                    # Handle arguments
                    if args.mode:
                        target_mode = args.mode
                    if args.fan:
                        target_fan = args.fan
                    
                    if args.temp:
                        if args.temp.startswith('+'):
                             delta = int(args.temp[1:])
                             target_temp += delta
                        elif args.temp.startswith('-'):
                             delta = int(args.temp[1:])
                             target_temp -= delta
                        else:
                             target_temp = int(args.temp)

                    # Send Command (Implicitly turns ON)
                    sb.set_ac(target_temp, target_mode, target_fan, True)
                    print(f"AC ON: {target_temp}C, Mode {target_mode}, Fan {target_fan}")
                    
                    new_state = {
                        "on": True,
                        "temp": target_temp,
                        "mode": target_mode,
                        "fan": target_fan
                    }
                    update_device_state("switchbot", "ac", new_state)

            else:
                sb_parser.print_help()
                return
            
            # Save state after SwitchBot change
            update_last_active()
            save_snapshot()

    else:
        # Global Preset Mode
        parser.add_argument("preset", nargs="?", help="Name of the global preset to apply")
        parser.add_argument("--list", action="store_true", help="List available presets")
        
        args = parser.parse_args()

        # Load presets if they haven't been loaded yet
        if not GLOBAL_PRESETS:
            load_presets()

        if args.list:
            print("Available Global Presets:")
            for name, data in GLOBAL_PRESETS.items():
                print(f"  - {name}: {data.get('description', '')}")
            return

        if args.preset:
            apply_global_preset(args.preset)
        else:
            parser.print_help()
            print("\nSubcommands also available:")
            print("  hue [options]")
            print("  switchbot [globe|curtain|light|ac] ...")
