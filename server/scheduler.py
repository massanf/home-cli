import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .hue import HueCode
from .presets import apply_preset
from .state import update_device_state
from .switchbot import SwitchBotCode

scheduler = BackgroundScheduler()

def _resolve_action(action: str):
    if action.startswith("preset:"):
        name = action.split(":", 1)[1]
        return lambda: apply_preset(name)
    if action.startswith("switchbot:globe:"):
        state = action.split(":")[-1]
        return lambda: (
            SwitchBotCode().set_globe(state == "on"),
            update_device_state("switchbot", "globe", state),
        )
    if action.startswith("switchbot:edison:"):
        state = action.split(":")[-1]
        return lambda: (
            SwitchBotCode().set_edison(state == "on"),
            update_device_state("switchbot", "edison", state),
        )
    if action.startswith("switchbot:curtain:"):
        state = action.split(":")[-1]
        return lambda: (
            SwitchBotCode().set_curtain(state == "open"),
            update_device_state("switchbot", "curtain", state),
        )
    if action.startswith("hue:"):
        preset = action.split(":", 1)[1]
        return lambda: (
            HueCode().apply_preset(preset),
            update_device_state("hue", "preset", preset),
        )
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
