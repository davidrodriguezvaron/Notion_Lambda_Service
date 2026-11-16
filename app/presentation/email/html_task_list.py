"""HTML for one agenda section: its numbered heading and the task rows."""

import html
from datetime import date
from typing import List, Optional

from app.domain.agenda import AgendaItem
from app.presentation.email import copy
from app.presentation.email.html_primitives import attr, label, row
from app.presentation.email.linkify import notes_to_html
from app.presentation.email.spanish_dates import format_weekday_day
from app.presentation.email.theme import (
    ACCENT,
    DOT,
    INK,
    MUTED,
    RED,
    RULE,
    SECTION_STYLES,
    area_class,
    area_color,
)

ROW_BORDER = f"border-bottom:1px dotted {DOT};"


def section_html(key: str, items: List[AgendaItem], today: date, number: str) -> str:
    _, heading, color, css_class = SECTION_STYLES[key]
    if key == "upcoming":
        rows = _upcoming_rows(items, today)
    else:
        rows = "".join(_task_row(item, today, key) for item in items)
    title = label(
        f"{number}. {heading}",
        color,
        f"{css_class} rule",
        f"border-bottom:1px solid {RULE};padding-bottom:8px;",
    )
    return row(
        f"{title}"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="margin-top:4px;">{rows}</table>',
        "30px 40px 0 40px",
    )


def _upcoming_rows(items: List[AgendaItem], today: date) -> str:
    """Upcoming tasks with the day in a left column, shown once per day."""
    rows = []
    previous = None
    for item in items:
        day = item.day or today
        day_label = ""
        if day != previous:
            day_label = "mañana" if (day - today).days == 1 else format_weekday_day(day)
        previous = day
        rows.append(_task_row(item, today, "upcoming", day_label))
    return "".join(rows)


def _task_row(
    item: AgendaItem, today: date, key: str, day_label: Optional[str] = None
) -> str:
    box, title = _checkbox_and_title(item, overdue=key == "overdue")
    when = _when(item, today, key)
    day_cell = ""
    if day_label is not None:
        day_cell = (
            f'<td class="dot muted" width="62" valign="top" style="width:62px;'
            f"{ROW_BORDER}padding:14px 0 13px 0;font-size:14px;line-height:23px;"
            f'font-style:italic;color:{MUTED};">{html.escape(day_label)}</td>'
        )
    # Without a date or time on the right, the title takes that space too.
    when_cell = (
        f'<td class="dot" align="right" valign="top" style="{ROW_BORDER}'
        f'padding:16px 0 13px 12px;white-space:nowrap;">{when}</td>'
        if when
        else ""
    )
    colspan = "" if when else ' colspan="2"'
    return (
        f"<tr>{day_cell}"
        f'<td class="dot" width="24" valign="top" style="width:24px;{ROW_BORDER}'
        f'padding:19px 0 13px 0;line-height:11px;">{box}</td>'
        f'<td class="dot" valign="top"{colspan} style="{ROW_BORDER}'
        'padding:14px 0 13px 0;">'
        f'<div class="ink task" style="font-size:18px;line-height:24px;color:{INK};">'
        f"{title}</div>{_details(item)}</td>{when_cell}</tr>"
    )


def _checkbox_and_title(item: AgendaItem, overdue: bool):
    """A printed checkbox and the title, both linked to the Notion page."""
    box_color, box_class = (RED, "box-red") if overdue else (ACCENT, "box")
    box = (
        f'<span class="{box_class}" style="display:inline-block;width:11px;'
        f'height:11px;border:1.5px solid {box_color};border-radius:2px;"></span>'
    )
    title = html.escape(copy.title_of(item))
    url = item.task.url
    if url:
        href = attr(url)
        box = f'<a href="{href}" style="text-decoration:none;">{box}</a>'
        title = (
            f'<a href="{href}" class="ink" style="color:{INK};'
            f'text-decoration:none;">{title}</a>'
        )
    return box, title


def _details(item: AgendaItem) -> str:
    """Area in italic ink and the notes, under the title."""
    parts = []
    if item.task.area:
        area = item.task.area
        parts.append(
            f'<i class="{area_class(area)}" style="color:{area_color(area)};">'
            f"{html.escape(area.lower())}</i>"
        )
    if item.task.notes:
        parts.append(notes_to_html(item.task.notes, ACCENT, "accent"))
    if not parts:
        return ""
    return (
        f'<div class="muted" style="font-size:14px;line-height:21px;color:{MUTED};'
        f'margin-top:4px;word-break:break-word;">{" · ".join(parts)}</div>'
    )


def _when(item: AgendaItem, today: date, key: str) -> str:
    """Right column: how late an overdue task is, or the time of day."""
    if key == "overdue":
        text, color, css_class = copy.when_label(item, today), RED, "red"
    elif item.time:
        text, color, css_class = item.time, ACCENT, "accent"
    else:
        return ""
    return (
        f'<span class="{css_class}" style="font-size:14px;line-height:20px;'
        f'font-style:italic;color:{color};">{html.escape(text)}</span>'
    )
