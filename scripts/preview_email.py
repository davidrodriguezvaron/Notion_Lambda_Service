#!/usr/bin/env python3
"""
Builds the digest email with sample tasks and writes it to preview/email.html
(and preview/email.txt). Nothing is sent and Notion is not called.

Usage:
    python scripts/preview_email.py              # today in America/Bogota
    python scripts/preview_email.py 2026-11-15   # fixed date
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.application.clock import ZonedClock  # noqa: E402
from app.bootstrap import build_composer  # noqa: E402
from app.domain.agenda import build_agenda  # noqa: E402
from app.domain.recurrence import RescheduledTask  # noqa: E402
from app.domain.task import Task  # noqa: E402

TZ = ZoneInfo("America/Bogota")


def sample_tasks(today: date):
    def d(offset):
        return (today + timedelta(days=offset)).isoformat()

    page = "https://www.notion.so/ejemplo-"
    return [
        {"title": "Pagar ENEL", "due": d(-2), "area": "Hogar", "url": page + "1"},
        {
            "title": "Revisar SIMIT",
            "due": d(-1),
            "area": "Carro",
            "notes": "Consultar en https://www.fcm.org.co/simit/ antes de pagar.",
            "url": page + "2",
        },
        {
            "title": "Responder LinkedIn",
            "due": d(0),
            "area": "Trabajo",
            "url": page + "3",
        },
        {
            "title": "Vacuna Nala rabia",
            "due": f"{d(0)}T10:30:00.000-05:00",
            "area": "Gatos",
            "notes": "Llevar el carné de vacunas.\nPreguntar por la desparasitación.",
            "url": page + "4",
        },
        {"title": "Ajustar seguridad iPhone", "due": d(0), "url": page + "5"},
        {
            "title": "Cita médica Aleja",
            "due": f"{d(1)}T15:00:00.000-05:00",
            "area": "Salud",
            "url": page + "6",
        },
        {"title": "Cita mango", "due": d(2), "area": "Personal", "url": page + "7"},
        {
            "title": "Organizar bloques de trabajo en torno a las reuniones para poder enfocarme",
            "due": d(3),
            "area": "Estudio",
            "notes": "Ideas: arquitectura hexagonal, problema N+1, cursor vs offset. www.notion.so",
            "url": page + "8",
        },
    ]


def main():
    if len(sys.argv) > 1:
        today = date.fromisoformat(sys.argv[1])
    else:
        today = ZonedClock(TZ).today()
    composer = build_composer("https://www.notion.so/1fab41585726474ab6fba763401b3af3")
    tasks = [Task(id=str(n), **fields) for n, fields in enumerate(sample_tasks(today))]
    rescheduled = [
        RescheduledTask(
            "Pagar Vanti",
            date(2026, 12, 21),
            "https://www.notion.so/ejemplo-v",
            date(2026, 11, 21),
        ),
        RescheduledTask("Pagar Spotify", date(2026, 12, 12), None, date(2026, 11, 12)),
    ]
    content = composer.compose(build_agenda(tasks, today, 3, TZ), rescheduled, [])
    empty = composer.compose(build_agenda([], today, 3, TZ), [], [])

    out = ROOT / "preview"
    out.mkdir(exist_ok=True)
    (out / "email.html").write_text(content.html, encoding="utf-8")
    (out / "email.txt").write_text(content.text, encoding="utf-8")
    (out / "email_empty.html").write_text(empty.html, encoding="utf-8")
    print(f"Subject: {content.subject}")
    print(f"Wrote {out / 'email.html'}")


if __name__ == "__main__":
    main()
