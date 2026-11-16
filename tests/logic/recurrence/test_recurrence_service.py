import unittest
from datetime import date
from unittest.mock import Mock

from app.common.integrations.notion.exceptions import NotionApiError
from app.logic.recurrence.recurrence_service import (
    PERMISSION_HINT,
    RecurrenceService,
    next_date,
)


def task(fecha, recurrencia="Mensual", titulo="Pagar ENEL", task_id="t1"):
    return {
        "id": task_id,
        "url": f"https://www.notion.so/{task_id}",
        "titulo": titulo,
        "fecha": fecha,
        "recurrencia": recurrencia,
    }


class FakeNotion:
    """
    In-memory version of the Tareas database that behaves like Notion:
    only Done tasks with a recurrence come back from the query, and a PATCH
    changes the stored status and date.
    """

    def __init__(self, tasks, done_ids=None):
        if done_ids is None:
            done_ids = [t["id"] for t in tasks]
        done_ids = set(done_ids)
        self.tasks = {
            t["id"]: dict(t, status="Done" if t["id"] in done_ids else "Not Started")
            for t in tasks
        }
        self.patches = []

    def get_done_recurring_tasks(self):
        return [
            dict(t)
            for t in self.tasks.values()
            if t["status"] == "Done" and t.get("recurrencia")
        ]

    def reschedule_task(self, task_id, new_start):
        self.patches.append((task_id, new_start))
        self.tasks[task_id].update(status="Not Started", fecha=new_start)

    def check(self, task_id):
        """Simulates ticking the Status checkbox in the "Todo" view."""
        self.tasks[task_id]["status"] = "Done"


class TestNextDate(unittest.TestCase):
    def test_each_interval(self):
        base = date(2026, 11, 21)
        expected = {
            "Semanal": date(2026, 11, 28),
            "Quincenal": date(2026, 12, 5),
            "Mensual": date(2026, 12, 21),
            "Bimestral": date(2027, 1, 21),
            "Trimestral": date(2027, 2, 21),
            "Semestral": date(2027, 5, 21),
            "Anual": date(2027, 11, 21),
        }
        for interval, result in expected.items():
            with self.subTest(interval=interval):
                self.assertEqual(next_date(base, interval), result)

    def test_water_bill_every_two_months_from_3_dec(self):
        dates = [date(2026, 12, 3)]
        for _ in range(3):
            dates.append(next_date(dates[-1], "Bimestral"))
        self.assertEqual(
            dates,
            [date(2026, 12, 3), date(2027, 2, 3), date(2027, 4, 3), date(2027, 6, 3)],
        )

    def test_end_of_month_uses_last_day(self):
        self.assertEqual(next_date(date(2027, 1, 31), "Mensual"), date(2027, 2, 28))
        self.assertEqual(next_date(date(2028, 1, 31), "Mensual"), date(2028, 2, 29))
        self.assertEqual(next_date(date(2026, 8, 31), "Semestral"), date(2027, 2, 28))

    def test_year_rollover(self):
        self.assertEqual(next_date(date(2026, 12, 12), "Mensual"), date(2027, 1, 12))
        self.assertEqual(next_date(date(2027, 9, 1), "Anual"), date(2028, 9, 1))


