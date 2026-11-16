import unittest
from datetime import date

from app.domain.recurrence import RescheduledTask
from app.presentation.email.text_renderer import PlainTextRenderer
from tests.fakes import task
from tests.presentation.email.helpers import NOTION_URL, agenda


class TestPlainTextRenderer(unittest.TestCase):
    def test_same_sections_as_the_html(self):
        text = PlainTextRenderer(NOTION_URL).render(
            agenda(
                task("Pagar ENEL", "2026-11-14", area="Finanzas", task_id="p1"),
                task(
                    "Vacuna",
                    "2026-11-16T10:30:00-05:00",
                    notes="Llevar carné\n\nY correa",
                    url=None,
                ),
                task("Cita mango", "2026-11-17", url=None),
            ),
            [
                RescheduledTask(
                    "Pagar Vanti", date(2026, 12, 21), None, date(2026, 11, 21)
                )
            ],
            ["Revisa permisos"],
        )
        self.assertEqual(
            text,
            "Tareas: 1 vencida, 1 hoy, 1 próxima\n"
            "Lunes, 16 de noviembre\n"
            "\n"
            "VENCIDAS (1)\n"
            "- Pagar ENEL [Finanzas] (hace 2 días)\n"
            "    https://www.notion.so/p1\n"
            "\n"
            "HOY (1)\n"
            "- Vacuna (hoy, 10:30 a. m.)\n"
            "    Llevar carné\n"
            "    Y correa\n"
            "\n"
            "PRÓXIMOS DÍAS (1)\n"
            "- Cita mango (mañana)\n"
            "\n"
            "REPROGRAMADAS HOY (1)\n"
            "- Pagar Vanti: del 21 nov al 21 dic\n"
            "\n"
            "Aviso: Revisa permisos\n"
            "\n"
            f"Abrir Tareas en Notion: {NOTION_URL}\n",
        )

    def test_empty_day_without_link(self):
        text = PlainTextRenderer("").render(agenda(), [], [])
        self.assertEqual(
            text,
            "Tareas: nada pendiente hoy\nLunes, 16 de noviembre\n\nNada pendiente hoy.\n",
        )


if __name__ == "__main__":
    unittest.main()
