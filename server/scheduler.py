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
    try:
        with open(filepath) as f:
            schedules = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. No schedules loaded.")
        return
    for s in schedules:
        scheduler.add_job(
            _resolve_action(s["action"]),
            CronTrigger.from_crontab(s["cron"]),
            id=s["id"],
            replace_existing=True,
        )
        print(f"Scheduled: {s['id']} ({s['cron']}) -> {s['action']}")

def get_schedules():
    return [
        {
            "id": job.id,
            "next_run": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]

def start():
    load_schedules()
    scheduler.start()
