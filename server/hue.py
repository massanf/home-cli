import json
import requests

PRESETS = {
    'on': {'hue': 7894, 'sat': 185, 'bri': 255, 'on': True},
    'off': {'hue': 1000, 'sat': 100, 'bri': 0, 'on': False},
    'bar': {'hue': 6291, 'sat': 251, 'bri': 70, 'on': True},
    'theatre': {
        '1': {'hue': 7875, 'sat': 187, 'bri': 97, 'on': True},
        '2': {'hue': 7875, 'sat': 187, 'bri': 70, 'on': False},
        '3': {'hue': 7875, 'sat': 187, 'bri': 70, 'on': False},
        '4': {'hue': 7857, 'sat': 187, 'bri': 121, 'on': True},
    },
    'dim': {'hue': 6291, 'sat': 251, 'bri': 70, 'on': True},
}

class HueCode:
    def __init__(self):
        with open('secrets.json', 'r') as f:
            secrets = json.load(f)
        self.bridge_ip = secrets['hue_bridge_ip']
        self.username = secrets['hue_username']
        self.base_url = f"http://{self.bridge_ip}/api/{self.username}"

    def get_lights(self):
        try:
            return requests.get(f"{self.base_url}/lights").json()
        except requests.RequestException as e:
            print(f"Error getting lights: {e}")
            return {}

    def set_light(self, light_id: int, on: bool = None, bri: int = None, hue: int = None, sat: int = None, **kwargs):
        url = f"{self.base_url}/lights/{light_id}/state"
        payload = {}
        if on is not None: payload['on'] = on
        if bri is not None: payload['bri'] = bri
        if hue is not None: payload['hue'] = hue
        if sat is not None: payload['sat'] = sat
        if not payload:
            return
        try:
            return requests.put(url, json=payload).json()
        except requests.RequestException as e:
            print(f"Error setting light {light_id}: {e}")

    def apply_preset(self, preset_name: str):
        if preset_name not in PRESETS:
            print(f"Preset '{preset_name}' not found.")
            return
        preset_data = PRESETS[preset_name]
        lights = self.get_lights()
        for light_id in lights:
            if any(k.isdigit() for k in preset_data.keys()):
                if str(light_id) in preset_data:
                    self.set_light(int(light_id), **preset_data[str(light_id)])
            else:
                self.set_light(int(light_id), **preset_data)
