"""Renders the digest as an email safe HTML page in the "paper" style."""

import html
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from app.domain.agenda import Agenda
from app.domain.recurrence import RescheduledTask
from app.presentation.email import copy
from app.presentation.email.html_primitives import attr, label, row
from app.presentation.email.html_task_list import section_html
from app.presentation.email.spanish_dates import format_month_year, weekday_name
from app.presentation.email.theme import (
    ACCENT,
    BODY,
    INK,
    MUTED,
    NOTE_BG,
    NOTE_RED_BG,
    RED,
    ROMAN,
    RULE,
    SANS,
    SERIF,
    dark_area_css,
)

TEMPLATE_PATH = Path(__file__).parent / "template.html"
PLACEHOLDER = re.compile(r"\{\{\w+\}\}")


@lru_cache(maxsize=1)
def load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


class PaperHtmlRenderer:
    def __init__(self, notion_tasks_url: str = ""):
        self._notion_tasks_url = notion_tasks_url

    def render(
        self,
        agenda: Agenda,
        rescheduled: Sequence[RescheduledTask],
        warnings: Sequence[str],
    ) -> str:
        parts = [_masthead(agenda.today), _dateline(agenda)]
        if agenda.is_empty:
            parts.append(_blank_page())
        else:
            parts.append(_stats(agenda))
            present = [(key, items) for key, items in agenda.sections() if items]
            for number, (key, items) in zip(ROMAN, present):
                parts.append(section_html(key, items, agenda.today, number))
        parts += [_note(rescheduled), _warnings(warnings), self._footer()]

        replacements = {
            "{{subject}}": html.escape(copy.subject(agenda)),
            "{{preheader}}": html.escape(copy.preheader(agenda)),
            "{{body}}": "".join(parts),
            "{{dark_area_css}}": dark_area_css(),
        }
        # One pass, so task text inserted into the body is never substituted.
        return PLACEHOLDER.sub(
            lambda m: replacements.get(m.group(0), m.group(0)), load_template()
        )

    def _footer(self) -> str:
        link = ""
        if self._notion_tasks_url:
            link = (
                f'<a href="{attr(self._notion_tasks_url)}" class="accent" '
                f'style="font-family:{SANS};font-size:12px;letter-spacing:0.15em;'
                f"text-transform:uppercase;color:{ACCENT};text-decoration:none;"
                f'font-weight:700;white-space:nowrap;">{copy.NOTION_LINK_TEXT} '
                "&rarr;</a>"
            )
        return row(
            f'<div class="rule-ink" style="border-top:1px solid {INK};"></div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0" style="margin-top:12px;"><tr>'
            f'<td class="muted" style="font-size:13px;line-height:19px;font-style:italic;'
            f'color:{MUTED};padding-right:12px;">Chulea una tarea para quitarla de esta '
            "página.</td>"
            f'<td align="right" valign="top">{link}</td></tr></table>',
            "32px 40px 36px 40px",
        )


def _masthead(today: date) -> str:
    """ "Tareas · Edición diaria" and the edition number (day of the year)."""
    edition = today.timetuple().tm_yday
    return row(
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr>'
        f'<td valign="top">{label("Tareas · Edición diaria", ACCENT, "accent")}</td>'
        f'<td valign="top" align="right">{label(f"Nº {edition}", MUTED, "muted")}'
        "</td></tr></table>"
        f'<div class="rule-ink" style="border-top:2px solid {INK};margin-top:10px;">'
        "</div>"
        f'<div class="rule-ink" style="border-top:1px solid {INK};margin-top:3px;">'
        "</div>",
        "36px 40px 0 40px",
    )


