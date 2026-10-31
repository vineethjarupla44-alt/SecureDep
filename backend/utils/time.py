"""Timezone helpers used by maturity and alert calculations."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app, has_app_context


def configured_timezone():
    """Return the configured IANA timezone, with a safe IST default."""
    timezone_name = current_app.config.get("APP_TIMEZONE", "Asia/Kolkata") if has_app_context() else "Asia/Kolkata"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        # Windows Python builds may not ship the IANA database. Keep the
        # default business timezone deterministic even before tzdata installs.
        fixed_offsets = {
            "Asia/Kolkata": timedelta(hours=5, minutes=30),
            "Pacific/Kiritimati": timedelta(hours=14),
            "UTC": timedelta(0),
        }
        return timezone(fixed_offsets.get(timezone_name, timedelta(0)), name=timezone_name)


def local_business_date() -> date:
    """Return today's date in the application's configured business timezone."""
    return datetime.now(configured_timezone()).date()
