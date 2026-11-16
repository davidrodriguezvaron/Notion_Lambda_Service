"""
Date helpers for the task digest.

Spanish day and month names are defined here on purpose: the Lambda runtime
does not ship the es_CO locale, so strftime("%A") would return English names.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DAYS_SHORT = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
MONTHS_SHORT = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]


@dataclass(frozen=True)
class TaskDate:
    """A Notion date resolved to the configured time zone."""

    day: date
    time: Optional[str] = None  # "10:30 a. m." when the Notion date has a time


def today_in(tz: ZoneInfo, now: Optional[datetime] = None) -> date:
    """
    Returns the current calendar date in the given time zone.

    Args:
        tz: Target time zone.
        now: Optional aware datetime used instead of the real clock (tests).
    """
    current = now or datetime.now(timezone.utc)
    return current.astimezone(tz).date()


def parse_notion_date(value: Optional[str], tz: ZoneInfo) -> Optional[TaskDate]:
    """
    Parses a Notion date start value ("2026-11-16" or an ISO datetime).

    Datetimes are converted to the configured zone so a task due at 11 p. m.
    in Bogota is not shown on the next day.
    """
    if not value:
        return None
    try:
        if "T" not in value:
            return TaskDate(day=date.fromisoformat(value))
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    local = parsed.astimezone(tz)
    return TaskDate(day=local.date(), time=format_time(local))


def format_time(value: datetime) -> str:
    """Formats a time as "10:30 a. m." (Colombian style)."""
    hour = value.hour % 12 or 12
    suffix = "a. m." if value.hour < 12 else "p. m."
    return f"{hour}:{value.minute:02d} {suffix}"


def format_long_date(value: date) -> str:
    """Formats a date as "Lunes, 16 de noviembre"."""
    return f"{DAYS[value.weekday()].capitalize()}, {value.day} de {MONTHS[value.month - 1]}"


def format_short_date(value: date) -> str:
    """Formats a date as "jue 19 nov"."""
    return f"{DAYS_SHORT[value.weekday()]} {value.day} {MONTHS_SHORT[value.month - 1]}"


def format_day_month(value: date) -> str:
    """Formats a date as "21 dic"."""
    return f"{value.day} {MONTHS_SHORT[value.month - 1]}"


def relative_label(target: date, today: date) -> str:
    """
    Human label relative to today: "hace 2 días", "ayer", "hoy", "mañana",
    "en 2 días, jue 19 nov".
    """
    delta = (target - today).days
    if delta == 0:
        return "hoy"
    if delta == -1:
        return "ayer"
    if delta < -1:
        return f"hace {-delta} días"
    if delta == 1:
        return "mañana"
    return f"en {delta} días, {format_short_date(target)}"


def add_days(value: date, days: int) -> date:
    return value + timedelta(days=days)


def add_months(value: date, months: int) -> date:
    """
    Adds calendar months keeping the day of the month, or the last day when
    the target month is shorter (31 Jan + 1 month -> 28/29 Feb).
    """
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(value.day, last_day))