def _dateline(agenda: Agenda) -> str:
    """Large day numeral, weekday and the lead sentence."""
    today = agenda.today
    lead = f"Buenos días. {copy.greeting(agenda)}"
    return row(
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td valign="top" class="accent numeral" style="font-family:{SERIF};'
        f"font-size:86px;line-height:80px;font-weight:bold;color:{ACCENT};"
        f'padding-right:18px;">{today.day}</td>'
        '<td valign="top" style="padding-top:8px;">'
        f'<div class="ink weekday" style="font-size:28px;line-height:32px;'
        f'font-style:italic;color:{INK};">{weekday_name(today)}</div>'
        f'<div class="muted" style="font-size:16px;line-height:22px;color:{MUTED};">'
        f"{format_month_year(today)}</div></td></tr></table>"
        f'<p class="body" style="font-size:17px;line-height:27px;margin:18px 0 0 0;'
        f'color:{BODY};">{html.escape(lead)}</p>',
        "22px 40px 0 40px",
    )


def _stats(agenda: Agenda) -> str:
    """Newspaper style box: three big numerals split by thin rules."""
    overdue = len(agenda.overdue)
    stats = [
        (overdue, "Vencidas", RED if overdue else MUTED, "red" if overdue else "muted"),
        (len(agenda.due_today), "Hoy", ACCENT, "accent"),
        (len(agenda.upcoming), "Próximas", INK, "ink"),
    ]
    cells = []
    for index, (count, text, color, css_class) in enumerate(stats):
        divider = "" if index == 0 else f"border-left:1px solid {RULE};"
        cells.append(
            f'<td class="rule" width="33%" align="center" valign="top" '
            f'style="{divider}padding:12px 4px 10px 4px;">'
            f'<div class="{css_class} stat" style="font-family:{SERIF};'
            f"font-size:34px;line-height:38px;font-weight:bold;color:{color};"
            f'">{count}</div>'
            f'{label(text, MUTED, "muted", "margin-top:4px;")}</td>'
        )
    return row(
        '<table role="presentation" class="rule-ink" width="100%" cellpadding="0" '
        f'cellspacing="0" border="0" style="border-top:1px solid {INK};'
        f'border-bottom:1px solid {INK};"><tr>{"".join(cells)}</tr></table>',
        "24px 40px 0 40px",
    )


def _blank_page() -> str:
    return row(
        f'<div class="rule-ink" style="border-top:1px solid {INK};'
        f'border-bottom:1px solid {INK};padding:26px 0;text-align:center;">'
        f'<div class="ink" style="font-size:30px;line-height:36px;font-style:italic;'
        f'color:{INK};">Página en blanco.</div>'
        f'<div class="muted" style="font-size:15px;line-height:23px;color:{MUTED};'
        'margin-top:8px;">No hay nada vencido, para hoy ni para los próximos '
        "días.</div></div>",
        "26px 40px 0 40px",
    )


def _note(rescheduled: Sequence[RescheduledTask]) -> str:
    """ "Nota del día" listing recurring tasks moved in this run."""
    if not rescheduled:
        return ""
    items = []
    for item in rescheduled:
        title = html.escape(item.title)
        if item.url:
            title = (
                f'<a href="{attr(item.url)}" class="ink" '
                f'style="color:{INK};text-decoration:none;">{title}</a>'
            )
        items.append(
            f"<b>{title}</b> "
            f'<span class="muted" style="color:{MUTED};">'
            f"({html.escape(copy.moved_label(item))})</span>"
        )
    verb = "Se reprogramó" if len(items) == 1 else "Se reprogramaron"
    return row(
        f'<div class="note body" style="background-color:{NOTE_BG};'
        f"border-left:3px solid {ACCENT};padding:14px 18px;font-size:15px;"
        f'line-height:23px;color:{BODY};"><i>Nota del día.</i> {verb} '
        f"{copy.join_es(items)}.</div>",
        "30px 40px 0 40px",
    )


def _warnings(warnings: Sequence[str]) -> str:
    if not warnings:
        return ""
    items = "".join(f" {html.escape(w)}" for w in warnings)
    return row(
        f'<div class="note-red red" style="background-color:{NOTE_RED_BG};'
        f"border-left:3px solid {RED};padding:14px 18px;font-size:15px;"
        f'line-height:23px;color:{RED};"><i>Aviso.</i>{items}</div>',
        "16px 40px 0 40px",
    )
