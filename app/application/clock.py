"""Clock that answers "what day is it" in the user's time zone, not in UTC."""

from datetime import date, datetime, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ZonedClock:
    def __init__(self, tz: ZoneInfo, now: Optional[Callable[[], datetime]] = None):
        self._tz = tz
        self._now = now or utc_now

    def today(self) -> date:
        return self._now().astimezone(self._tz).date()
