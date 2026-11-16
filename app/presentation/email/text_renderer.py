"""Plain text alternative of the digest, with the same sections as the HTML."""

from typing import List, Sequence

from app.domain.agenda import Agenda, AgendaItem
from app.domain.recurrence import RescheduledTask
from app.presentation.email import copy
from app.presentation.email.spanish_dates import format_long_date
from app.presentation.email.theme import SECTION_STYLES


class PlainTextRenderer:
    def __init__(self, notion_tasks_url: str = ""):
        self._notion_tasks_url = notion_tasks_url

    def render(
        self,
        agenda: Agenda,
        rescheduled: Sequence[RescheduledTask],
        warnings: Sequence[str],
    ) -> str:
        lines = [copy.subject(agenda), format_long_date(agenda.today), ""]
        if agenda.is_empty:
            lines += ["Nada pendiente hoy.", ""]
        for key, items in agenda.sections():
            if items:
                lines += _section(key, items, agenda)
        if rescheduled:
            lines.append(f"REPROGRAMADAS HOY ({len(rescheduled)})")
            lines += [f"- {r.title}: {copy.moved_label(r)}" for r in rescheduled]
            lines.append("")
        for warning in warnings:
            lines += [f"Aviso: {warning}", ""]
        if self._notion_tasks_url:
            lines.append(f"{copy.NOTION_LINK_TEXT}: {self._notion_tasks_url}")
        return "\n".join(lines).rstrip() + "\n"


def _section(key: str, items: List[AgendaItem], agenda: Agenda) -> List[str]:
    lines = [f"{SECTION_STYLES[key][0].upper()} ({len(items)})"]
    for item in items:
        task = item.task
        area = f" [{task.area}]" if task.area else ""
        when = copy.when_label(item, agenda.today)
        lines.append(f"- {copy.title_of(item)}{area} ({when})")
        lines += [
            f"    {line.strip()}" for line in task.notes.splitlines() if line.strip()
        ]
        if task.url:
            lines.append(f"    {task.url}")
    lines.append("")
    return lines
