import argparse
import sys
import json
# from home.switchbot import SwitchBotCode
# from home.hue import HueCode
# Relative imports for package execution
from .switchbot import SwitchBotCode
from .hue import HueCode
from .state_manager import update_device_state, load_snapshot, save_snapshot, update_last_active, get_time_since_last_active
from .server import run_server
from .presets import apply_global_preset, load_presets, GLOBAL_PRESETS

def main():
    parser = argparse.ArgumentParser(description="Home Automation CLI")
    
    # We want to support both:
    # 1. home-cli <preset>  (e.g. "morning", "off")
    # 2. home-cli <category> <command> (e.g. "switchbot globe on")
    
    # Strategy: Use subcommands for 'hue' and 'switchbot'. 
    # If the first argument isn't one of them (and isn't -h/--list), assume it's a global preset.

    if len(sys.argv) > 1 and sys.argv[1] in ['hue', 'switchbot', 'server']:
        subparsers = parser.add_subparsers(dest="command", help="Device category", required=True)

        # --- HUE ---
        hue_parser = subparsers.add_parser("hue", help="Control Philips Hue Lights")
        hue_parser.add_argument("--preset", type=str, help="Apply a hue preset (scene) to all lights")
        hue_parser.add_argument("--list", action="store_true", help="List all lights and current state")
        hue_parser.add_argument("--on", action="store_true", help="Turn all lights on")
        hue_parser.add_argument("--off", action="store_true", help="Turn all lights off")

        # --- SERVER ---
        server_parser = subparsers.add_parser("server", help="Start the Homebridge API Server")
        server_parser.add_argument("--port", type=int, default=5001, help="Port to run server on")

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
            update_last_active()
            save_snapshot()

        elif args.command == "server":
            print(f"Starting server on port {args.port}...")
            run_server(args.port)

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
