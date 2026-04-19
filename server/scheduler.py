import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .hue import HueCode
from .presets import apply_preset
from .state import save_snapshot, update_device_state
from .switchbot import SwitchBotCode

scheduler = BackgroundScheduler()

def _resolve_action(action: str):
    if action.startswith("preset:"):
        name = action.split(":", 1)[1]
        return lambda: apply_preset(name)  # apply_preset calls save_snapshot internally
    if action.startswith("switchbot:globe:"):
        state = action.split(":")[-1]
        def _globe():
            SwitchBotCode().set_globe(state == "on")
            update_device_state("switchbot", "globe", state)
            save_snapshot()
        return _globe
    if action.startswith("switchbot:edison:"):
        state = action.split(":")[-1]
        def _edison():
            SwitchBotCode().set_edison(state == "on")
            update_device_state("switchbot", "edison", state)
            save_snapshot()
        return _edison
    if action.startswith("switchbot:curtain:"):
        state = action.split(":")[-1]
        def _curtain():
            sb = SwitchBotCode()
            if state == "quietopen":
                sb.set_curtain_quiet(True)
                canonical = "open"
            elif state == "quietclose":
                sb.set_curtain_quiet(False)
                canonical = "close"
            else:
                sb.set_curtain(state == "open")
                canonical = state
            update_device_state("switchbot", "curtain", canonical)
            save_snapshot()
        return _curtain
    if action.startswith("hue:"):
        preset = action.split(":", 1)[1]
        def _hue():
            HueCode().apply_preset(preset)
            update_device_state("hue", "preset", preset)
            save_snapshot()
        return _hue
    raise ValueError(f"Unknown action: {action}")

def load_schedules(filepath="config/schedules.json"):
    global _raw_schedules
    try:
        with open(filepath) as f:
            schedules = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. No schedules loaded.")
        return
    _raw_schedules = schedules
    for s in schedules:
        scheduler.add_job(
            _resolve_action(s["action"]),
            CronTrigger.from_crontab(s["cron"]),
            id=s["id"],
            replace_existing=True,
        )
        print(f"Scheduled: {s['id']} ({s['cron']}) -> {s['action']}")

_raw_schedules = []

def get_schedules():
    return _raw_schedules

def reload_schedules():
    for job in scheduler.get_jobs():
        job.remove()
    load_schedules()

def start():
    load_schedules()
    scheduler.start()
