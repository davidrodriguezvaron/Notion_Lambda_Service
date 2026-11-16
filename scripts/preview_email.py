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

from app.common.adapter.email_adapter import EmailAdapter  # noqa: E402
from app.common.utils.dates import today_in  # noqa: E402
from app.logic.recurrence.recurrence_service import Rescheduled  # noqa: E402

TZ = ZoneInfo("America/Bogota")


def sample_tasks(today: date):
    def d(offset):
        return (today + timedelta(days=offset)).isoformat()

    page = "https://www.notion.so/ejemplo-"
    return [
        {"titulo": "Pagar ENEL", "fecha": d(-2), "area": "Hogar", "url": page + "1"},
        {
            "titulo": "Revisar SIMIT",
            "fecha": d(-1),
            "area": "Carro",
            "notas": "Consultar en https://www.fcm.org.co/simit/ antes de pagar.",
            "url": page + "2",
        },
        {
            "titulo": "Responder LinkedIn",
            "fecha": d(0),
            "area": "Trabajo",
            "url": page + "3",
        },
        {
            "titulo": "Vacuna Nala rabia",
            "fecha": f"{d(0)}T10:30:00.000-05:00",
            "area": "Gatos",
            "notas": "Llevar el carné de vacunas.\nPreguntar por la desparasitación.",
            "url": page + "4",
        },
        {"titulo": "Ajustar seguridad iPhone", "fecha": d(0), "url": page + "5"},
        {
            "titulo": "Cita médica Aleja",
            "fecha": f"{d(1)}T15:00:00.000-05:00",
            "area": "Salud",
            "url": page + "6",
        },
        {"titulo": "Cita mango", "fecha": d(2), "area": "Personal", "url": page + "7"},
        {
            "titulo": "Organizar bloques de trabajo en torno a las reuniones para poder enfocarme",
            "fecha": d(3),
            "area": "Estudio",
            "notas": "Ideas: arquitectura hexagonal, problema N+1, cursor vs offset. www.notion.so",
            "url": page + "8",
        },
    ]


def main():
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today_in(TZ)
    adapter = EmailAdapter(TZ, "https://www.notion.so/1fab41585726474ab6fba763401b3af3")
    rescheduled = [
        Rescheduled(
            "Pagar Vanti",
            date(2026, 12, 21),
            "https://www.notion.so/ejemplo-v",
            date(2026, 11, 21),
        ),
        Rescheduled("Pagar Spotify", date(2026, 12, 12), None, date(2026, 11, 12)),
    ]
    content = adapter.build_digest(sample_tasks(today), today, 3, rescheduled)
    empty = adapter.build_digest([], today, 3)

    out = ROOT / "preview"
    out.mkdir(exist_ok=True)
    (out / "email.html").write_text(content.html, encoding="utf-8")
    (out / "email.txt").write_text(content.text, encoding="utf-8")
    (out / "email_empty.html").write_text(empty.html, encoding="utf-8")
    print(f"Subject: {content.subject}")
    print(f"Wrote {out / 'email.html'}")


if __name__ == "__main__":
    main()
