from flask import Flask, jsonify, request
import logging
from .hue import HueCode
from .switchbot import SwitchBotCode
from .state import load_state, get_device_state, update_device_state
from .presets import apply_global_preset, load_presets

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

load_presets()

@app.route('/status', methods=['GET'])
def get_status():
    try:
        return jsonify(load_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/preset/<name>', methods=['GET', 'POST'])
def run_preset(name):
    try:
        apply_global_preset(name)
        return jsonify({"status": "success", "preset": name})
    except Exception as e:
        app.logger.error(f"Error applying preset {name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/smart/on', methods=['GET'])
def smart_on():
    try:
        apply_global_preset('on')
        return jsonify({"status": "success", "action": "smart_on"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/smart/off', methods=['GET'])
def smart_off():
    try:
        apply_global_preset('off')
        return jsonify({"status": "success", "action": "smart_off"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hue/on', methods=['GET'])
def hue_on():
    try:
        HueCode().apply_preset('on')
        update_device_state("hue", "preset", "on")
        return jsonify({"status": "success", "action": "hue_on"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hue/off', methods=['GET'])
def hue_off():
    try:
        HueCode().apply_preset('off')
        update_device_state("hue", "preset", "off")
        return jsonify({"status": "success", "action": "hue_off"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/globe/<state>', methods=['GET'])
def switchbot_globe(state):
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        SwitchBotCode().set_globe(state == 'on')
        update_device_state("switchbot", "globe", state)
        return jsonify({"status": "success", "device": "globe", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/curtain/<state>', methods=['GET'])
def switchbot_curtain(state):
    if state not in ['open', 'close']:
        return jsonify({"error": "Invalid state, use open/close"}), 400
    try:
        SwitchBotCode().set_curtain(state == 'open')
        update_device_state("switchbot", "curtain", state)
        return jsonify({"status": "success", "device": "curtain", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/light/<state>', methods=['GET'])
def switchbot_light(state):
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        SwitchBotCode().set_light(state == 'on')
        update_device_state("switchbot", "light", state)
        return jsonify({"status": "success", "device": "light", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/ac/status', methods=['GET'])
def get_ac_status():
    try:
        current_ac_state = get_device_state("switchbot", "ac") or {}
        sb_mode = current_ac_state.get("mode", 1)
        is_on = current_ac_state.get("on", False)
        target_temp = float(current_ac_state.get("temp", 25))
        hk_state = 0
        if is_on:
            if sb_mode == 2: hk_state = 2
            elif sb_mode == 5: hk_state = 1
            else: hk_state = 3
        return jsonify({
            "targetHeatingCoolingState": hk_state,
            "currentHeatingCoolingState": hk_state,
            "targetTemperature": target_temp,
            "currentTemperature": target_temp
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/ac/targetTemperature', methods=['GET'])
def set_ac_temp():
    try:
        temp_val = request.args.get('value')
        if not temp_val:
            return jsonify({"error": "Missing value param"}), 400
        target_temp = int(float(temp_val))
        current_ac_state = get_device_state("switchbot", "ac") or {}
        if current_ac_state.get("on", False):
            SwitchBotCode().set_ac(
                target_temp,
                current_ac_state.get("mode", 1),
                current_ac_state.get("fan", 1),
                True
            )
        new_state = {**current_ac_state, "temp": target_temp}
        update_device_state("switchbot", "ac", new_state)
        return jsonify({"status": "success", "targetTemperature": target_temp})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/ac/targetHeatingCoolingState', methods=['GET'])
def set_ac_mode():
    try:
        mode_val = request.args.get('value')
        if mode_val is None:
            return jsonify({"error": "Missing value param"}), 400
        mode = int(float(mode_val))
        current_ac_state = get_device_state("switchbot", "ac") or {}
        target_temp = current_ac_state.get("temp", 25)
        target_fan = current_ac_state.get("fan", 1)
        if mode == 0:
            SwitchBotCode().set_ac(target_temp, 1, 1, False)
            update_device_state("switchbot", "ac", {**current_ac_state, "on": False})
            return jsonify({"status": "success", "targetHeatingCoolingState": 0})
        sb_mode = {1: 5, 2: 2, 3: 1}.get(mode, 1)
        SwitchBotCode().set_ac(target_temp, sb_mode, target_fan, True)
        update_device_state("switchbot", "ac", {**current_ac_state, "on": True, "mode": sb_mode})
        return jsonify({"status": "success", "targetHeatingCoolingState": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run(port=5001):
    app.run(host='0.0.0.0', port=port)
