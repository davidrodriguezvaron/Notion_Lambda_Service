"""Task entity and its due date, independent of Notion or the email."""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DueDate:
    """A due date resolved to the configured time zone."""

    day: date
    time: Optional[str] = None  # "10:30 a. m." when the source has a time

    @classmethod
    def parse(cls, value: Optional[str], tz: ZoneInfo) -> Optional["DueDate"]:
        """
        Parses an ISO start value ("2026-11-16" or an ISO datetime).

        Datetimes are converted to the configured zone, so a task due at 11 p. m.
        in Bogota is not shown on the next day.
        """
        if not value:
            return None
        try:
            if "T" not in value:
                return cls(day=date.fromisoformat(value))
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"Could not parse due date '{value}'; shown as undated")
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tz)
        local = parsed.astimezone(tz)
        return cls(day=local.date(), time=format_time(local))


def format_time(value: datetime) -> str:
    """Formats a time as "10:30 a. m." (Colombian style)."""
    hour = value.hour % 12 or 12
    suffix = "a. m." if value.hour < 12 else "p. m."
    return f"{hour}:{value.minute:02d} {suffix}"


@dataclass(frozen=True)
class Task:
    """
    A task as the application sees it.

    `due` keeps the raw ISO start value so a reschedule can preserve the time
    and offset exactly as they were stored.
    """

    id: str
    title: str
    due: Optional[str] = None
    notes: str = ""
    area: Optional[str] = None
    recurrence: Optional[str] = None
    url: Optional[str] = None

    def due_date(self, tz: ZoneInfo) -> Optional[DueDate]:
        return DueDate.parse(self.due, tz)
