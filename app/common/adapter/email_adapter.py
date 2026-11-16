"""
Builds the daily task digest (subject, HTML and plain text) in Spanish.

The HTML is email safe: table layout, inline styles, 600 px max width, no
gradients or shadows. A small <style> block only adds dark mode and mobile
tweaks; clients that drop it still get a complete, readable email.
"""

import html
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

from app.common.utils.dates import (
    TaskDate,
    format_day_month,
    format_long_date,
    format_short_date,
    parse_notion_date,
    relative_label,
)

# Area -> (light background, light text, dark background, dark text)
AREA_STYLES: Dict[str, tuple] = {
    "Hogar": ("#fef3c7", "#92400e", "#3b2f12", "#fcd34d"),
    "Gatos": ("#fce7f3", "#9d174d", "#3d1a2c", "#f9a8d4"),
    "Carro": ("#e0e7ff", "#3730a3", "#23264a", "#a5b4fc"),
    "Finanzas": ("#dcfce7", "#166534", "#15301f", "#86efac"),
    "Trabajo": ("#e0f2fe", "#075985", "#132b3a", "#7dd3fc"),
    "Salud": ("#fee2e2", "#991b1b", "#3b1a1a", "#fca5a5"),
    "Personal": ("#ccfbf1", "#115e59", "#123330", "#5eead4"),
    "Estudio": ("#ffedd5", "#9a3412", "#3b2414", "#fdba74"),
}
DEFAULT_AREA_STYLE = ("#f3f4f6", "#374151", "#2a2f35", "#d1d5db")

# Color tones: (accent, soft background, text on soft background).
# Each tone has matching dark mode classes in email_template.html.
TONES = {
    "red": ("#ef4444", "#fef2f2", "#b91c1c"),
    "blue": ("#3b82f6", "#eff6ff", "#1d4ed8"),
    "slate": ("#cbd5e1", "#f1f5f9", "#475569"),
    "green": ("#22c55e", "#f0fdf4", "#15803d"),
}

# Section key -> (title, tone)
SECTION_STYLES = {
    "overdue": ("Vencidas", "red"),
    "today": ("Hoy", "blue"),
    "upcoming": ("Próximos días", "slate"),
}

# Small icons: emoji render in Gmail, Apple Mail and Outlook without CSS.
AREA_EMOJI = {
    "Hogar": "🏠",
    "Gatos": "🐱",
    "Carro": "🚗",
    "Finanzas": "💰",
    "Trabajo": "💼",
    "Salud": "🩺",
    "Personal": "✨",
    "Estudio": "📚",
}
SECTION_EMOJI = {"overdue": "⏰", "today": "📌", "upcoming": "🗓️"}

# Up to this many upcoming days get their own cell in the header agenda;
# a longer window is shown as a single "Próximas" cell.
MAX_STRIP_DAYS = 4

INK = "#1e293b"
MUTED = "#64748b"
FAINT = "#94a3b8"
LINE = "#edf0f4"

