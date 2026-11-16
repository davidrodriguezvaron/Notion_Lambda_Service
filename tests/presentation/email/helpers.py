from datetime import date
from zoneinfo import ZoneInfo

from app.domain.agenda import build_agenda
from tests.fakes import task

TODAY = date(2026, 11, 16)  # Monday, day 320 of the year
TZ = ZoneInfo("America/Bogota")
NOTION_URL = "https://www.notion.so/db"


def agenda(*tasks, upcoming_days=3):
    return build_agenda(list(tasks), TODAY, upcoming_days, TZ)


def sample_agenda():
    """One overdue, one today (with time and notes) and one upcoming task."""
    return agenda(
        task("Pagar ENEL", "2026-11-14", area="Finanzas", task_id="p1"),
        task(
            "Vacuna <Nala>",
            "2026-11-16T10:30:00.000-05:00",
            area="Gatos",
            notes="Ver https://example.com/a?b=1&c=2.\nOtra línea www.test.co",
            task_id="p2",
        ),
        task("Cita mango", "2026-11-18", url=None),
    )
