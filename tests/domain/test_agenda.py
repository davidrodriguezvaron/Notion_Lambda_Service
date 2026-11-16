import unittest
from datetime import date
from zoneinfo import ZoneInfo

from app.domain.agenda import build_agenda
from tests.fakes import task

TODAY = date(2026, 11, 16)
TZ = ZoneInfo("America/Bogota")


def titles(items):
    return [item.task.title for item in items]


class TestBuildAgenda(unittest.TestCase):
    def test_sections_and_window(self):
        agenda = build_agenda(
            [
                task("Vieja", "2026-11-10"),
                task("Ayer", "2026-11-15"),
                task("Hoy", "2026-11-16"),
                task("Mañana", "2026-11-17"),
                task("En tres", "2026-11-19"),
                task("Fuera de ventana", "2026-11-20"),
            ],
            TODAY,
            3,
            TZ,
        )
        self.assertEqual(titles(agenda.overdue), ["Vieja", "Ayer"])
        self.assertEqual(titles(agenda.due_today), ["Hoy"])
        self.assertEqual(titles(agenda.upcoming), ["Mañana", "En tres"])
        self.assertEqual(agenda.total, 5)
        self.assertFalse(agenda.is_empty)

    def test_late_night_utc_value_counts_as_today(self):
        # 10 p. m. in Bogota today, stored by Notion as the next UTC day.
        agenda = build_agenda([task("Noche", "2026-11-17T03:00:00.000Z")], TODAY, 0, TZ)
        self.assertEqual(titles(agenda.due_today), ["Noche"])
        self.assertEqual(agenda.due_today[0].time, "10:00 p. m.")

    def test_all_day_tasks_first_then_by_time(self):
        agenda = build_agenda(
            [
                task("B hora", "2026-11-16T15:00:00-05:00"),
                task("A hora", "2026-11-16T09:00:00-05:00"),
                task("Zeta", "2026-11-16"),
            ],
            TODAY,
            0,
            TZ,
        )
        self.assertEqual(titles(agenda.due_today), ["Zeta", "A hora", "B hora"])

    def test_task_without_date_goes_to_today(self):
        agenda = build_agenda([task("Sin fecha", None)], TODAY, 3, TZ)
        self.assertEqual(titles(agenda.due_today), ["Sin fecha"])
        self.assertIsNone(agenda.due_today[0].day)

    def test_negative_window_is_zero(self):
        agenda = build_agenda([task("Mañana", "2026-11-17")], TODAY, -2, TZ)
        self.assertTrue(agenda.is_empty)
        self.assertEqual(agenda.upcoming_days, 0)

    def test_sections_order(self):
        agenda = build_agenda([], TODAY, 3, TZ)
        self.assertEqual(
            [key for key, _ in agenda.sections()], ["overdue", "today", "upcoming"]
        )


if __name__ == "__main__":
    unittest.main()