URL_PATTERN = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)")
TRAILING_PUNCTUATION = ".,;:!?)]}"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


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
        html_body = self._render_html(
            sections, today, rescheduled, warnings, upcoming_days
        )
        text_body = self._render_text(sections, today, rescheduled, warnings)
        return EmailContent(subject, html_body, text_body, sections)

    # ------------------------------------------------------------------- HTML

    def _load_template(self) -> str:
        if self._template is None:
            with open(self.TEMPLATE_PATH, "r", encoding="utf-8") as f:
                self._template = f.read()
        return self._template

    def _render_html(
        self, sections, today, rescheduled, warnings, upcoming_days=3
    ) -> str:
        if sections.total:
            body = "".join(
                self._section_html(key, items, today)
                for key, items in sections.items()
                if items
            )
            preheader = self.summary(sections).capitalize()
        else:
            body = self._empty_html()
            preheader = "Nada pendiente hoy. Disfruta el día."
        body += self._rescheduled_html(rescheduled) + self._warnings_html(warnings)

        replacements = {
            "{{subject}}": html.escape(self.subject(sections)),
            "{{preheader}}": html.escape(preheader),
            "{{header}}": self._header_html(sections, today, upcoming_days),
            "{{counters}}": "",
            "{{sections}}": body,
            "{{footer}}": self._footer_html(),
            "{{dark_area_css}}": self._dark_area_css(),
        }
        result = self._load_template()
        for key, value in replacements.items():
            result = result.replace(key, value)
        return result

    @staticmethod
    def _dark_area_css() -> str:
        rules = []
        for name, (_, _, dark_bg, dark_fg) in AREA_STYLES.items():
            css_class = EmailAdapter._area_class(name)
            rules.append(
                f"    .{css_class} {{ background-color: {dark_bg} !important; "
                f"color: {dark_fg} !important; }}"
            )
        return "\n".join(rules)

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

    @staticmethod
    def _pill(text: str, tone: str) -> str:
        _, soft, fg = TONES[tone]
        return (
            f'<span class="soft-{tone} fg-{tone}" style="display:inline-block;'
            f"background-color:{soft};color:{fg};font-size:12px;line-height:18px;"
            f'font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap;">'
            f"{html.escape(text)}</span>"
        )

    # ----------------------------------------------------------------- header

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
        if not extra:
            return f"{first}."
        if len(extra) == 1:
            return f"{first} y {extra[0]}."
        return f"{first}, {extra[0]} y {extra[1]}."

    def _header_html(self, sections: Sections, today: date, upcoming_days: int) -> str:
        strip = self._agenda_strip_html(sections, today, upcoming_days)
        return (
            '<tr><td class="hero px" style="background-color:#eef2ff;'
            'border-radius:17px 17px 0 0;padding:30px 32px 28px 32px;">'
            '<div class="hero-eyebrow" style="font-size:12px;line-height:16px;'
            "font-weight:700;letter-spacing:0.12em;text-transform:uppercase;"
            'color:#6366f1;">Buenos días</div>'
            '<div class="h1 hero-title" style="font-size:27px;line-height:33px;'
            'font-weight:800;letter-spacing:-0.01em;color:#1e1b4b;margin-top:6px;">'
            f"{html.escape(format_long_date(today))}</div>"
            '<div class="hero-text" style="font-size:15px;line-height:22px;'
            'color:#4b5563;margin-top:8px;">'
            f"{html.escape(self.greeting_line(sections))}</div>"
            f"{strip}</td></tr>"
        )

    def _agenda_strip_html(
        self, sections: Sections, today: date, upcoming_days: int
    ) -> str:
        """Row of small cells: Vencidas, Hoy and each upcoming day with a count."""
        if not sections.total:
            return ""
        # Cell kinds: "red" (overdue > 0), "accent" (today) and "plain".
        cells = [
            ("Vencidas", len(sections.overdue), "red" if sections.overdue else "plain"),
            ("Hoy", len(sections.today), "accent"),
        ]
        if upcoming_days <= MAX_STRIP_DAYS:
            for offset in range(1, upcoming_days + 1):
                day = today + timedelta(days=offset)
                count = sum(
                    1 for t in sections.upcoming if t.when and t.when.day == day
                )
                label = (
                    "Mañana"
                    if offset == 1
                    else f"{format_short_date(day)[:3].capitalize()} {day.day}"
                )
                cells.append((label, count, "plain"))
        else:
            cells.append(("Próximas", len(sections.upcoming), "plain"))

        styles = {
            # kind: (cell class, background, border, label color, number color)
            "red": ("cell-red", "#fee2e2", "#fecaca", "#b91c1c", "#b91c1c"),
            "accent": ("cell-accent", "#4f46e5", "#4f46e5", "#e0e7ff", "#ffffff"),
            "plain": ("cell", "#ffffff", "#e0e7ff", "#6b7280", "#1e1b4b"),
        }
        tds = []
        cell_width = f"{100 // len(cells)}%"
        for index, (label, count, kind) in enumerate(cells):
            cls, bg, border, label_color, number_color = styles[kind]
            if kind == "plain" and not count:
                number_color = "#a5b4fc"
            gap = (
                ""
                if index == 0
                else '<td width="6" style="width:6px;font-size:0;">&nbsp;</td>'
            )
            tds.append(
                f'{gap}<td class="{cls}" align="center" valign="top" '
                f'width="{cell_width}" style="width:{cell_width};'
                f"background-color:{bg};border:1px solid {border};"
                'border-radius:12px;padding:10px 4px 11px 4px;">'
                f'<div class="{cls}-label" style="font-size:11px;line-height:14px;'
                f'font-weight:700;color:{label_color};white-space:nowrap;">'
                f"{html.escape(label)}</div>"
                f'<div class="count {cls}-num" style="font-size:24px;line-height:28px;'
                f'font-weight:800;color:{number_color};margin-top:3px;">{count}</div></td>'
            )
        return (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin-top:22px;"><tr>{"".join(tds)}</tr></table>'
        )

    # --------------------------------------------------------------- sections

    def _section_html(self, key: str, items: List[DigestTask], today: date) -> str:
        title, tone = SECTION_STYLES[key]
        accent, _, fg = TONES[tone]
        if key == "upcoming":
            rows = self._grouped_rows_html(items, today)
        else:
            rows = "".join(
                self._task_html(task, today, key, index == len(items) - 1)
                for index, task in enumerate(items)
            )
        title_color = fg if tone != "slate" else "#334155"
        title_cls = f"fg-{tone}" if tone != "slate" else "txt"
        return (
            '<tr><td class="px" style="padding:28px 32px 0 32px;">'
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            'style="margin-bottom:10px;"><tr>'
            '<td valign="middle" style="padding-right:8px;font-size:15px;'
            f'line-height:18px;">{SECTION_EMOJI[key]}</td>'
            f'<td valign="middle" class="{title_cls}" style="font-size:15px;'
            f'line-height:18px;font-weight:800;color:{title_color};padding-right:8px;">'
            f"{title}</td>"
            f'<td valign="middle">{self._pill(str(len(items)), tone)}</td>'
            "</tr></table>"
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" class="box rail-{tone}" style="background-color:#ffffff;'
            f"border:1px solid {LINE};border-left:4px solid {accent};"
            f'border-radius:12px;">{rows}</table></td></tr>'
        )

    def _grouped_rows_html(self, items: List[DigestTask], today: date) -> str:
        """Upcoming tasks grouped under a small header per day."""
        groups: Dict[date, List[DigestTask]] = {}
        for task in items:
            groups.setdefault(task.when.day if task.when else today, []).append(task)
        rows = []
        for group_index, (day, tasks) in enumerate(groups.items()):
            border = "" if group_index == 0 else f"border-top:1px solid {LINE};"
            label = format_long_date(day)
            if (day - today).days == 1:
                label = f"Mañana · {label}"
            rows.append(
                f'<tr><td class="line txt-muted" style="{border}'
                "padding:12px 16px 0 16px;font-size:11px;line-height:14px;"
                "font-weight:800;letter-spacing:0.08em;text-transform:uppercase;"
                f'color:{MUTED};">{html.escape(label)}</td></tr>'
            )
            rows += [
                self._task_html(task, today, "upcoming", index == len(tasks) - 1)
                for index, task in enumerate(tasks)
            ]
        return "".join(rows)

    def _task_html(self, task: DigestTask, today: date, key: str, last: bool) -> str:
        title = html.escape(task.titulo)
        ring = (
            '<span class="ring" style="display:inline-block;width:14px;height:14px;'
            'border:2px solid #cbd5e1;border-radius:9px;"></span>'
        )
        if task.url:
            href = _attr(task.url)
            title = (
                f'<a href="{href}" class="txt" style="color:{INK};'
                f'text-decoration:none;">{title}</a>'
            )
            ring = f'<a href="{href}" style="text-decoration:none;">{ring}</a>'

        meta = []
        when = self._when_pill(task, today, key)
        if when:
            meta.append(when)
        if task.area:
            meta.append(self._area_tag_html(task.area))
        meta_html = (
            f'<div style="margin-top:6px;line-height:22px;">{"&nbsp;".join(meta)}</div>'
            if meta
            else ""
        )
        notes = ""
        if task.notas:
            notes = (
                f'<div class="txt-muted" style="font-size:13px;line-height:20px;'
                f'color:{MUTED};margin-top:8px;word-break:break-word;">'
                f"{self._notes_html(task.notas)}</div>"
            )
        border = "" if last else f"border-bottom:1px solid {LINE};"
        return (
            f'<tr><td class="line" style="padding:12px 16px 13px 14px;{border}">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0"><tr>'
            '<td valign="top" width="26" style="width:26px;padding-top:2px;">'
            f"{ring}</td>"
            '<td valign="top">'
            f'<div class="txt" style="font-size:15px;line-height:21px;font-weight:700;'
            f'color:{INK};">{title}</div>'
            f"{meta_html}{notes}</td></tr></table></td></tr>"
        )

    def _when_pill(self, task: DigestTask, today: date, key: str) -> str:
        if key in ("upcoming", "today"):
            # The day is already in the section or group header; only the time
            # adds information.
            if task.when and task.when.time:
                return self._pill(task.when.time, "blue" if key == "today" else "slate")
            return ""
        return self._pill(self._when_label(task, today), "red")

    def _area_tag_html(self, area: str) -> str:
        bg, fg, _, _ = AREA_STYLES.get(area, DEFAULT_AREA_STYLE)
        emoji = AREA_EMOJI.get(area)
        label = f"{emoji} {html.escape(area)}" if emoji else html.escape(area)
        return (
            f'<span class="{self._area_class(area)}" style="display:inline-block;'
            f"background-color:{bg};color:{fg};font-size:12px;line-height:18px;"
            f'font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap;">'
            f"{label}</span>"
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
                f'<a href="{_attr(href)}" class="link" '
                f'style="color:#2563eb;text-decoration:underline;">'
                f"{html.escape(trimmed)}</a>"
            )
            last = end
        parts.append(html.escape(notes[last:]))
        return "".join(parts).replace("\n", "<br>")

    @staticmethod
    def _empty_html() -> str:
        accent, soft, fg = TONES["green"]
        return (
            '<tr><td class="px" style="padding:22px 32px 4px 32px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0"><tr><td class="soft-green" style="background-color:{soft};'
            f'border:1px solid #bbf7d0;border-radius:14px;padding:22px 20px;">'
            f'<div class="fg-green" style="font-size:17px;line-height:24px;font-weight:800;'
            f'color:{fg};">Nada pendiente hoy</div>'
            f'<div class="txt-muted" style="font-size:14px;line-height:21px;color:{MUTED};'
            'margin-top:4px;">No hay tareas vencidas, para hoy ni para los próximos '
            "días.</div></td></tr></table></td></tr>"
        )

    def _rescheduled_html(self, rescheduled: Sequence[Any]) -> str:
        """Green box at the end listing recurring tasks moved in this run."""
        if not rescheduled:
            return ""
        _, soft, fg = TONES["green"]
        lines = []
        for item in rescheduled:
            title = html.escape(item.titulo)
            if item.url:
                title = (
                    f'<a href="{_attr(item.url)}" class="txt" '
                    f'style="color:{INK};text-decoration:none;">{title}</a>'
                )
            lines.append(
                f'<div class="txt" style="margin-top:6px;color:{INK};">'
                f"<strong>{title}</strong>: "
                f'<span class="txt-muted" style="color:{MUTED};">'
                f"{html.escape(self._moved_label(item))}</span></div>"
            )
        return (
            '<tr><td class="px" style="padding:26px 32px 0 32px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0"><tr><td class="soft-green" style="background-color:{soft};'
            "border:1px solid #bbf7d0;border-radius:12px;padding:14px 16px;"
            'font-size:14px;line-height:20px;">'
            f'<div class="fg-green" style="font-size:12px;line-height:16px;font-weight:800;'
            f'letter-spacing:0.09em;text-transform:uppercase;color:{fg};">'
            f"🔁 Reprogramadas hoy ({len(rescheduled)})</div>"
            f'{"".join(lines)}</td></tr></table></td></tr>'
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
        _, soft, fg = TONES["red"]
        items = "".join(
            f'<div style="margin-top:4px;">{html.escape(w)}</div>' for w in warnings
        )
        return (
            '<tr><td class="px" style="padding:18px 32px 0 32px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0"><tr><td class="soft-red fg-red" style="background-color:{soft};'
            f"border:1px solid #fecaca;border-radius:12px;padding:12px 16px;"
            f'font-size:13px;line-height:19px;color:{fg};">'
            f"<strong>Atención</strong>{items}</td></tr></table></td></tr>"
        )

    def _footer_html(self) -> str:
        button = ""
        if self.notion_tasks_url:
            button = (
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
                '<tr><td class="btn" style="background-color:#4f46e5;border-radius:10px;">'
                f'<a href="{_attr(self.notion_tasks_url)}" class="btn-txt" '
                'style="display:inline-block;padding:12px 20px;font-size:14px;'
                'line-height:18px;font-weight:700;color:#ffffff;text-decoration:none;">'
                "Abrir Tareas en Notion &rarr;</a></td></tr></table>"
            )
        return (
            '<tr><td class="px" style="padding:30px 32px 30px 32px;">'
            f"{button}"
            f'<div class="line txt-faint" style="border-top:1px solid {LINE};'
            f"margin-top:{'24px' if button else '0'};padding-top:16px;font-size:12px;"
            f'line-height:18px;color:{FAINT};">Resumen diario de tu base Tareas en '
            "Notion. Chulea una tarea para quitarla de aquí.</div></td></tr>"
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
