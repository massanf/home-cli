import base64
import hashlib
import hmac
import json
import time
import uuid

import requests

from .logger import log_request

DEVICE_ID_GLOBE = "9888E0C6BE2E"
DEVICE_ID_CURTAIN = "E50D4BD20F40"
DEVICE_ID_EDISON = "02-202511170026-84472226"
DEVICE_ID_AC = "02-202508120124-76089867"


class SwitchBotCode:
    def __init__(self):
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        self.token = secrets["token"]
        self.secret = secrets["secret"]
        self.base_url = "https://api.switch-bot.com/v1.1"

    def _get_headers(self):
        nonce = str(uuid.uuid4())
        t = int(round(time.time() * 1000))
        string_to_sign = bytes(f"{self.token}{t}{nonce}", "utf-8")
        secret = bytes(self.secret, "utf-8")
        sign = base64.b64encode(
            hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest()
        )
        return {
            "Authorization": self.token,
            "t": str(t),
            "sign": str(sign, "utf-8"),
            "nonce": nonce,
            "Content-Type": "application/json; charset=utf8",
        }

    def get_devices(self):
        url = f"{self.base_url}/devices"
        response = requests.get(url, headers=self._get_headers())
        resp_json = response.json()
        log_request("GET", url, status=response.status_code, response=resp_json)
        return resp_json

    def send_command(
        self, device_id, command, parameter="default", command_type="command"
    ):
        url = f"{self.base_url}/devices/{device_id}/commands"
        payload = {
            "command": command,
            "parameter": parameter,
            "commandType": command_type,
        }
        response = requests.post(url, headers=self._get_headers(), json=payload)
        resp_json = response.json()
        if resp_json.get("statusCode") != 100:
            print(f"Error sending command to {device_id}: {resp_json}")
        log_request(
            "POST",
            url,
            payload=payload,
            status=response.status_code,
            response=resp_json,
        )
        return resp_json

    def set_globe(self, on: bool):
        return self.send_command(DEVICE_ID_GLOBE, "turnOn" if on else "turnOff")

    def set_curtain(self, open: bool):
        return self.send_command(DEVICE_ID_CURTAIN, "turnOn" if open else "turnOff")

    def set_curtain_quiet(self, open: bool):
        position = 0 if open else 100
        return self.send_command(DEVICE_ID_CURTAIN, "setPosition", f"0,1,{position}")

    def set_edison(self, on: bool):
        return self.send_command(DEVICE_ID_EDISON, "turnOn" if on else "turnOff")

    def set_ac(self, temperature: int, mode: int, fan_speed: int, on: bool):
        power_state = "on" if on else "off"
        parameter = f"{temperature},{mode},{fan_speed},{power_state}"
        return self.send_command(DEVICE_ID_AC, "setAll", parameter)
