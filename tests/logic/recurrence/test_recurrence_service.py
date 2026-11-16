import unittest
from datetime import date
from unittest.mock import Mock

from app.common.integrations.notion.exceptions import NotionApiError
from app.logic.recurrence.recurrence_service import (
    PERMISSION_HINT,
    RecurrenceService,
    next_date,
    resolve_anchor,
)


def task(
    fecha, recurrencia="Mensual", dia_ancla=None, titulo="Pagar ENEL", task_id="t1"
):
    return {
        "id": task_id,
        "url": f"https://www.notion.so/{task_id}",
        "titulo": titulo,
        "fecha": fecha,
        "recurrencia": recurrencia,
        "dia_ancla": dia_ancla,
    }


class FakeRepository:
    """In-memory Notion: only Done tasks with recurrence are returned."""

    def __init__(self, tasks):
        self.tasks = {t["id"]: dict(t, status="Done") for t in tasks}
        self.patches = []

    def get_done_recurring_tasks(self):
        return [
            dict(t)
            for t in self.tasks.values()
            if t["status"] == "Done" and t.get("recurrencia")
        ]

    def reschedule_task(self, task_id, new_start, anchor_day):
        self.patches.append((task_id, new_start, anchor_day))
        stored = self.tasks[task_id]
        stored.update(status="Not Started", fecha=new_start)
        if anchor_day is not None:
            stored["dia_ancla"] = anchor_day


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
                self.assertEqual(next_date(base, interval, None), result)

    def test_end_of_month_round_trip(self):
        # 31 Jan -> 28 Feb -> 31 Mar -> 30 Apr -> 31 May
        current, anchor = date(2027, 1, 31), None
        seen = []
        for _ in range(4):
            anchor = resolve_anchor(current, anchor)
            current = next_date(current, "Mensual", anchor)
            seen.append(current)
        self.assertEqual(
            seen,
            [
                date(2027, 2, 28),
                date(2027, 3, 31),
                date(2027, 4, 30),
                date(2027, 5, 31),
            ],
        )

    def test_leap_year_february(self):
        self.assertEqual(
            next_date(date(2028, 1, 31), "Mensual", None), date(2028, 2, 29)
        )
        self.assertEqual(next_date(date(2028, 2, 29), "Anual", 29), date(2029, 2, 28))
        self.assertEqual(next_date(date(2031, 2, 28), "Anual", 29), date(2032, 2, 29))

    def test_weekly_ignores_anchor(self):
        self.assertEqual(next_date(date(2027, 1, 31), "Semanal", 31), date(2027, 2, 7))


class TestResolveAnchor(unittest.TestCase):
    def test_no_stored_anchor_uses_current_day(self):
        self.assertEqual(resolve_anchor(date(2027, 1, 31), None), 31)

    def test_clamped_date_keeps_anchor(self):
        self.assertEqual(resolve_anchor(date(2027, 2, 28), 31), 31)
        self.assertEqual(resolve_anchor(date(2027, 4, 30), 31), 31)

    def test_manual_move_overrides_anchor(self):
        # The user moved the task from the 21st to the 25th by hand.
        self.assertEqual(resolve_anchor(date(2026, 12, 25), 21), 25)


class TestRecurrenceService(unittest.TestCase):
    def test_reschedules_done_task_one_interval_from_its_own_date(self):
        repo = FakeRepository([task("2026-11-21")])
        result = RecurrenceService(repo).process()

        self.assertEqual(repo.patches, [("t1", "2026-12-21", 21)])
        self.assertEqual(len(result.rescheduled), 1)
        self.assertEqual(result.rescheduled[0].nueva_fecha, date(2026, 12, 21))
        self.assertEqual(result.rescheduled[0].titulo, "Pagar ENEL")
        self.assertEqual(result.warnings, [])

    def test_old_overdue_task_advances_only_one_interval(self):
        repo = FakeRepository([task("2026-08-21")])
        RecurrenceService(repo).process()
        self.assertEqual(repo.patches[0][1], "2026-09-21")

    def test_idempotent_on_second_run(self):
        repo = FakeRepository(
            [task("2026-11-21"), task("2026-12-12", "Anual", task_id="t2")]
        )
        service = RecurrenceService(repo)

        first = service.process()
        second = service.process()

        self.assertEqual(len(first.rescheduled), 2)
        self.assertEqual(second.rescheduled, [])
        self.assertEqual(len(repo.patches), 2)
        self.assertEqual(repo.tasks["t1"]["fecha"], "2026-12-21")

    def test_end_of_month_uses_stored_anchor(self):
        repo = FakeRepository([task("2027-02-28", dia_ancla=31)])
        RecurrenceService(repo).process()
        self.assertEqual(repo.patches, [("t1", "2027-03-31", 31)])

    def test_keeps_time_of_datetime_tasks(self):
        repo = FakeRepository([task("2026-11-21T10:30:00.000-05:00", "Semanal")])
        RecurrenceService(repo).process()
        self.assertEqual(repo.patches, [("t1", "2026-11-28T10:30:00.000-05:00", None)])

    def test_skips_task_without_date_or_unknown_interval(self):
        repo = FakeRepository(
            [task(None), task("2026-11-21", "Cada luna llena", task_id="t2")]
        )
        result = RecurrenceService(repo).process()
        self.assertEqual(repo.patches, [])
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
        self.assertEqual(len(result.warnings), 1)

    def test_retries_without_anchor_when_property_is_missing(self):
        repo = Mock()
        repo.get_done_recurring_tasks.return_value = [task("2026-11-21")]
        repo.reschedule_task.side_effect = [
            NotionApiError("Día ancla is not a property", status_code=400),
            None,
        ]
        result = RecurrenceService(repo).process()
        self.assertEqual(len(result.rescheduled), 1)
        self.assertEqual(
            repo.reschedule_task.call_args_list[1].args, ("t1", "2026-12-21", None)
        )

    def test_400_without_anchor_is_reported(self):
        repo = Mock()
        repo.get_done_recurring_tasks.return_value = [task("2026-11-21", "Semanal")]
        repo.reschedule_task.side_effect = NotionApiError("bad", status_code=400)
        result = RecurrenceService(repo).process()
        self.assertEqual(result.rescheduled, [])
        self.assertEqual(len(result.warnings), 1)


if __name__ == "__main__":
    unittest.main()
