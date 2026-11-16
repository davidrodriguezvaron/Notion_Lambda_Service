"""The Spanish wording of the digest, shared by the HTML and the plain text."""

from datetime import date
from typing import List

from app.domain.agenda import Agenda, AgendaItem
from app.domain.recurrence import RescheduledTask
from app.presentation.email.spanish_dates import format_day_month, relative_label

UNTITLED = "(sin título)"
EMPTY_PREHEADER = "Nada pendiente hoy. Disfruta el día."
NOTION_LINK_TEXT = "Abrir Tareas en Notion"


def plural(count: int, singular: str, plural_form: str) -> str:
    return f"{count} {singular if count == 1 else plural_form}"


def join_es(parts: List[str]) -> str:
    """["a", "b", "c"] -> "a, b y c"."""
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " y " + parts[-1]


def summary(agenda: Agenda) -> str:
    """ "2 vencidas, 3 hoy, 1 próxima" (only the parts that apply)."""
    parts = []
    if agenda.overdue:
        parts.append(plural(len(agenda.overdue), "vencida", "vencidas"))
    if agenda.due_today:
        parts.append(f"{len(agenda.due_today)} hoy")
    if agenda.upcoming:
        parts.append(plural(len(agenda.upcoming), "próxima", "próximas"))
    return ", ".join(parts) if parts else "nada pendiente hoy"


def subject(agenda: Agenda) -> str:
    return f"Tareas: {summary(agenda)}"


def preheader(agenda: Agenda) -> str:
    return EMPTY_PREHEADER if agenda.is_empty else summary(agenda).capitalize()


def greeting(agenda: Agenda) -> str:
    """One sentence that sums up the day."""
    if agenda.is_empty:
        return "No tienes nada pendiente. Disfruta el día."
    today_count = len(agenda.due_today)
    first = (
        f"Hoy tienes {plural(today_count, 'tarea', 'tareas')}"
        if today_count
        else "Hoy no tienes tareas nuevas"
    )
    extra = []
    if agenda.overdue:
        extra.append(plural(len(agenda.overdue), "vencida", "vencidas") + " por cerrar")
    if agenda.upcoming:
        extra.append(f"{len(agenda.upcoming)} en los próximos días")
    return join_es([first] + extra) + "."


def title_of(item: AgendaItem) -> str:
    return item.task.title or UNTITLED


def when_label(item: AgendaItem, today: date) -> str:
    """ "hace 2 días", "hoy, 10:30 a. m.", or "sin fecha"."""
    if not item.due:
        return "sin fecha"
    label = relative_label(item.due.day, today)
    return f"{label}, {item.due.time}" if item.due.time else label


def moved_label(item: RescheduledTask) -> str:
    """ "del 21 nov al 21 dic", or "al 21 dic" when the old date is unknown."""
    new = format_day_month(item.new_day)
    if item.previous_day:
        return f"del {format_day_month(item.previous_day)} al {new}"
    return f"al {new}"
