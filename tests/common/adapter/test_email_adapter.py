import unittest
from datetime import date
from zoneinfo import ZoneInfo

from app.common.adapter.email_adapter import EmailAdapter
from app.logic.recurrence.recurrence_service import Rescheduled

TODAY = date(2026, 11, 16)  # Monday
TZ = ZoneInfo("America/Bogota")


def t(titulo, fecha, **extra):
    return dict({"id": titulo, "titulo": titulo, "fecha": fecha}, **extra)


class TestGrouping(unittest.TestCase):
    def setUp(self):
        self.adapter = EmailAdapter(TZ, "https://www.notion.so/db")

    def test_sections(self):
        tasks = [
            t("Vieja", "2026-11-10"),
            t("Ayer", "2026-11-15"),
            t("Hoy", "2026-11-16"),
            t("Mañana", "2026-11-17"),
            t("En tres", "2026-11-19"),
            t("Fuera de ventana", "2026-11-20"),
        ]
        s = self.adapter.group_tasks(tasks, TODAY, 3)
        self.assertEqual([x.titulo for x in s.overdue], ["Vieja", "Ayer"])
        self.assertEqual([x.titulo for x in s.today], ["Hoy"])
        self.assertEqual([x.titulo for x in s.upcoming], ["Mañana", "En tres"])
        self.assertEqual(s.total, 5)

    def test_utc_datetime_late_at_night_counts_as_today(self):
        # 10 p. m. in Bogota today, stored by Notion as the next UTC day.
        s = self.adapter.group_tasks([t("Noche", "2026-11-17T03:00:00.000Z")], TODAY, 0)
        self.assertEqual([x.titulo for x in s.today], ["Noche"])
        self.assertEqual(s.today[0].when.time, "10:00 p. m.")

    def test_sorting_all_day_first_then_time(self):
        tasks = [
            t("B hora", "2026-11-16T15:00:00-05:00"),
            t("A hora", "2026-11-16T09:00:00-05:00"),
            t("Zeta", "2026-11-16"),
        ]
        s = self.adapter.group_tasks(tasks, TODAY, 0)
        self.assertEqual([x.titulo for x in s.today], ["Zeta", "A hora", "B hora"])

    def test_missing_title_and_date(self):
        s = self.adapter.group_tasks([{"titulo": "  ", "fecha": None}], TODAY, 0)
        self.assertEqual(s.today[0].titulo, "(sin título)")


class TestSubject(unittest.TestCase):
    def setUp(self):
        self.adapter = EmailAdapter(TZ)

    def subject(self, tasks):
        return self.adapter.build_digest(tasks, TODAY, 3).subject

    def test_full_summary(self):
        tasks = [
            t("a", "2026-11-14"),
            t("b", "2026-11-15"),
            t("c", "2026-11-16"),
            t("d", "2026-11-17"),
        ]
        self.assertEqual(self.subject(tasks), "Tareas: 2 vencidas, 1 hoy, 1 próxima")

    def test_only_applicable_parts(self):
        self.assertEqual(self.subject([t("c", "2026-11-16")]), "Tareas: 1 hoy")
        self.assertEqual(self.subject([t("a", "2026-11-15")]), "Tareas: 1 vencida")
        self.assertEqual(
            self.subject([t("d", "2026-11-17"), t("e", "2026-11-18")]),
            "Tareas: 2 próximas",
        )

    def test_empty(self):
        self.assertEqual(self.subject([]), "Tareas: nada pendiente hoy")


