import json
import time
import hashlib
import hmac
import base64
import uuid
import requests

# Device IDs
DEVICE_ID_GLOBE = '9888E0C6BE2E'
DEVICE_ID_CURTAIN = 'E50D4BD20F40' # Front Curtain (Master)
DEVICE_ID_LIGHT = '02-202511170026-84472226' # IR Light
DEVICE_ID_AC = '02-202508120124-76089867' # Air Conditioner

class SwitchBotCode:
    def __init__(self):
        with open('secrets.json', 'r') as f:
            secrets = json.load(f)
        self.token = secrets['token']
        self.secret = secrets['secret']
        self.base_url = "https://api.switch-bot.com/v1.1"

    def _get_headers(self):
        nonce = str(uuid.uuid4())
        t = int(round(time.time() * 1000))
        string_to_sign = '{}{}{}'.format(self.token, t, nonce)

        string_to_sign = bytes(string_to_sign, 'utf-8')
        secret = bytes(self.secret, 'utf-8')

        sign = base64.b64encode(
            hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest()
        )

        return {
            'Authorization': self.token,
            't': str(t),
            'sign': str(sign, 'utf-8'),
            'nonce': nonce,
            'Content-Type': 'application/json; charset=utf8'
        }

    def get_devices(self):
        url = f"{self.base_url}/devices"
        headers = self._get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def send_command(self, device_id, command, parameter='default', command_type='command'):
        url = f"{self.base_url}/devices/{device_id}/commands"
        headers = self._get_headers()
        payload = {
            "command": command,
            "parameter": parameter,
            "commandType": command_type
        }
        response = requests.post(url, headers=headers, json=payload)
        resp_json = response.json()
        if resp_json.get('statusCode') != 100:
            print(f"Error sending command to {device_id}: {resp_json}")
        return resp_json

    def set_globe(self, on: bool):
        command = "turnOn" if on else "turnOff"
        return self.send_command(DEVICE_ID_GLOBE, command)

    def set_curtain(self, open: bool):
        command = "turnOn" if open else "turnOff"
        return self.send_command(DEVICE_ID_CURTAIN, command)

    def set_light(self, on: bool):
        command = "turnOn" if on else "turnOff"
        return self.send_command(DEVICE_ID_LIGHT, command)

    def set_ac(self, temperature: int, mode: int, fan_speed: int, on: bool):
        """
        mode: 1 (auto), 2 (cool), 3 (dry), 4 (fan), 5 (heat)
        fan_speed: 1 (auto), 2 (low), 3 (medium), 4 (high)
        """
        power_state = "on" if on else "off"
        parameter = f"{temperature},{mode},{fan_speed},{power_state}"
        return self.send_command(DEVICE_ID_AC, "setAll", parameter)

if __name__ == "__main__":
    bot = SwitchBotCode()
    # Uncomment to test
    # print(bot.get_devices())
    print(bot.set_globe(False))
    # print(bot.set_curtain(False))
    print(bot.set_light(False))
    # print(bot.set_ac(21, 5, 1, True))
