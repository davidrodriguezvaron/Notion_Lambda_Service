"""Splits pending tasks into overdue, today and upcoming."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.domain.task import DueDate, Task


@dataclass(frozen=True)
class AgendaItem:
    """A task together with its due date in the configured time zone."""

    task: Task
    due: Optional[DueDate]

    @property
    def day(self) -> Optional[date]:
        return self.due.day if self.due else None

    @property
    def time(self) -> Optional[str]:
        return self.due.time if self.due else None


@dataclass
class Agenda:
    today: date
    upcoming_days: int = 3
    overdue: List[AgendaItem] = field(default_factory=list)
    due_today: List[AgendaItem] = field(default_factory=list)
    upcoming: List[AgendaItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.overdue) + len(self.due_today) + len(self.upcoming)

    @property
    def is_empty(self) -> bool:
        return self.total == 0

    def sections(self) -> List[Tuple[str, List[AgendaItem]]]:
        """Sections in display order, including empty ones."""
        return [
            ("overdue", self.overdue),
            ("today", self.due_today),
            ("upcoming", self.upcoming),
        ]


def build_agenda(
    tasks: Iterable[Task], today: date, upcoming_days: int, tz: ZoneInfo
) -> Agenda:
    """Groups tasks by their local due date; tasks past the window are dropped."""
    window = max(0, upcoming_days)
    limit = today + timedelta(days=window)
    agenda = Agenda(today=today, upcoming_days=window)
    for task in tasks:
        item = AgendaItem(task=task, due=task.due_date(tz))
        day = item.day or today
        if day < today:
            agenda.overdue.append(item)
        elif day == today:
            agenda.due_today.append(item)
        elif day <= limit:
            agenda.upcoming.append(item)
    for _, items in agenda.sections():
        items.sort(key=_sort_key)
    return agenda


def _sort_key(item: AgendaItem):
    # All-day tasks first, then by time of day, then by title.
    return (item.day or date.min, 1 if item.time else 0, item.task.title.lower())
