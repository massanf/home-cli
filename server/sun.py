import json
from datetime import datetime, timedelta, timezone

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from astral import LocationInfo
from astral.sun import sun as astral_sun

from .scheduler import _resolve_action, scheduler

LOCATION_FILE = "config/location.json"
SUN_SCHEDULES_FILE = "config/sun_schedules.json"


def _load_location() -> LocationInfo:
    with open(LOCATION_FILE) as f:
        data = json.load(f)
    return LocationInfo(
        name=data.get("name", "Home"),
        region=data.get("region", ""),
        timezone=data["timezone"],
        latitude=data["latitude"],
        longitude=data["longitude"],
    )


def _load_sun_schedules() -> list:
    try:
        with open(SUN_SCHEDULES_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def schedule_sun_jobs():
    location = _load_location()
    now = datetime.now(timezone.utc)

    for job in _load_sun_schedules():
        for days_ahead in (0, 1):
            date = (now + timedelta(days=days_ahead)).date()
            s = astral_sun(location.observer, date=date, tzinfo=location.timezone)
            fire_time = s[job["event"]] + timedelta(
                minutes=job.get("offset_minutes", 0)
            )
            if fire_time > now:
                break
        else:
            print(f"Sun-schedule '{job['id']}': could not find a future fire time.")
            continue
        scheduler.add_job(
            _resolve_action(job["action"]),
            DateTrigger(run_date=fire_time),
            id=job["id"],
            replace_existing=True,
        )
        print(f"Sun-scheduled: {job['id']} at {fire_time} -> {job['action']}")


def start():
    schedule_sun_jobs()
    scheduler.add_job(
        schedule_sun_jobs,
        CronTrigger.from_crontab("0 12 * * *"),
        id="__sun_bootstrap__",
        replace_existing=True,
    )
