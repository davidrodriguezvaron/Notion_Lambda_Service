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

    def build(self, tasks, **kwargs):
        return self.adapter.build_digest(tasks, TODAY, 3, **kwargs).html

    def test_is_email_safe(self):
        self.assertIn('<meta name="color-scheme" content="light dark">', self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn("max-width:600px", self.html)
        self.assertNotIn("linear-gradient", self.html)
        self.assertNotIn("box-shadow", self.html)
        self.assertNotIn("{{", self.html)

    def test_masthead_and_dateline(self):
        self.assertIn("Tareas · Edición diaria", self.html)
        self.assertIn("Nº 320", self.html)  # 16 Nov is day 320 of the year
        self.assertIn(">16</td>", self.html)
        self.assertIn(">lunes</div>", self.html)
        self.assertIn("de noviembre de 2026", self.html)
        self.assertIn(
            "Buenos días. Hoy tienes 1 tarea, 1 vencida por cerrar y 1 en los "
            "próximos días.",
            self.html,
        )

    def test_preheader(self):
        self.assertIn("1 vencida, 1 hoy, 1 próxima", self.html)
        self.assertIn("display:none", self.html)

    def test_stats_box(self):
        self.assertIn(">Vencidas</div>", self.html)
        self.assertIn(">Hoy</div>", self.html)
        self.assertIn(">Próximas</div>", self.html)

    def test_overdue_stat_red_only_when_needed(self):
        red_stat = 'class="red stat"'
        self.assertIn(red_stat, self.html)
        self.assertNotIn(red_stat, self.build([t("c", "2026-11-16")]))

    def test_sections_are_numbered_in_order(self):
        self.assertIn("I. Pendientes de días anteriores", self.html)
        self.assertIn("II. Para hoy", self.html)
        self.assertIn("III. Lo que viene", self.html)

    def test_numbering_skips_empty_sections(self):
        html_ = self.build([t("c", "2026-11-16"), t("d", "2026-11-17")])
        self.assertIn("I. Para hoy", html_)
        self.assertIn("II. Lo que viene", html_)
        self.assertNotIn("Pendientes de días anteriores", html_)

    def test_task_title_links_to_notion_and_is_escaped(self):
        self.assertIn('href="https://www.notion.so/p1"', self.html)
        self.assertIn("Vacuna &lt;Nala&gt;", self.html)
        self.assertNotIn("<Nala>", self.html)

    def test_checkbox_per_task(self):
        self.assertEqual(self.html.count('class="box-red"'), 1)  # overdue
        self.assertEqual(self.html.count('class="box"'), 2)  # today, upcoming

    def test_area_and_right_column(self):
        self.assertIn(">finanzas</i>", self.html)
        self.assertIn('class="tag-finanzas"', self.html)
        self.assertIn(">hace 2 días</span>", self.html)
        self.assertIn(">10:30 a. m.</span>", self.html)
        self.assertNotIn(">hoy</span>", self.html)

    def test_task_without_area_has_no_tag(self):
        self.assertNotIn('class="tag-', self.build([t("Sin area", "2026-11-16")]))

    def test_title_uses_full_width_without_date_or_time(self):
        html_ = self.build([t("Sin hora", "2026-11-16")])
        self.assertIn('colspan="2"', html_)

    def test_upcoming_day_label_once_per_day(self):
        html_ = self.build(
            [t("a", "2026-11-17"), t("b", "2026-11-17"), t("c", "2026-11-18")]
        )
        self.assertEqual(html_.count(">mañana</td>"), 1)
        self.assertEqual(html_.count(">mié 18</td>"), 1)

    def test_notes_links_escape_and_line_breaks(self):
        self.assertIn('href="https://example.com/a?b=1&amp;c=2"', self.html)
        self.assertIn(">https://example.com/a?b=1&amp;c=2</a>.", self.html)
        self.assertIn('href="https://www.test.co"', self.html)
        self.assertIn("<br>", self.html)

    def test_rescheduled_note(self):
        self.assertIn("<i>Nota del día.</i> Se reprogramó", self.html)
        self.assertIn(">Pagar Vanti</a></b>", self.html)
        self.assertIn("(del 21 nov al 21 dic)", self.html)
        # The note comes after the task sections.
        self.assertGreater(
            self.html.index("Nota del día"), self.html.index("Lo que viene")
        )

    def test_rescheduled_plural_and_without_old_date_or_url(self):
        html_ = self.build(
            [],
            rescheduled=[
                Rescheduled("Pagar TC", date(2026, 12, 1)),
                Rescheduled("Pagar ETB", date(2026, 12, 12)),
            ],
        )
        self.assertIn("Se reprogramaron <b>Pagar TC</b>", html_)
        self.assertIn("(al 1 dic)</span> y <b>Pagar ETB</b>", html_)

    def test_no_note_when_nothing_moved(self):
        content = self.adapter.build_digest([t("c", "2026-11-16")], TODAY, 3)
        self.assertNotIn("Nota del día", content.html)
        self.assertNotIn("REPROGRAMADAS", content.text)

    def test_warning(self):
        self.assertIn("<i>Aviso.</i> Aviso de permisos", self.html)

    def test_footer(self):
        self.assertIn("Abrir Tareas en Notion", self.html)
        self.assertIn('href="https://www.notion.so/db"', self.html)
        self.assertIn("Chulea una tarea para quitarla de esta página.", self.html)

    def test_no_footer_link_without_url(self):
        content = EmailAdapter(TZ).build_digest([], TODAY, 3)
        self.assertNotIn("Abrir Tareas en Notion", content.html)

    def test_greeting_variants(self):
        def line(tasks):
            return self.adapter.greeting_line(self.adapter.group_tasks(tasks, TODAY, 3))

        self.assertEqual(line([]), "No tienes nada pendiente. Disfruta el día.")
        self.assertEqual(line([t("a", "2026-11-16")]), "Hoy tienes 1 tarea.")
        self.assertEqual(
            line([t("a", "2026-11-15"), t("b", "2026-11-14")]),
            "Hoy no tienes tareas nuevas y 2 vencidas por cerrar.",
        )

    def test_unknown_area_uses_default_style(self):
        self.assertIn(">viajes</i>", self.build([t("x", "2026-11-16", area="Viajes")]))

    def test_dark_mode_area_colors(self):
        self.assertIn(".tag-finanzas { color: #8fcf9f !important; }", self.html)

    def test_empty_digest(self):
        html_ = self.build([])
        self.assertIn("Página en blanco.", html_)
        self.assertNotIn('class="red stat"', html_)
        self.assertNotIn(">Vencidas</div>", html_)

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
