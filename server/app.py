import json
import logging

from flask import Flask, Response, jsonify, request, stream_with_context

from .hue import HueCode
from .logger import get_logs, subscribe, unsubscribe
from .presence import on_enter, on_leave
from .presets import apply_preset, load_presets
from .scheduler import get_schedules
from .scheduler import start as start_scheduler
from .state import get_device_state, load_state, update_device_state
from .switchbot import SwitchBotCode

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

load_presets()
start_scheduler()

@app.route('/', methods=['GET'])
def api_docs():
    rows = "".join(
        f"""<tr>
            <td>{', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))}</td>
            <td><code>{rule.rule}</code></td>
        </tr>"""
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
        if rule.rule != '/static/<path:filename>'
    )
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>home-server API</title>
    <style>
        body {{ font-family: monospace; padding: 1rem; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.8rem; text-align: left; }}
        th {{ background: #f0f0f0; }}
        td:first-child {{ color: steelblue; font-weight: bold; width: 5rem; }}
    </style>
</head>
<body>
    <h2>home-server API</h2>
    <table>
        <tr><th>Method</th><th>Endpoint</th></tr>
        {rows}
    </table>
</body>
</html>"""
    return html

@app.route('/switchbot/devices', methods=['GET'])
def switchbot_devices():
    try:
        return jsonify(SwitchBotCode().get_devices())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logs', methods=['GET'])
def logs():
    entries = get_logs()
    rows = ""
    for e in entries:
        status_color = "green" if e["status"] == 200 else "red"
        rows += f"""
        <tr>
            <td>{e["time"]}</td>
            <td>{e["method"]}</td>
            <td style="word-break:break-all">{e["url"]}</td>
            <td style="color:{status_color}">{e["status"]}</td>
            <td><pre>{e["payload"] or ""}</pre></td>
            <td><pre>{e["response"] or ""}</pre></td>
        </tr>"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>home-server logs</title>
    <style>
        body {{ font-family: monospace; padding: 1rem; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
        th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem;
                  vertical-align: top; }}
        th {{ background: #f0f0f0; }}
        pre {{ margin: 0; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h2>Outgoing requests (live)</h2>
    <table id="log-table">
        <tr>
            <th>Time</th><th>Method</th><th>URL</th>
            <th>Status</th><th>Payload</th><th>Response</th>
        </tr>
        {rows}
    </table>
    <script>
        const table = document.getElementById('log-table');
        const es = new EventSource('/logs/stream');
        es.onmessage = e => {{
            const d = JSON.parse(e.data);
            const color = d.status === 200 ? 'green' : 'red';
            const row = `<tr>
                <td>${{d.time}}</td>
                <td>${{d.method}}</td>
                <td style="word-break:break-all">${{d.url}}</td>
                <td style="color:${{color}}">${{d.status}}</td>
                <td><pre>${{JSON.stringify(d.payload, null, 2) || ''}}</pre></td>
                <td><pre>${{JSON.stringify(d.response, null, 2) || ''}}</pre></td>
            </tr>`;
            table.querySelector('tr:last-child').insertAdjacentHTML('afterend', row);
        }};
    </script>
</body>
</html>"""
    return html

@app.route('/logs/stream', methods=['GET'])
def logs_stream():
    def generate():
        q = subscribe()
        try:
            while True:
                entry = q.get()
                yield f"data: {json.dumps(entry)}\n\n"
        finally:
            unsubscribe(q)
    return Response(stream_with_context(generate()),
                    mimetype='text/event-stream')

@app.route('/schedules', methods=['GET'])
def schedules():
    return jsonify(get_schedules())

@app.route('/status', methods=['GET'])
def get_status():
    try:
        return jsonify(load_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/preset/<name>', methods=['POST'])
def run_preset(name):
    try:
        apply_preset(name)
        return jsonify({"status": "success", "preset": name})
    except Exception as e:
        app.logger.error(f"Error applying preset {name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/presence/enter', methods=['POST'])
def presence_enter():
    try:
        on_enter()
        return jsonify({"status": "success", "action": "presence_enter"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/presence/leave', methods=['POST'])
def presence_leave():
    try:
        on_leave()
        return jsonify({"status": "success", "action": "presence_leave"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hue/on', methods=['POST'])
def hue_on():
    try:
        HueCode().apply_preset('on')
        update_device_state("hue", "preset", "on")
        return jsonify({"status": "success", "action": "hue_on"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hue/off', methods=['POST'])
def hue_off():
    try:
        HueCode().apply_preset('off')
        update_device_state("hue", "preset", "off")
        return jsonify({"status": "success", "action": "hue_off"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/globe/<state>', methods=['POST'])
def switchbot_globe(state):
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        SwitchBotCode().set_globe(state == 'on')
        update_device_state("switchbot", "globe", state)
        return jsonify({"status": "success", "device": "globe", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/curtain/<state>', methods=['POST'])
def switchbot_curtain(state):
    if state not in ['open', 'close']:
        return jsonify({"error": "Invalid state, use open/close"}), 400
    try:
        SwitchBotCode().set_curtain(state == 'open')
        update_device_state("switchbot", "curtain", state)
        return jsonify({"status": "success", "device": "curtain", "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/switchbot/edison/<state>', methods=['POST'])
def switchbot_edison(state):
    if state not in ['on', 'off']:
        return jsonify({"error": "Invalid state"}), 400
    try:
        SwitchBotCode().set_edison(state == 'on')
        update_device_state("switchbot", "edison", state)
        return jsonify({"status": "success", "device": "edison", "state": state})
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
            if sb_mode == 2:
                hk_state = 2
            elif sb_mode == 5:
                hk_state = 1
            else:
                hk_state = 3
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
        new_state = {**current_ac_state, "on": True, "mode": sb_mode}
        update_device_state("switchbot", "ac", new_state)
        return jsonify({"status": "success", "targetHeatingCoolingState": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run(port=5001):
    app.run(host='0.0.0.0', port=port, threaded=True)
