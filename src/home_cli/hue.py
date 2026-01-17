import json
import requests

# Presets can be a single dict (applied to all lights) or a dict of light_ids (scene)
PRESETS = {
    'on': {'hue': 7894, 'sat': 185, 'bri': 255, 'on': True},
    'off': {'on': False}, # Global Off
    'bar': {'hue': 6291, 'sat': 251, 'bri': 70, 'on': True},
    'theatre': {
        '1': {'hue': 7875, 'sat': 187, 'bri': 97, 'on': True},
        '2': {'hue': 7875, 'sat': 187, 'bri': 70, 'on': False},
        '3': {'hue': 7875, 'sat': 187, 'bri': 70, 'on': False},
        '4': {'hue': 7857, 'sat': 187, 'bri': 121, 'on': True},
    },
    'dim': {'hue': 6291, 'sat': 251, 'bri': 70, 'on':True},
    'off': {'hue': 1000, 'sat': 100, 'bri': 0, 'on': False}
}

class HueCode:
    def __init__(self):
        with open('secrets.json', 'r') as f:
            secrets = json.load(f)
        self.bridge_ip = secrets['hue_bridge_ip']
        self.username = secrets['hue_username']
        self.base_url = f"http://{self.bridge_ip}/api/{self.username}"

    def get_lights(self):
        """Returns a dictionary of all lights."""
        url = f"{self.base_url}/lights"
        try:
            response = requests.get(url)
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting lights: {e}")
            return {}

    def get_sensors(self):
        """Returns a dictionary of all sensors."""
        url = f"{self.base_url}/sensors"
        try:
            response = requests.get(url)
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting sensors: {e}")
            return {}

    def set_light(self, light_id: int, on: bool = None, bri: int = None, hue: int = None, sat: int = None, **kwargs):
        """
        Control a light state.
        :param light_id: ID of the light (e.g., 1, 2)
        :param on: True/False
        :param bri: 0-254 (brightness)
        :param hue: 0-65535
        :param sat: 0-254
        """
        url = f"{self.base_url}/lights/{light_id}/state"
        payload = {}
        
        if on is not None:
            payload['on'] = on
        if bri is not None:
            payload['bri'] = bri
        if hue is not None:
            payload['hue'] = hue
        if sat is not None:
            payload['sat'] = sat

        if not payload:
            print("No changes specified.")
            return

        try:
            response = requests.put(url, json=payload)
            return response.json()
        except requests.RequestException as e:
            print(f"Error setting light {light_id}: {e}")
            return None

    def apply_preset(self, preset_name: str):
        if preset_name not in PRESETS:
            print(f"Preset '{preset_name}' not found.")
            return None

        preset_data = PRESETS[preset_name]
        results = {}
        
        # Get all available lights
        lights = self.get_lights()
        
        for light_id in lights:
            light_str = str(light_id)
            
            # Check if this preset is a "Scene" (dict of light IDs)
            if isinstance(preset_data, dict) and any(k.isdigit() for k in preset_data.keys()):
                # It is a scene, look for this light's config
                if light_str in preset_data:
                    results[light_id] = self.set_light(int(light_id), **preset_data[light_str])
                else:
                    # Light not in user's scene definition, do nothing
                    pass
            else:
                # It's a global preset, apply to all lights
                results[light_id] = self.set_light(int(light_id), **preset_data)
                
        return results

    def get_light_state(self, light_id: int):
        """Helper to print current state as a Python dict for saving as preset"""
        lights = self.get_lights()
        if str(light_id) in lights:
             state = lights[str(light_id)]['state']
             # Format output to be copy-paste ready
             print(f"'{light_id}': {{'hue': {state.get('hue')}, 'sat': {state.get('sat')}, 'bri': {state.get('bri')}, 'on': {state.get('on')}}},")

    def set_rgb(self, light_id: int, r: int, g: int, b: int):
        """
        Set light color using RGB values (0-255).
        Approximation using Hue/Sat.
        """
        # Very simple RGB to Hue/Sat conversion
        # For better accuracy, XY conversion is recommended but complex
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        hue = int(h * 65535)
        sat = int(s * 254)
        bri = int(v * 254)
        
        return self.set_light(light_id, on=True, hue=hue, sat=sat, brightness=bri)

if __name__ == "__main__":
    hue = HueCode()
    
    # List all lights
    lights = hue.get_lights()
    print("Found Lights:")
    for id, data in lights.items():
        print(f"ID: {id}, Name: {data['name']}, On: {data['state']['on']}")
    
    # Example Usage:
    # Turn on light ID 1
    # for id, data in lights.items():
    #     print(hue.set_light(id, on=True))
    
    # Set light ID 1 to Red (approx hue=0, sat=254)
    # print(hue.set_light(1, on=True, hue=0, sat=254, brightness=254))
    for id, data in lights.items():
        hue.get_light_state(id)
    
    print(hue.apply_preset('on'))
