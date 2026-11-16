"""
Builds the daily task digest (subject, HTML and plain text) in Spanish.

The HTML uses a "paper" look: a printed daily edition with serif type, warm
cream paper, ink colored text and a sienna accent. It is email safe: table
layout, inline styles, 600 px max width, no gradients or shadows. A small
<style> block only adds dark mode ("papel de noche") and mobile tweaks;
clients that drop it still get a complete, readable email.
"""

import html
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

from app.common.utils.dates import (
    DAYS,
    MONTHS,
    TaskDate,
    format_day_month,
    format_long_date,
    format_short_date,
    parse_notion_date,
    relative_label,
)

# --------------------------------------------------------------------- palette

PAGE = "#efe7da"  # around the sheet
PAPER = "#fbf7f0"
INK = "#3b2f2a"  # titles
BODY = "#4a3d36"  # running text
MUTED = "#8a7b6e"
RULE = "#e3d8c6"
DOT = "#d6c9b5"
ACCENT = "#a0522d"  # sienna
RED = "#b42318"
NOTE_BG = "#f3ebdd"
NOTE_RED_BG = "#fbe9e4"

SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

# Area -> (ink color on paper, ink color on dark paper). Printed, muted tones.
AREA_STYLES: Dict[str, tuple] = {
    "Hogar": ("#9a6b1f", "#e2b46a"),
    "Gatos": ("#a3466e", "#e79abb"),
    "Carro": ("#4a5a8a", "#a3b2e0"),
    "Finanzas": ("#3f7a4f", "#8fcf9f"),
    "Trabajo": ("#2f6f86", "#86c6dc"),
    "Salud": ("#a33a3a", "#ec9a9a"),
    "Personal": ("#6b5d52", "#c4b4a5"),
    "Estudio": ("#b0602a", "#eba476"),
}
DEFAULT_AREA_STYLE = (MUTED, "#a89a8b")

# Section key -> (title used in the plain text, printed heading, color, class)
SECTION_STYLES = {
    "overdue": ("Vencidas", "Pendientes de días anteriores", RED, "red"),
    "today": ("Hoy", "Para hoy", ACCENT, "accent"),
    "upcoming": ("Próximos días", "Lo que viene", MUTED, "muted"),
}
ROMAN = ["I", "II", "III"]

URL_PATTERN = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)")
TRAILING_PUNCTUATION = ".,;:!?)]}"


@dataclass
class DigestTask:
    titulo: str
    when: Optional[TaskDate]
    notas: str = ""
    area: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Sections:
    overdue: List[DigestTask] = field(default_factory=list)
    today: List[DigestTask] = field(default_factory=list)
    upcoming: List[DigestTask] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.overdue) + len(self.today) + len(self.upcoming)

    def items(self):
        return [
            ("overdue", self.overdue),
            ("today", self.today),
            ("upcoming", self.upcoming),
        ]


@dataclass
class EmailContent:
    subject: str
    html: str
    text: str
    sections: Sections = field(default_factory=Sections)


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _attr(value: str) -> str:
    return html.escape(value or "", quote=True)


def _join_es(parts: List[str]) -> str:
    """["a", "b", "c"] -> "a, b y c"."""
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " y " + parts[-1]


def _row(content: str, padding: str) -> str:
    return f'<tr><td class="px" style="padding:{padding};">{content}</td></tr>'


def _label(text: str, color: str, css_class: str, extra: str = "") -> str:
    """Small uppercase sans label, the "newspaper" section style."""
    return (
        f'<div class="{css_class}" style="font-family:{SANS};font-size:11px;'
        f"line-height:16px;letter-spacing:0.2em;text-transform:uppercase;"
        f'color:{color};{extra}">{text}</div>'
    )


