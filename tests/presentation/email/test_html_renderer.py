import unittest
from datetime import date

from app.domain.recurrence import RescheduledTask
from app.presentation.email.html_renderer import PaperHtmlRenderer, load_template
from tests.fakes import task
from tests.presentation.email.helpers import NOTION_URL, agenda, sample_agenda

VANTI = RescheduledTask(
    "Pagar Vanti", date(2026, 12, 21), "https://www.notion.so/v", date(2026, 11, 21)
)


def render(a, rescheduled=(), warnings=(), url=NOTION_URL):
    return PaperHtmlRenderer(url).render(a, rescheduled, warnings)


class TestPaperHtmlRenderer(unittest.TestCase):
    def setUp(self):
        self.html = render(sample_agenda(), [VANTI], ["Aviso de permisos"])

    def test_is_email_safe(self):
        self.assertIn('<meta name="color-scheme" content="light dark">', self.html)
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn("max-width:600px", self.html)
        self.assertNotIn("linear-gradient", self.html)
        self.assertNotIn("box-shadow", self.html)
        self.assertNotIn("{{", self.html)

    def test_masthead_and_dateline(self):
        self.assertIn("Tareas · Edición diaria", self.html)
        self.assertIn("Nº 320", self.html)
        self.assertIn(">16</td>", self.html)
        self.assertIn(">lunes</div>", self.html)
        self.assertIn("de noviembre de 2026", self.html)
        self.assertIn(
            "Buenos días. Hoy tienes 1 tarea, 1 vencida por cerrar y 1 en los "
            "próximos días.",
            self.html,
        )

    def test_subject_and_preheader(self):
        self.assertIn("<title>Tareas: 1 vencida, 1 hoy, 1 próxima</title>", self.html)
        self.assertIn(">1 vencida, 1 hoy, 1 próxima&#8203;", self.html)

    def test_stats_box(self):
        for text in (">Vencidas</div>", ">Hoy</div>", ">Próximas</div>"):
            self.assertIn(text, self.html)
        self.assertIn('class="red stat"', self.html)
        self.assertNotIn('class="red stat"', render(agenda(task("c", "2026-11-16"))))

    def test_sections_numbered_in_order(self):
        self.assertIn("I. Pendientes de días anteriores", self.html)
        self.assertIn("II. Para hoy", self.html)
        self.assertIn("III. Lo que viene", self.html)

    def test_numbering_skips_empty_sections(self):
        html_ = render(agenda(task("c", "2026-11-16"), task("d", "2026-11-17")))
        self.assertIn("I. Para hoy", html_)
        self.assertIn("II. Lo que viene", html_)
        self.assertNotIn("Pendientes de días anteriores", html_)

    def test_titles_link_to_notion_and_are_escaped(self):
        self.assertIn('href="https://www.notion.so/p1"', self.html)
        self.assertIn("Vacuna &lt;Nala&gt;", self.html)
        self.assertNotIn("<Nala>", self.html)
        self.assertIn(">Cita mango</div>", self.html)  # no URL, no link

    def test_one_checkbox_per_task(self):
        self.assertEqual(self.html.count('class="box-red"'), 1)
        self.assertEqual(self.html.count('class="box"'), 2)

    def test_area_and_right_column(self):
        self.assertIn(
            '<i class="tag-finanzas" style="color:#3f7a4f;">finanzas</i>', self.html
        )
        self.assertIn(">hace 2 días</span>", self.html)
        self.assertIn(">10:30 a. m.</span>", self.html)
        self.assertNotIn(">hoy</span>", self.html)

    def test_unknown_area_uses_default_color(self):
        html_ = render(agenda(task("x", "2026-11-16", area="Viajes")))
        self.assertIn('style="color:#8a7b6e;">viajes</i>', html_)

    def test_no_area_no_details(self):
        self.assertNotIn('<i class="tag-', render(agenda(task("x", "2026-11-16"))))

    def test_title_uses_full_width_without_date_or_time(self):
        self.assertIn('colspan="2"', render(agenda(task("Sin hora", "2026-11-16"))))

    def test_upcoming_day_label_once_per_day(self):
        html_ = render(
            agenda(
                task("a", "2026-11-17"),
                task("b", "2026-11-17"),
                task("c", "2026-11-18"),
            )
        )
        self.assertEqual(html_.count(">mañana</td>"), 1)
        self.assertEqual(html_.count(">mié 18</td>"), 1)

    def test_notes(self):
        self.assertIn('href="https://example.com/a?b=1&amp;c=2"', self.html)
        self.assertIn("<br>", self.html)

    def test_rescheduled_note(self):
        self.assertIn("<i>Nota del día.</i> Se reprogramó", self.html)
        self.assertIn(">Pagar Vanti</a></b>", self.html)
        self.assertIn("(del 21 nov al 21 dic)", self.html)
        self.assertGreater(
            self.html.index("Nota del día"), self.html.index("Lo que viene")
        )

    def test_rescheduled_plural_without_old_date_or_url(self):
        html_ = render(
            agenda(),
            [
                RescheduledTask("Pagar TC", date(2026, 12, 1)),
                RescheduledTask("Pagar ETB", date(2026, 12, 12)),
            ],
        )
        self.assertIn("Se reprogramaron <b>Pagar TC</b>", html_)
        self.assertIn("(al 1 dic)</span> y <b>Pagar ETB</b>", html_)

    def test_no_note_or_warning_when_nothing_happened(self):
        html_ = render(agenda(task("c", "2026-11-16")))
        self.assertNotIn("Nota del día", html_)
        self.assertNotIn("<i>Aviso.</i>", html_)

    def test_warning(self):
        self.assertIn("<i>Aviso.</i> Aviso de permisos", self.html)

    def test_footer(self):
        self.assertIn("Abrir Tareas en Notion &rarr;</a>", self.html)
        self.assertIn(f'href="{NOTION_URL}"', self.html)
        self.assertIn("Chulea una tarea para quitarla de esta página.", self.html)
        self.assertNotIn("Abrir Tareas en Notion", render(agenda(), url=""))

    def test_dark_mode_area_colors(self):
        self.assertIn(".tag-finanzas { color: #8fcf9f !important; }", self.html)

    def test_blank_page(self):
        html_ = render(agenda())
        self.assertIn("Página en blanco.", html_)
        self.assertNotIn(">Vencidas</div>", html_)

    def test_template_is_cached(self):
        self.assertIs(load_template(), load_template())


if __name__ == "__main__":
    unittest.main()