class TestHtml(unittest.TestCase):
    def setUp(self):
        self.adapter = EmailAdapter(TZ, "https://www.notion.so/db")
        self.tasks = [
            t(
                "Pagar ENEL",
                "2026-11-14",
                area="Finanzas",
                url="https://www.notion.so/p1",
            ),
            t(
                "Vacuna <Nala>",
                "2026-11-16T10:30:00.000-05:00",
                area="Gatos",
                notas="Ver https://example.com/a?b=1&c=2.\nOtra línea www.test.co",
                url="https://www.notion.so/p2",
            ),
            t("Cita mango", "2026-11-18"),
        ]
        self.content = self.adapter.build_digest(
            self.tasks,
            TODAY,
            3,
            rescheduled=[
                Rescheduled(
                    "Pagar Vanti",
                    date(2026, 12, 21),
                    "https://www.notion.so/v",
                    date(2026, 11, 21),
                )
            ],
            warnings=["Aviso de permisos"],
        )
        self.html = self.content.html

    def test_is_email_safe(self):
        self.assertIn('<meta name="color-scheme" content="light dark">', self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn("max-width:600px", self.html)
        self.assertNotIn("linear-gradient", self.html)
        self.assertNotIn("box-shadow", self.html)
        self.assertNotIn("{{", self.html)

    def test_header_and_preheader(self):
        self.assertIn("Lunes, 16 de noviembre", self.html)
        self.assertIn("1 vencida, 1 hoy, 1 próxima", self.html)
        self.assertIn("display:none", self.html)

    def test_section_titles_and_rails(self):
        self.assertIn("Vencidas", self.html)
        self.assertIn("Próximos días", self.html)
        # Colored side rail per section: red, blue and gray.
        self.assertIn("border-left:4px solid #ef4444", self.html)
        self.assertIn("border-left:4px solid #3b82f6", self.html)
        self.assertIn("border-left:4px solid #cbd5e1", self.html)

    def test_empty_sections_hidden(self):
        content = self.adapter.build_digest([t("c", "2026-11-16")], TODAY, 3)
        self.assertNotIn('class="box rail-red"', content.html)
        self.assertNotIn('class="box rail-slate"', content.html)
        self.assertNotIn("Próximos días", content.html)
        self.assertIn('class="box rail-blue"', content.html)

    def test_overdue_cell_red_only_when_needed(self):
        red_cell = "background-color:#fee2e2;border:1px solid #fecaca"
        self.assertIn(red_cell, self.html)
        content = self.adapter.build_digest([t("c", "2026-11-16")], TODAY, 3)
        self.assertNotIn(red_cell, content.html)

    def test_task_title_links_to_notion_and_is_escaped(self):
        self.assertIn('href="https://www.notion.so/p1"', self.html)
        self.assertIn("Vacuna &lt;Nala&gt;", self.html)
        self.assertNotIn("<Nala>", self.html)

    def test_area_tag_and_relative_dates(self):
        self.assertIn(">💰 Finanzas</span>", self.html)
        self.assertIn("tag-finanzas", self.html)
        self.assertIn(">hace 2 días</span>", self.html)
        # Today and upcoming only show the time; the day is in the header.
        self.assertIn(">10:30 a. m.</span>", self.html)
        self.assertNotIn(">hoy</span>", self.html)
        self.assertIn(">Miércoles, 18 de noviembre</td>", self.html)

    def test_task_without_area_has_no_tag(self):
        content = self.adapter.build_digest([t("Sin area", "2026-11-16")], TODAY, 3)
        self.assertNotIn('class="tag-', content.html)

    def test_notes_links_escape_and_line_breaks(self):
        self.assertIn('href="https://example.com/a?b=1&amp;c=2"', self.html)
        self.assertIn(">https://example.com/a?b=1&amp;c=2</a>.", self.html)
        self.assertIn('href="https://www.test.co"', self.html)
        self.assertIn("<br>", self.html)

    def test_footer(self):
        self.assertIn("Reprogramadas hoy (1)", self.html)
        self.assertIn(">Pagar Vanti</a></strong>: ", self.html)
        self.assertIn(">del 21 nov al 21 dic</span>", self.html)
        # The rescheduled box comes after the task sections.
        self.assertGreater(
            self.html.index("Reprogramadas hoy"), self.html.index("Próximos días")
        )
        self.assertIn("Abrir Tareas en Notion", self.html)
        self.assertIn('href="https://www.notion.so/db"', self.html)
        self.assertIn("Aviso de permisos", self.html)

    def test_no_rescheduled_box_when_nothing_moved(self):
        content = self.adapter.build_digest([t("c", "2026-11-16")], TODAY, 3)
        self.assertNotIn("Reprogramadas hoy", content.html)
        self.assertNotIn("REPROGRAMADAS", content.text)

    def test_rescheduled_without_old_date_or_url(self):
        content = self.adapter.build_digest(
            [], TODAY, 3, rescheduled=[Rescheduled("Pagar TC", date(2026, 12, 1))]
        )
        self.assertIn("<strong>Pagar TC</strong>: ", content.html)
        self.assertIn(">al 1 dic</span>", content.html)

    def test_no_footer_link_without_url(self):
        content = EmailAdapter(TZ).build_digest([], TODAY, 3)
        self.assertNotIn("Abrir Tareas en Notion", content.html)

    def test_header_greeting(self):
        self.assertIn("Buenos días", self.html)
        self.assertIn(
            "Hoy tienes 1 tarea, 1 vencida por cerrar y 1 en los próximos días.",
            self.html,
        )

    def test_agenda_strip_one_cell_per_day(self):
        for label in (
            ">Vencidas</div>",
            ">Hoy</div>",
            ">Mañana</div>",
            ">Mié 18</div>",
            ">Jue 19</div>",
        ):
            self.assertIn(label, self.html)
        self.assertIn('width="20%"', self.html)

    def test_agenda_strip_collapses_long_windows(self):
        content = self.adapter.build_digest([t("d", "2026-11-22")], TODAY, 7)
        self.assertIn(">Próximas</div>", content.html)
        self.assertNotIn(">Mañana</div>", content.html)

    def test_upcoming_grouped_by_day(self):
        content = self.adapter.build_digest(
            [t("a", "2026-11-17"), t("b", "2026-11-17"), t("c", "2026-11-18")], TODAY, 3
        )
        self.assertEqual(content.html.count("Mañana · Martes, 17 de noviembre"), 1)
        self.assertEqual(content.html.count(">Miércoles, 18 de noviembre</td>"), 1)

    def test_greeting_variants(self):
        def line(tasks):
            return self.adapter.greeting_line(self.adapter.group_tasks(tasks, TODAY, 3))

        self.assertEqual(line([]), "No tienes nada pendiente. Disfruta el día.")
        self.assertEqual(line([t("a", "2026-11-16")]), "Hoy tienes 1 tarea.")
        self.assertEqual(
            line([t("a", "2026-11-15"), t("b", "2026-11-14")]),
            "Hoy no tienes tareas nuevas y 2 vencidas por cerrar.",
        )

    def test_warning_box(self):
        self.assertIn("<strong>Atención</strong>", self.html)

    def test_unknown_area_uses_default_style(self):
        content = self.adapter.build_digest(
            [t("x", "2026-11-16", area="Viajes")], TODAY, 3
        )
        self.assertIn(">Viajes</span>", content.html)

    def test_empty_digest(self):
        content = self.adapter.build_digest([], TODAY, 3)
        self.assertIn("Nada pendiente hoy", content.html)
        self.assertNotIn('card-neutral" width', content.html)

    def test_template_cached(self):
        first = self.adapter._load_template()
        self.assertIs(first, self.adapter._load_template())


class TestPlainText(unittest.TestCase):
    def test_same_sections_as_html(self):
        adapter = EmailAdapter(TZ, "https://www.notion.so/db")
        tasks = [
            t(
                "Pagar ENEL",
                "2026-11-14",
                area="Finanzas",
                url="https://www.notion.so/p1",
            ),
            t("Vacuna", "2026-11-16T10:30:00-05:00", notas="Llevar carné\n\nY correa"),
            t("Cita mango", "2026-11-17"),
        ]
        text = adapter.build_digest(
            tasks,
            TODAY,
            3,
            rescheduled=[
                Rescheduled(
                    "Pagar Vanti",
                    date(2026, 12, 21),
                    "https://www.notion.so/v",
                    date(2026, 11, 21),
                )
            ],
            warnings=["Revisa permisos"],
        ).text
        expected = (
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
            "Abrir Tareas en Notion: https://www.notion.so/db\n"
        )
        self.assertEqual(text, expected)
        self.assertNotIn("<", text)

    def test_empty(self):
        text = EmailAdapter(TZ).build_digest([], TODAY, 3).text
        self.assertIn("Nada pendiente hoy.", text)


if __name__ == "__main__":
    unittest.main()
