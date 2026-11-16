"""
Reopens recurring tasks that were marked as Done.

Rules:
- Only tasks with Status = Done and a Recurrencia value are touched. Tasks you
  have not checked are never moved, so an unpaid bill stays overdue.
- The next date is computed from the task's own Fecha (not from today) and
  advances exactly one interval.
- The task goes back to Not Started in the same PATCH that moves the date, so
  a second run on the same day finds it Not Started and leaves it alone
  (idempotent without extra bookkeeping).
- No new pages are created: the same page is reused, as when you move the
  date by hand.
- Month based intervals keep the day of the month and use the last day when
  the target month is shorter (31 Jan -> 28 Feb). There is no anchor day, so
  a task that lands on the 28th stays on the 28th afterwards.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.common.integrations.notion.exceptions import NotionApiError
from app.common.logger.logger import get_logger
from app.common.utils.dates import add_days, add_months

logger = get_logger(__name__)

# Interval name -> ("days" | "months", amount)
INTERVALS: Dict[str, Tuple[str, int]] = {
    "Semanal": ("days", 7),
    "Quincenal": ("days", 14),
    "Mensual": ("months", 1),
    "Bimestral": ("months", 2),
    "Trimestral": ("months", 3),
    "Semestral": ("months", 6),
    "Anual": ("months", 12),
}

PERMISSION_HINT = (
    "La integración de Notion no tiene permiso para editar páginas. "
    "Actívalo en notion.so/profile/integrations > tu integración > "
    "Capabilities > Update content, y confirma que la base Tareas esté "
    "conectada a la integración."
)


@dataclass(frozen=True)
class Rescheduled:
    titulo: str
    nueva_fecha: date
    url: Optional[str] = None
    fecha_anterior: Optional[date] = None


@dataclass
class RecurrenceResult:
    rescheduled: List[Rescheduled]
    warnings: List[str]


def next_date(current: date, interval: str) -> date:
    """Returns the next occurrence, one interval after current."""
    kind, amount = INTERVALS[interval]
    if kind == "days":
        return add_days(current, amount)
    return add_months(current, amount)


def _split_start(start: str) -> Tuple[date, Optional[str]]:
    """Splits a Notion start value into its date and the time suffix, if any."""
    if "T" in start:
        day_part, time_part = start.split("T", 1)
        return date.fromisoformat(day_part), time_part
    return date.fromisoformat(start), None


class RecurrenceService:
    def __init__(self, task_repository):
        self.task_repository = task_repository

    def process(self) -> RecurrenceResult:
        result = RecurrenceResult(rescheduled=[], warnings=[])
        try:
            tasks = self.task_repository.get_done_recurring_tasks()
        except NotionApiError as e:
            if e.status_code == 400:
                # Usually: the Recurrencia property does not exist yet.
                logger.warning(f"Recurrence query skipped: {e}")
                return result
            raise

        for task in tasks:
            try:
                item = self._reschedule(task)
            except NotionApiError as e:
                if e.status_code in (401, 403):
                    logger.error(f"{PERMISSION_HINT} ({e})")
                    result.warnings.append(PERMISSION_HINT)
                    break
                logger.error(f"Could not reschedule '{task.get('titulo')}': {e}")
                result.warnings.append(
                    f"No se pudo reprogramar \"{task.get('titulo')}\"."
                )
                continue
            if item:
                result.rescheduled.append(item)
        return result

    def _reschedule(self, task: Dict) -> Optional[Rescheduled]:
        interval = task.get("recurrencia")
        start = task.get("fecha")
        if interval not in INTERVALS or not start:
            logger.warning(
                f"Skipping '{task.get('titulo')}': recurrence={interval}, fecha={start}"
            )
            return None

        current, time_part = _split_start(start)
        new_day = next_date(current, interval)
        new_start = (
            f"{new_day.isoformat()}T{time_part}" if time_part else new_day.isoformat()
        )

        self.task_repository.reschedule_task(task["id"], new_start)
        logger.info(f"Rescheduled '{task.get('titulo')}' from {start} to {new_start}")
        return Rescheduled(
            titulo=task.get("titulo") or "(sin título)",
            nueva_fecha=new_day,
            url=task.get("url"),
            fecha_anterior=current,
        )
