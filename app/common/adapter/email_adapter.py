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

# Section key -> (title, rail color, rail class, title color, title class)
SECTION_STYLES = {
    "overdue": ("Vencidas", "#f2a7a7", "rail-red", "#b42318", "txt-alert"),
    "today": ("Hoy", "#2f6feb", "rail-blue", "#1d4ed8", "txt-blue"),
    "upcoming": ("Próximos días", "#d1d5db", "rail-gray", "#4b5563", "txt-muted"),
}

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

        replacements = {
            "{{subject}}": html.escape(self.subject(sections)),
            "{{preheader}}": html.escape(preheader),
            "{{date_label}}": html.escape(format_long_date(today)),
            "{{counters}}": self._counters_html(sections),
            "{{sections}}": body + self._rescheduled_html(rescheduled),
            "{{footer}}": self._footer_html(warnings),
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

    def _counters_html(self, sections: Sections) -> str:
        if not sections.total:
            return ""
        cards = [
            ("Vencidas", len(sections.overdue), bool(sections.overdue)),
            ("Hoy", len(sections.today), False),
            ("Próximas", len(sections.upcoming), False),
        ]
        cells = []
        for index, (label, count, alert) in enumerate(cards):
            bg, fg, card_cls, txt_cls = (
                ("#fdecec", "#b42318", "card-alert", "txt-alert")
                if alert
                else ("#f3f4f6", "#111827", "card-neutral", "txt")
            )
            label_color = "#b42318" if alert else "#6b7280"
            label_cls = "txt-alert" if alert else "txt-muted"
            gap = (
                ""
                if index == 0
                else '<td width="8" style="width:8px;font-size:0;">&nbsp;</td>'
            )
            cells.append(
                f'{gap}<td class="{card_cls}" width="33%" valign="top" '
                f'style="background-color:{bg};border-radius:8px;padding:10px 12px;">'
                f'<div class="{txt_cls} count" style="font-size:24px;line-height:28px;'
                f'font-weight:700;color:{fg};">{count}</div>'
                f'<div class="{label_cls}" style="font-size:12px;line-height:16px;'
                f'color:{label_color};margin-top:2px;">{label}</div></td>'
            )
        return (
            '<tr><td class="px" style="padding:16px 28px 4px 28px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0"><tr>{"".join(cells)}</tr></table></td></tr>'
        )

    def _section_html(self, key: str, items: List[DigestTask], today: date) -> str:
        title, rail, rail_cls, title_color, title_cls = SECTION_STYLES[key]
        rows = []
        for index, task in enumerate(items):
            last = index == len(items) - 1
            rows.append(self._task_html(task, today, key, last))
        return (
            '<tr><td class="px" style="padding:20px 28px 0 28px;">'
            f'<div class="{title_cls}" style="font-size:13px;line-height:18px;'
            f'font-weight:700;color:{title_color};margin:0 0 8px 0;font-family:{FONT};">'
            f'{title} <span style="font-weight:400;">({len(items)})</span></div>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" class="{rail_cls}" style="border-left:3px solid {rail};">'
            f'{"".join(rows)}</table></td></tr>'
        )

    def _task_html(self, task: DigestTask, today: date, key: str, last: bool) -> str:
        title = html.escape(task.titulo)
        if task.url:
            title = (
                f'<a href="{_attr(task.url)}" class="txt" '
                'style="color:#111827;text-decoration:none;font-weight:700;">'
                f"{title}</a>"
            )
        when_label = html.escape(self._when_label(task, today))
        when_color, when_cls = (
            ("#b42318", "txt-alert") if key == "overdue" else ("#6b7280", "txt-muted")
        )
        meta = [
            f'<span class="{when_cls}" style="color:{when_color};">{when_label}</span>'
        ]
        if task.area:
            meta.insert(0, self._area_tag_html(task.area))
        notes = ""
        if task.notas:
            notes = (
                '<div class="txt-muted" style="font-size:13px;line-height:19px;'
                f'color:#6b7280;margin-top:6px;word-break:break-word;">'
                f"{self._notes_html(task.notas)}</div>"
            )
        border = "" if last else "border-bottom:1px solid #eef0f2;"
        return (
            f'<tr><td class="line" style="padding:10px 0 10px 14px;{border}">'
            f'<div class="txt" style="font-size:15px;line-height:21px;font-weight:700;'
            f'color:#111827;">{title}</div>'
            f'<div style="font-size:12px;line-height:18px;margin-top:3px;">'
            f'{"&nbsp;&nbsp;".join(meta)}</div>{notes}</td></tr>'
        )

    def _area_tag_html(self, area: str) -> str:
        bg, fg, _, _ = AREA_STYLES.get(area, DEFAULT_AREA_STYLE)
        return (
            f'<span class="{self._area_class(area)}" style="display:inline-block;'
            f"background-color:{bg};color:{fg};font-size:11px;line-height:16px;"
            f'font-weight:600;padding:1px 8px;border-radius:9px;">'
            f"{html.escape(area)}</span>"
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
        return (
            '<tr><td class="px" style="padding:24px 28px 8px 28px;">'
            '<div class="txt" style="font-size:16px;line-height:22px;font-weight:600;'
            'color:#111827;">Nada pendiente hoy</div>'
            '<div class="txt-muted" style="font-size:14px;line-height:20px;'
            'color:#6b7280;margin-top:4px;">No hay tareas vencidas, para hoy ni '
            "para los próximos días.</div></td></tr>"
        )

    def _rescheduled_html(self, rescheduled: Sequence[Any]) -> str:
        """Small box at the end listing recurring tasks moved in this run."""
        if not rescheduled:
            return ""
        lines = []
        for item in rescheduled:
            title = html.escape(item.titulo)
            if item.url:
                title = (
                    f'<a href="{_attr(item.url)}" class="txt" '
                    f'style="color:#111827;text-decoration:none;">{title}</a>'
                )
            lines.append(
                f'<div style="margin-top:4px;"><strong>{title}</strong>: '
                f"{html.escape(self._moved_label(item))}</div>"
            )
        return (
            '<tr><td class="px" style="padding:24px 28px 0 28px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0"><tr><td class="card-ok txt" style="background-color:#ecfdf3;'
            "border-radius:8px;padding:12px 14px;font-size:13px;line-height:19px;"
            'color:#111827;">'
            '<div class="txt-ok" style="font-size:12px;font-weight:700;color:#067647;">'
            f"Reprogramadas hoy ({len(rescheduled)})</div>"
            f'{"".join(lines)}</td></tr></table></td></tr>'
        )

    @staticmethod
    def _moved_label(item: Any) -> str:
        """ "del 21 nov al 21 dic", or "al 21 dic" when the old date is unknown."""
        new = format_day_month(item.nueva_fecha)
        old = getattr(item, "fecha_anterior", None)
        return f"del {format_day_month(old)} al {new}" if old else f"al {new}"

    def _footer_html(self, warnings: Sequence[str]) -> str:
        blocks = []
        for warning in warnings:
            blocks.append(
                '<div class="txt-alert" style="color:#b42318;margin-bottom:8px;">'
                f"{html.escape(warning)}</div>"
            )
        if self.notion_tasks_url:
            blocks.append(
                f'<a href="{_attr(self.notion_tasks_url)}" class="link" '
                'style="color:#2563eb;text-decoration:none;font-weight:600;">'
                "Abrir Tareas en Notion</a>"
            )
        content = "".join(blocks)
        return (
            '<tr><td class="px" style="padding:24px 28px 28px 28px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'border="0"><tr><td class="line txt-muted" style="border-top:1px solid '
            "#eef0f2;padding-top:16px;font-size:12px;line-height:18px;"
            f'color:#6b7280;">{content}</td></tr></table></td></tr>'
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
