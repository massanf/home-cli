from .hue import HueCode
from .state import load_snapshot, save_snapshot, update_device_state
from .switchbot import SwitchBotCode

NON_VOLATILE = {
    "switchbot": ["globe", "edison"],
    "hue": ["preset"],
}

def on_leave():
    save_snapshot()
    print("Presence: left. Turning off lights...")
    sb = SwitchBotCode()
    sb.set_globe(False)
    update_device_state("switchbot", "globe", "off")
    sb.set_edison(False)
    update_device_state("switchbot", "edison", "off")
    HueCode().apply_preset("off")
    update_device_state("hue", "preset", "off")

def on_enter():
    print("Presence: entered. Restoring state...")
    snapshot = load_snapshot()
    if not snapshot:
        print("No snapshot found.")
        return
    sb = SwitchBotCode()
    for device in NON_VOLATILE.get("switchbot", []):
        state = snapshot.get("switchbot", {}).get(device)
        if state is None:
            continue
        if device == "globe":
            sb.set_globe(state == "on")
        elif device == "edison":
            sb.set_edison(state == "on")
        update_device_state("switchbot", device, state)
    for device in NON_VOLATILE.get("hue", []):
        state = snapshot.get("hue", {}).get(device)
        if state is None:
            continue
        if device == "preset":
            HueCode().apply_preset(state)
        update_device_state("hue", device, state)
