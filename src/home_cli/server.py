from flask import Flask, jsonify, request
import logging
from .hue import HueCode
from .switchbot import SwitchBotCode
from .state_manager import load_state, get_device_state, update_device_state
from .presets import apply_global_preset, load_presets, GLOBAL_PRESETS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Ensure presets are loaded
load_presets()

@app.route('/status', methods=['GET'])
def get_status():
    """Returns the current state of all devices (from state.json)."""
    try:
        state = load_state()
        return jsonify(state)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/preset/<name>', methods=['GET', 'POST'])
def run_preset(name):
    """Applies a global preset."""
    try:
        apply_global_preset(name)
        return jsonify({"status": "success", "preset": name})
    except Exception as e:
        app.logger.error(f"Error applying preset {name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/hue/on', methods=['GET'])
def hue_on():
    """Turns Hue lights ON (using 'on' preset)."""
    try:
        hue = HueCode()
        hue.apply_preset('on')
        update_device_state("hue", "preset", "on")
        return jsonify({"status": "success", "action": "hue_on"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hue/off', methods=['GET'])
def hue_off():
    """Turns Hue lights OFF."""
    try:
        hue = HueCode()
        hue.apply_preset('off')
        update_device_state("hue", "preset", "off")
        return jsonify({"status": "success", "action": "hue_off"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint for Homebridge HTTP-SWITCH for SwitchBot Globe
@app.route('/switchbot/globe/<state>', methods=['GET'])
def switchbot_globe(state):
    """Control Globe (on/off). State must be 'on' or 'off'."""
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        sb = SwitchBotCode()
        sb.set_globe(state == 'on')
        update_device_state("switchbot", "globe", state)
        return jsonify({"status": "success", "device": "globe", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint for SwitchBot Curtain
@app.route('/switchbot/curtain/<state>', methods=['GET'])
def switchbot_curtain(state):
    """Control Curtain (open/close)."""
    # map open/close to API expected open/close (or on/off if that's what underlying uses)
    # switchbot.py uses set_curtain(open: bool) -> 'turnOn'/'turnOff'
    if state not in ['open', 'close']:
        return jsonify({"error": "Invalid state, use open/close"}), 400
    try:
        sb = SwitchBotCode()
        sb.set_curtain(state == 'open')
        update_device_state("switchbot", "curtain", state)
        return jsonify({"status": "success", "device": "curtain", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint for SwitchBot IR Light
@app.route('/switchbot/light/<state>', methods=['GET'])
def switchbot_light(state):
    """Control IR Light (on/off)."""
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        sb = SwitchBotCode()
        sb.set_light(state == 'on')
        update_device_state("switchbot", "light", state)
        return jsonify({"status": "success", "device": "light", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Thermostat Endpoints (homebridge-web-thermostat) ---

@app.route('/switchbot/ac/status', methods=['GET'])
def get_ac_status():
    """Returns AC state expected by homebridge-web-thermostat."""
    try:
        current_ac_state = get_device_state("switchbot", "ac") or {}
        
        # SwitchBot Modes: 1(auto), 2(cool), 3(dry), 4(fan), 5(heat)
        # HomeKit Modes: 0=Off, 1=Heat, 2=Cool, 3=Auto
        
        sb_mode = current_ac_state.get("mode", 1)
        is_on = current_ac_state.get("on", False)
        target_temp = float(current_ac_state.get("temp", 25))
        
        hk_state = 0 # Off
        if is_on:
            if sb_mode == 2: hk_state = 2 # Cool
            elif sb_mode == 5: hk_state = 1 # Heat
            elif sb_mode == 1: hk_state = 3 # Auto
            else: hk_state = 3 # Default to Auto for others
            
        return jsonify({
            "targetHeatingCoolingState": hk_state,
            "currentHeatingCoolingState": hk_state, # We assume current matches target instantly
            "targetTemperature": target_temp,
            "currentTemperature": target_temp # Mirror target as current (no sensor)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/ac/targetTemperature', methods=['GET'])
def set_ac_temp():
    """Sets target temperature from query param ?value=FLOAT."""
    try:
        temp_val = request.args.get('value')
        if not temp_val:
            return jsonify({"error": "Missing value param"}), 400
            
        target_temp = int(float(temp_val))
        
        sb = SwitchBotCode()
        current_ac_state = get_device_state("switchbot", "ac") or {}
        
        target_mode = current_ac_state.get("mode", 1) 
        target_fan = current_ac_state.get("fan", 1)
        is_on = current_ac_state.get("on", False)
        
        # If AC is ON, update it. If OFF, just save state?
        if is_on:
            sb.set_ac(target_temp, target_mode, target_fan, True)
        
        new_state = current_ac_state.copy()
        new_state["temp"] = target_temp
        update_device_state("switchbot", "ac", new_state)
        
        return jsonify({"status": "success", "targetTemperature": target_temp})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/ac/targetHeatingCoolingState', methods=['GET'])
def set_ac_mode():
    """Sets mode from query param ?value=INT (0-3)."""
    try:
        mode_val = request.args.get('value')
        if mode_val is None:
            return jsonify({"error": "Missing value param"}), 400
            
        mode = int(float(mode_val)) # 0=Off, 1=Heat, 2=Cool, 3=Auto
        
        sb = SwitchBotCode()
        current_ac_state = get_device_state("switchbot", "ac") or {}
        
        target_temp = current_ac_state.get("temp", 25)
        target_fan = current_ac_state.get("fan", 1)
        
        if mode == 0:
            # Turn OFF
            sb.set_ac(target_temp, 1, 1, False)
            new_state = current_ac_state.copy()
            new_state["on"] = False
            update_device_state("switchbot", "ac", new_state)
            return jsonify({"status": "success", "targetHeatingCoolingState": 0})
            
        # Map HomeKit -> SwitchBot
        sb_mode = 1
        if mode == 1: sb_mode = 5 # Heat
        elif mode == 2: sb_mode = 2 # Cool
        elif mode == 3: sb_mode = 1 # Auto
        
        # Turn ON / Change Mode
        sb.set_ac(target_temp, sb_mode, target_fan, True)
        
        new_state = current_ac_state.copy()
        new_state["on"] = True
        new_state["mode"] = sb_mode
        update_device_state("switchbot", "ac", new_state)
        
        return jsonify({"status": "success", "targetHeatingCoolingState": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_server(port=5001):
    app.run(host='0.0.0.0', port=port)