class TestRecurrenceService(unittest.TestCase):
    def test_checked_task_is_reopened_one_interval_from_its_own_date(self):
        notion = FakeNotion([task("2026-11-21")])
        result = RecurrenceService(notion).process()

        self.assertEqual(notion.patches, [("t1", "2026-12-21")])
        self.assertEqual(notion.tasks["t1"]["status"], "Not Started")
        self.assertEqual(len(result.rescheduled), 1)
        item = result.rescheduled[0]
        self.assertEqual(item.titulo, "Pagar ENEL")
        self.assertEqual(item.fecha_anterior, date(2026, 11, 21))
        self.assertEqual(item.nueva_fecha, date(2026, 12, 21))
        self.assertEqual(result.warnings, [])

    def test_unchecked_task_is_never_moved(self):
        # An unpaid bill stays where it is, so it keeps showing as overdue.
        notion = FakeNotion([task("2026-10-21")], done_ids=[])
        result = RecurrenceService(notion).process()

        self.assertEqual(notion.patches, [])
        self.assertEqual(notion.tasks["t1"]["fecha"], "2026-10-21")
        self.assertEqual(result.rescheduled, [])

    def test_checked_task_without_recurrence_stays_done(self):
        notion = FakeNotion([task("2026-11-21", recurrencia=None)])
        RecurrenceService(notion).process()
        self.assertEqual(notion.tasks["t1"]["status"], "Done")
        self.assertEqual(notion.patches, [])

    def test_late_payment_advances_only_one_interval(self):
        # Paid two months late: next date is the missed month, not today.
        notion = FakeNotion([task("2026-09-21")])
        RecurrenceService(notion).process()
        self.assertEqual(notion.patches, [("t1", "2026-10-21")])

    def test_idempotent_when_run_twice_the_same_day(self):
        notion = FakeNotion(
            [task("2026-11-21"), task("2026-12-03", "Bimestral", "Pagar agua", "t2")]
        )
        service = RecurrenceService(notion)

        first = service.process()
        second = service.process()

        self.assertEqual(len(first.rescheduled), 2)
        self.assertEqual(second.rescheduled, [])
        self.assertEqual(len(notion.patches), 2)
        self.assertEqual(notion.tasks["t1"]["fecha"], "2026-12-21")
        self.assertEqual(notion.tasks["t2"]["fecha"], "2027-02-03")

    def test_month_by_month_cycle(self):
        # Tick it, the Lambda reopens it, tick it again next month...
        notion = FakeNotion([task("2026-11-21")])
        service = RecurrenceService(notion)
        seen = []
        for _ in range(3):
            service.process()
            seen.append(notion.tasks["t1"]["fecha"])
            notion.check("t1")
        self.assertEqual(seen, ["2026-12-21", "2027-01-21", "2027-02-21"])

    def test_keeps_time_of_datetime_tasks(self):
        notion = FakeNotion([task("2026-11-21T10:30:00.000-05:00", "Semanal")])
        RecurrenceService(notion).process()
        self.assertEqual(notion.patches, [("t1", "2026-11-28T10:30:00.000-05:00")])

    def test_skips_task_without_date_or_unknown_interval(self):
        notion = FakeNotion(
            [task(None), task("2026-11-21", "Cada luna llena", task_id="t2")]
        )
        result = RecurrenceService(notion).process()
        self.assertEqual(notion.patches, [])
        self.assertEqual(result.rescheduled, [])

    def test_missing_property_in_database_is_not_fatal(self):
        repo = Mock()
        repo.get_done_recurring_tasks.side_effect = NotionApiError(
            "Could not find property with name or id: Recurrencia", status_code=400
        )
        result = RecurrenceService(repo).process()
        self.assertEqual(result.rescheduled, [])
        self.assertEqual(result.warnings, [])

    def test_other_query_errors_propagate(self):
        repo = Mock()
        repo.get_done_recurring_tasks.side_effect = NotionApiError(
            "boom", status_code=500
        )
        with self.assertRaises(NotionApiError):
            RecurrenceService(repo).process()

    def test_403_reports_which_capability_to_enable(self):
        repo = Mock()
        repo.get_done_recurring_tasks.return_value = [
            task("2026-11-21"),
            task("2026-11-22"),
        ]
        repo.reschedule_task.side_effect = NotionApiError("Forbidden", status_code=403)

        result = RecurrenceService(repo).process()

        self.assertEqual(result.warnings, [PERMISSION_HINT])
        self.assertIn("Update content", PERMISSION_HINT)
        repo.reschedule_task.assert_called_once()  # stops after the first 403

    def test_other_patch_errors_continue_with_next_task(self):
        repo = Mock()
        repo.get_done_recurring_tasks.return_value = [
            task("2026-11-21", titulo="Falla"),
            task("2026-11-22", titulo="Pagar Vanti", task_id="t2"),
        ]
        repo.reschedule_task.side_effect = [
            NotionApiError("conflict", status_code=409),
            None,
        ]
        result = RecurrenceService(repo).process()
        self.assertEqual([r.titulo for r in result.rescheduled], ["Pagar Vanti"])
        self.assertEqual(result.warnings, ['No se pudo reprogramar "Falla".'])


if __name__ == "__main__":
    unittest.main()
