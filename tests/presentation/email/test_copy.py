import unittest
from datetime import date

from app.domain.agenda import AgendaItem
from app.domain.recurrence import RescheduledTask
from app.domain.task import DueDate
from app.presentation.email import copy
from tests.fakes import task
from tests.presentation.email.helpers import TODAY, agenda


class TestSubject(unittest.TestCase):
    def test_full_summary(self):
        a = agenda(
            task("a", "2026-11-14"),
            task("b", "2026-11-15"),
            task("c", "2026-11-16"),
            task("d", "2026-11-17"),
        )
        self.assertEqual(copy.subject(a), "Tareas: 2 vencidas, 1 hoy, 1 próxima")

    def test_only_the_parts_that_apply(self):
        self.assertEqual(copy.subject(agenda(task("c", "2026-11-16"))), "Tareas: 1 hoy")
        self.assertEqual(
            copy.subject(agenda(task("a", "2026-11-15"))), "Tareas: 1 vencida"
        )
        self.assertEqual(
            copy.subject(agenda(task("d", "2026-11-17"), task("e", "2026-11-18"))),
            "Tareas: 2 próximas",
        )

    def test_empty(self):
        self.assertEqual(copy.subject(agenda()), "Tareas: nada pendiente hoy")
        self.assertEqual(copy.preheader(agenda()), copy.EMPTY_PREHEADER)

    def test_preheader_capitalizes_the_summary(self):
        self.assertEqual(copy.preheader(agenda(task("c", "2026-11-16"))), "1 hoy")
        self.assertEqual(copy.preheader(agenda(task("a", "2026-11-15"))), "1 vencida")


class TestGreeting(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(
            copy.greeting(agenda()), "No tienes nada pendiente. Disfruta el día."
        )
        self.assertEqual(
            copy.greeting(agenda(task("a", "2026-11-16"))), "Hoy tienes 1 tarea."
        )
        self.assertEqual(
            copy.greeting(agenda(task("a", "2026-11-15"), task("b", "2026-11-14"))),
            "Hoy no tienes tareas nuevas y 2 vencidas por cerrar.",
        )
        self.assertEqual(
            copy.greeting(
                agenda(
                    task("a", "2026-11-15"),
                    task("b", "2026-11-16"),
                    task("c", "2026-11-17"),
                )
            ),
            "Hoy tienes 1 tarea, 1 vencida por cerrar y 1 en los próximos días.",
        )


class TestLabels(unittest.TestCase):
    def test_when_label(self):
        def item(due):
            return AgendaItem(task("x"), due)

        self.assertEqual(copy.when_label(item(None), TODAY), "sin fecha")
        self.assertEqual(
            copy.when_label(item(DueDate(date(2026, 11, 14))), TODAY), "hace 2 días"
        )
        self.assertEqual(
            copy.when_label(item(DueDate(TODAY, "10:30 a. m.")), TODAY),
            "hoy, 10:30 a. m.",
        )

    def test_title_placeholder(self):
        self.assertEqual(copy.title_of(AgendaItem(task(""), None)), "(sin título)")

    def test_moved_label(self):
        moved = RescheduledTask("Vanti", date(2026, 12, 21), None, date(2026, 11, 21))
        self.assertEqual(copy.moved_label(moved), "del 21 nov al 21 dic")
        self.assertEqual(
            copy.moved_label(RescheduledTask("TC", date(2026, 12, 1))), "al 1 dic"
        )

    def test_join_es(self):
        self.assertEqual(copy.join_es([]), "")
        self.assertEqual(copy.join_es(["a"]), "a")
        self.assertEqual(copy.join_es(["a", "b", "c"]), "a, b y c")


if __name__ == "__main__":
    unittest.main()
