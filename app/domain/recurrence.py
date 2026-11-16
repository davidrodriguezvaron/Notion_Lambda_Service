"""
Recurrence rules for tasks that repeat.

A recurring task is a single page that is reused: when it is done, it moves
one interval forward from its own date (not from today).
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional, Tuple

# Interval name (the Notion "Recurrencia" option) -> ("days" | "months", amount)
INTERVALS: Dict[str, Tuple[str, int]] = {
    "Semanal": ("days", 7),
    "Quincenal": ("days", 14),
    "Mensual": ("months", 1),
    "Bimestral": ("months", 2),
    "Trimestral": ("months", 3),
    "Semestral": ("months", 6),
    "Anual": ("months", 12),
}


@dataclass(frozen=True)
class RescheduledTask:
    title: str
    new_day: date
    url: Optional[str] = None
    previous_day: Optional[date] = None


def is_supported(interval: Optional[str]) -> bool:
    return interval in INTERVALS


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


def next_date(current: date, interval: str) -> date:
    """Returns the next occurrence, one interval after current."""
    kind, amount = INTERVALS[interval]
    if kind == "days":
        return current + timedelta(days=amount)
    return add_months(current, amount)


def next_start(start: str, interval: str) -> Tuple[date, date, str]:
    """
    Moves an ISO start value one interval forward, keeping its time part.

    Returns (previous day, new day, new ISO start value).
    """
    day_part, separator, time_part = start.partition("T")
    current = date.fromisoformat(day_part)
    new_day = next_date(current, interval)
    return current, new_day, f"{new_day.isoformat()}{separator}{time_part}"