class EmailAdapter:
    """Adapter to convert Notion tasks into the digest email."""

    TEMPLATE_PATH = (
        Path(__file__).parent.parent.parent / "resources" / "email_template.html"
    )

    def __init__(self, tz: Optional[ZoneInfo] = None, notion_tasks_url: str = ""):
        self.tz = tz or ZoneInfo("America/Bogota")
        self.notion_tasks_url = notion_tasks_url or ""
        self._template: Optional[str] = None

    # --------------------------------------------------------------- grouping

    def group_tasks(
        self, tasks: Iterable[Dict[str, Any]], today: date, upcoming_days: int
    ) -> Sections:
        """Splits tasks into overdue, today and upcoming (local dates)."""
        limit = today + timedelta(days=max(0, upcoming_days))
        sections = Sections()
        for raw in tasks:
            task = DigestTask(
                titulo=(raw.get("titulo") or "").strip() or "(sin título)",
                when=parse_notion_date(raw.get("fecha"), self.tz),
                notas=(raw.get("notas") or "").strip(),
                area=raw.get("area"),
                url=raw.get("url"),
            )
            day = task.when.day if task.when else today
            if day < today:
                sections.overdue.append(task)
            elif day == today:
                sections.today.append(task)
            elif day <= limit:
                sections.upcoming.append(task)
        for _, items in sections.items():
            items.sort(key=self._sort_key)
        return sections

    @staticmethod
    def _sort_key(task: DigestTask):
        when = task.when
        day = when.day if when else date.min
        # All-day tasks first, then by time of day.
        has_time = 1 if when and when.time else 0
        return (day, has_time, task.titulo.lower())

    # ---------------------------------------------------------------- summary

    @staticmethod
    def summary(sections: Sections) -> str:
        parts = []
        if sections.overdue:
            parts.append(_plural(len(sections.overdue), "vencida", "vencidas"))
        if sections.today:
            parts.append(f"{len(sections.today)} hoy")
        if sections.upcoming:
            parts.append(_plural(len(sections.upcoming), "próxima", "próximas"))
        return ", ".join(parts) if parts else "nada pendiente hoy"

    def subject(self, sections: Sections) -> str:
        return f"Tareas: {self.summary(sections)}"

    @staticmethod
    def greeting_line(sections: Sections) -> str:
        """One friendly sentence that sums up the day."""
        if not sections.total:
            return "No tienes nada pendiente. Disfruta el día."
        today_count = len(sections.today)
        first = (
            f"Hoy tienes {_plural(today_count, 'tarea', 'tareas')}"
            if today_count
            else "Hoy no tienes tareas nuevas"
        )
        extra = []
        if sections.overdue:
            extra.append(
                _plural(len(sections.overdue), "vencida", "vencidas") + " por cerrar"
            )
        if sections.upcoming:
            extra.append(f"{len(sections.upcoming)} en los próximos días")
        return _join_es([first] + extra) + "."

    # ------------------------------------------------------------- public API

    def build_digest(
        self,
        tasks: Iterable[Dict[str, Any]],
        today: date,
        upcoming_days: int = 3,
        rescheduled: Sequence[Any] = (),
        warnings: Sequence[str] = (),
    ) -> EmailContent:
        """Builds subject, HTML and plain text for the digest."""
        sections = self.group_tasks(tasks, today, upcoming_days)
        subject = self.subject(sections)
        html_body = self._render_html(sections, today, rescheduled, warnings)
        text_body = self._render_text(sections, today, rescheduled, warnings)
        return EmailContent(subject, html_body, text_body, sections)

    # ------------------------------------------------------------------- HTML

    def _load_template(self) -> str:
        if self._template is None:
            with open(self.TEMPLATE_PATH, "r", encoding="utf-8") as f:
                self._template = f.read()
        return self._template

    def _render_html(self, sections, today, rescheduled, warnings) -> str:
        parts = [self._masthead_html(today), self._dateline_html(sections, today)]
        if sections.total:
            parts.append(self._stats_html(sections))
            present = [(key, items) for key, items in sections.items() if items]
            for number, (key, items) in enumerate(present):
                parts.append(self._section_html(key, items, today, ROMAN[number]))
            preheader = self.summary(sections).capitalize()
        else:
            parts.append(self._empty_html())
            preheader = "Nada pendiente hoy. Disfruta el día."
        parts += [
            self._rescheduled_html(rescheduled),
            self._warnings_html(warnings),
            self._footer_html(),
        ]

        replacements = {
            "{{subject}}": html.escape(self.subject(sections)),
            "{{preheader}}": html.escape(preheader),
            "{{body}}": "".join(parts),
            "{{dark_area_css}}": self._dark_area_css(),
        }
        result = self._load_template()
        for key, value in replacements.items():
            result = result.replace(key, value)
        return result

    @staticmethod
    def _dark_area_css() -> str:
        return "\n".join(
            f"    .{EmailAdapter._area_class(name)} {{ color: {dark} !important; }}"
            for name, (_, dark) in AREA_STYLES.items()
        )

    @staticmethod
    def _area_class(area: str) -> str:
        ascii_name = (
            area.lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        return "tag-" + re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")

    # ---------------------------------------------------------------- header

    def _masthead_html(self, today: date) -> str:
        edition = today.timetuple().tm_yday
        return _row(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0"><tr>'
            f'<td valign="top">{_label("Tareas · Edición diaria", ACCENT, "accent")}</td>'
            f'<td valign="top" align="right">{_label(f"Nº {edition}", MUTED, "muted")}'
            "</td></tr></table>"
            f'<div class="rule-ink" style="border-top:2px solid {INK};margin-top:10px;">'
            "</div>"
            f'<div class="rule-ink" style="border-top:1px solid {INK};margin-top:3px;">'
            "</div>",
            "36px 40px 0 40px",
        )

    def _dateline_html(self, sections: Sections, today: date) -> str:
        weekday = DAYS[today.weekday()]
        rest = f"de {MONTHS[today.month - 1]} de {today.year}"
        lead = f"Buenos días. {self.greeting_line(sections)}"
        return _row(
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td valign="top" class="accent numeral" style="font-family:{SERIF};'
            f"font-size:86px;line-height:80px;font-weight:bold;color:{ACCENT};"
            f'padding-right:18px;">{today.day}</td>'
            '<td valign="top" style="padding-top:8px;">'
            f'<div class="ink weekday" style="font-size:28px;line-height:32px;'
            f'font-style:italic;color:{INK};">{weekday}</div>'
            f'<div class="muted" style="font-size:16px;line-height:22px;color:{MUTED};">'
            f"{rest}</div></td></tr></table>"
            f'<p class="body" style="font-size:17px;line-height:27px;margin:18px 0 0 0;'
            f'color:{BODY};">{html.escape(lead)}</p>',
            "22px 40px 0 40px",
        )

    def _stats_html(self, sections: Sections) -> str:
        """Newspaper style box: three big numerals split by thin rules."""
        overdue = len(sections.overdue)
        stats = [
            (
                overdue,
                "Vencidas",
                RED if overdue else MUTED,
                "red" if overdue else "muted",
            ),
            (len(sections.today), "Hoy", ACCENT, "accent"),
            (len(sections.upcoming), "Próximas", INK, "ink"),
        ]
        cells = []
        for index, (count, label, color, css_class) in enumerate(stats):
            divider = "" if index == 0 else f"border-left:1px solid {RULE};"
            cells.append(
                f'<td class="rule" width="33%" align="center" valign="top" '
                f'style="{divider}padding:12px 4px 10px 4px;">'
                f'<div class="{css_class} stat" style="font-family:{SERIF};'
                f"font-size:34px;line-height:38px;font-weight:bold;color:{color};"
                f'">{count}</div>'
                f'{_label(label, MUTED, "muted", "margin-top:4px;")}</td>'
            )
        return _row(
            '<table role="presentation" class="rule-ink" width="100%" cellpadding="0" '
            f'cellspacing="0" border="0" style="border-top:1px solid {INK};'
            f'border-bottom:1px solid {INK};"><tr>{"".join(cells)}</tr></table>',
            "24px 40px 0 40px",
        )

    # ---------------------------------------------------------------- sections

    def _section_html(
        self, key: str, items: List[DigestTask], today: date, number: str
    ) -> str:
        _, heading, color, css_class = SECTION_STYLES[key]
        if key == "upcoming":
            rows = self._upcoming_rows_html(items, today)
        else:
            rows = "".join(self._task_row_html(task, today, key) for task in items)
        title = _label(
            f"{number}. {heading}",
            color,
            f"{css_class} rule",
            f"border-bottom:1px solid {RULE};padding-bottom:8px;",
        )
        return _row(
            f"{title}"
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin-top:4px;">{rows}</table>',
            "30px 40px 0 40px",
        )

    def _upcoming_rows_html(self, items: List[DigestTask], today: date) -> str:
        """Upcoming tasks with the day in a left column, shown once per day."""
        rows = []
        previous = None
        for task in items:
            day = task.when.day if task.when else today
            label = ""
            if day != previous:
                label = (
                    "mañana" if (day - today).days == 1 else format_short_date(day)[:-4]
                )
            previous = day
            rows.append(self._task_row_html(task, today, "upcoming", day_label=label))
        return "".join(rows)

    def _task_row_html(
        self, task: DigestTask, today: date, key: str, day_label: Optional[str] = None
    ) -> str:
        overdue = key == "overdue"
        box_color, box_class = (RED, "box-red") if overdue else (ACCENT, "box")
        box = (
            f'<span class="{box_class}" style="display:inline-block;width:11px;'
            f'height:11px;border:1.5px solid {box_color};border-radius:2px;"></span>'
        )
        title = html.escape(task.titulo)
        if task.url:
            href = _attr(task.url)
            box = f'<a href="{href}" style="text-decoration:none;">{box}</a>'
            title = (
                f'<a href="{href}" class="ink" style="color:{INK};'
                f'text-decoration:none;">{title}</a>'
            )

        details = []
        if task.area:
            details.append(self._area_html(task.area))
        if task.notas:
            details.append(self._notes_html(task.notas))
        details_html = (
            f'<div class="muted" style="font-size:14px;line-height:21px;color:{MUTED};'
            f'margin-top:4px;word-break:break-word;">{" · ".join(details)}</div>'
            if details
            else ""
        )

        when = self._when_html(task, today, key)
        border = f"border-bottom:1px dotted {DOT};"
        day_cell = ""
        if day_label is not None:
            day_cell = (
                f'<td class="dot muted" width="62" valign="top" style="width:62px;'
                f"{border}padding:14px 0 13px 0;font-size:14px;line-height:23px;"
                f'font-style:italic;color:{MUTED};">{html.escape(day_label)}</td>'
            )
        # Without a date or time on the right, the title takes that space too.
        when_cell = (
            f'<td class="dot" align="right" valign="top" style="{border}'
            f'padding:16px 0 13px 12px;white-space:nowrap;">{when}</td>'
            if when
            else ""
        )
        colspan = "" if when else ' colspan="2"'
        return (
            f"<tr>{day_cell}"
            f'<td class="dot" width="24" valign="top" style="width:24px;{border}'
            f'padding:19px 0 13px 0;line-height:11px;">{box}</td>'
            f'<td class="dot" valign="top"{colspan} style="{border}'
            'padding:14px 0 13px 0;">'
            f'<div class="ink task" style="font-size:18px;line-height:24px;color:{INK};">'
            f"{title}</div>{details_html}</td>{when_cell}</tr>"
        )

    def _when_html(self, task: DigestTask, today: date, key: str) -> str:
        """Right column: how late an overdue task is, or the time of day."""
        if key == "overdue":
            text, color, css_class = self._when_label(task, today), RED, "red"
        elif task.when and task.when.time:
            text, color, css_class = task.when.time, ACCENT, "accent"
        else:
            return ""
        return (
            f'<span class="{css_class}" style="font-size:14px;line-height:20px;'
            f'font-style:italic;color:{color};">{html.escape(text)}</span>'
        )

    def _area_html(self, area: str) -> str:
        color, _ = AREA_STYLES.get(area, DEFAULT_AREA_STYLE)
        return (
            f'<i class="{self._area_class(area)}" style="color:{color};">'
            f"{html.escape(area.lower())}</i>"
        )

    @staticmethod
    def _when_label(task: DigestTask, today: date) -> str:
        if not task.when:
            return "sin fecha"
        label = relative_label(task.when.day, today)
        return f"{label}, {task.when.time}" if task.when.time else label

    def _notes_html(self, notes: str) -> str:
        """Escapes notes, turns URLs into links and keeps line breaks."""
        parts = []
        last = 0
        for match in URL_PATTERN.finditer(notes):
            url = match.group(1)
            trimmed = url.rstrip(TRAILING_PUNCTUATION)
            end = match.start() + len(trimmed)
            parts.append(html.escape(notes[last : match.start()]))
            href = trimmed if trimmed.startswith("http") else f"https://{trimmed}"
            parts.append(
                f'<a href="{_attr(href)}" class="accent" '
                f'style="color:{ACCENT};text-decoration:underline;">'
                f"{html.escape(trimmed)}</a>"
            )
            last = end
        parts.append(html.escape(notes[last:]))
        return "".join(parts).replace("\n", "<br>")

    @staticmethod
    def _empty_html() -> str:
        return _row(
            f'<div class="rule-ink" style="border-top:1px solid {INK};'
            f'border-bottom:1px solid {INK};padding:26px 0;text-align:center;">'
            f'<div class="ink" style="font-size:30px;line-height:36px;font-style:italic;'
            f'color:{INK};">Página en blanco.</div>'
            f'<div class="muted" style="font-size:15px;line-height:23px;color:{MUTED};'
            'margin-top:8px;">No hay nada vencido, para hoy ni para los próximos '
            "días.</div></div>",
            "26px 40px 0 40px",
        )

    # ------------------------------------------------------------ notes, footer

    def _rescheduled_html(self, rescheduled: Sequence[Any]) -> str:
        """ "Nota del día" listing recurring tasks moved in this run."""
        if not rescheduled:
            return ""
        items = []
        for item in rescheduled:
            title = html.escape(item.titulo)
            if item.url:
                title = (
                    f'<a href="{_attr(item.url)}" class="ink" '
                    f'style="color:{INK};text-decoration:none;">{title}</a>'
                )
            items.append(
                f"<b>{title}</b> "
                f'<span class="muted" style="color:{MUTED};">'
                f"({html.escape(self._moved_label(item))})</span>"
            )
        verb = "Se reprogramó" if len(items) == 1 else "Se reprogramaron"
        return _row(
            f'<div class="note body" style="background-color:{NOTE_BG};'
            f"border-left:3px solid {ACCENT};padding:14px 18px;font-size:15px;"
            f'line-height:23px;color:{BODY};"><i>Nota del día.</i> {verb} '
            f"{_join_es(items)}.</div>",
            "30px 40px 0 40px",
        )

    @staticmethod
    def _moved_label(item: Any) -> str:
        """ "del 21 nov al 21 dic", or "al 21 dic" when the old date is unknown."""
        new = format_day_month(item.nueva_fecha)
        old = getattr(item, "fecha_anterior", None)
        return f"del {format_day_month(old)} al {new}" if old else f"al {new}"

    @staticmethod
    def _warnings_html(warnings: Sequence[str]) -> str:
        if not warnings:
            return ""
        items = "".join(f" {html.escape(w)}" for w in warnings)
        return _row(
            f'<div class="note-red red" style="background-color:{NOTE_RED_BG};'
            f"border-left:3px solid {RED};padding:14px 18px;font-size:15px;"
            f'line-height:23px;color:{RED};"><i>Aviso.</i>{items}</div>',
            "16px 40px 0 40px",
        )

    def _footer_html(self) -> str:
        link = ""
        if self.notion_tasks_url:
            link = (
                f'<a href="{_attr(self.notion_tasks_url)}" class="accent" '
                f'style="font-family:{SANS};font-size:12px;letter-spacing:0.15em;'
                f"text-transform:uppercase;color:{ACCENT};text-decoration:none;"
                'font-weight:700;white-space:nowrap;">Abrir Tareas en Notion &rarr;</a>'
            )
        return _row(
            f'<div class="rule-ink" style="border-top:1px solid {INK};"></div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0" style="margin-top:12px;"><tr>'
            f'<td class="muted" style="font-size:13px;line-height:19px;font-style:italic;'
            f'color:{MUTED};padding-right:12px;">Chulea una tarea para quitarla de esta '
            "página.</td>"
            f'<td align="right" valign="top">{link}</td></tr></table>',
            "32px 40px 36px 40px",
        )

    # ------------------------------------------------------------- plain text

    def _render_text(self, sections, today, rescheduled, warnings) -> str:
        lines = [self.subject(sections), format_long_date(today), ""]
        if not sections.total:
            lines += ["Nada pendiente hoy.", ""]
        for key, items in sections.items():
            if items:
                lines += self._section_text(key, items, today)
        if rescheduled:
            lines.append(f"REPROGRAMADAS HOY ({len(rescheduled)})")
            lines += [f"- {r.titulo}: {self._moved_label(r)}" for r in rescheduled]
            lines.append("")
        for warning in warnings:
            lines += [f"Aviso: {warning}", ""]
        if self.notion_tasks_url:
            lines.append(f"Abrir Tareas en Notion: {self.notion_tasks_url}")
        return "\n".join(lines).rstrip() + "\n"

    def _section_text(self, key: str, items: List[DigestTask], today: date) -> list:
        lines = [f"{SECTION_STYLES[key][0].upper()} ({len(items)})"]
        for task in items:
            area = f" [{task.area}]" if task.area else ""
            lines.append(f"- {task.titulo}{area} ({self._when_label(task, today)})")
            lines += [f"    {n.strip()}" for n in task.notas.splitlines() if n.strip()]
            if task.url:
                lines.append(f"    {task.url}")
        lines.append("")
        return lines
