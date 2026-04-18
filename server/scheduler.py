import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .presence import on_enter, on_leave
from .presets import apply_preset
from .state import update_device_state
from .switchbot import SwitchBotCode

scheduler = BackgroundScheduler()

ACTIONS = {
    "presence:enter": on_enter,
    "presence:leave": on_leave,
}

def _resolve_action(action: str):
    if action in ACTIONS:
        return ACTIONS[action]
    if action.startswith("preset:"):
        name = action.split(":", 1)[1]
        return lambda: apply_preset(name)
    if action.startswith("switchbot:curtain:"):
        state = action.split(":")[-1]
        return lambda: (
            SwitchBotCode().set_curtain(state == "open"),
            update_device_state("switchbot", "curtain", state),
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
