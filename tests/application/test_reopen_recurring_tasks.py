import unittest
from datetime import date
from unittest.mock import Mock

from app.application.errors import (
    TaskStoreError,
    TaskStorePermissionError,
    TaskStoreSchemaError,
)
from app.application.reopen_recurring_tasks import (
    PERMISSION_HINT,
    ReopenRecurringTasks,
)
from tests.fakes import FakeTaskRepository, task


def recurring(due="2026-11-21", interval="Mensual", title="Pagar ENEL", task_id="t1"):
    return task(title, due, recurrence=interval, task_id=task_id)


class TestReopenRecurringTasks(unittest.TestCase):
    def test_checked_task_reopens_one_interval_from_its_own_date(self):
        repo = FakeTaskRepository(done=[recurring()])
        result = ReopenRecurringTasks(repo).execute()

        self.assertEqual(repo.reopened, [("t1", "2026-12-21")])
        self.assertEqual(repo.status["t1"], "Not Started")
        moved = result.rescheduled[0]
        self.assertEqual(moved.title, "Pagar ENEL")
        self.assertEqual(moved.previous_day, date(2026, 11, 21))
        self.assertEqual(moved.new_day, date(2026, 12, 21))
        self.assertEqual(moved.url, "https://www.notion.so/t1")
        self.assertEqual(result.warnings, [])

    def test_unchecked_task_is_never_moved(self):
        # An unpaid bill stays where it is, so it keeps showing as overdue.
        repo = FakeTaskRepository(pending=[recurring("2026-10-21")])
        result = ReopenRecurringTasks(repo).execute()
        self.assertEqual(repo.reopened, [])
        self.assertEqual(result.rescheduled, [])

    def test_checked_task_without_recurrence_stays_done(self):
        repo = FakeTaskRepository(done=[task("Comprar RAM", task_id="t1")])
        ReopenRecurringTasks(repo).execute()
        self.assertEqual(repo.status["t1"], "Done")

    def test_late_payment_advances_only_one_interval(self):
        repo = FakeTaskRepository(done=[recurring("2026-09-21")])
        ReopenRecurringTasks(repo).execute()
        self.assertEqual(repo.reopened, [("t1", "2026-10-21")])

    def test_idempotent_when_run_twice_the_same_day(self):
        repo = FakeTaskRepository(
            done=[
                recurring(),
                recurring("2026-12-03", "Bimestral", "Pagar agua", "t2"),
            ]
        )
        use_case = ReopenRecurringTasks(repo)
        first = use_case.execute()
        second = use_case.execute()

        self.assertEqual(len(first.rescheduled), 2)
        self.assertEqual(second.rescheduled, [])
        self.assertEqual(repo.reopened, [("t1", "2026-12-21"), ("t2", "2027-02-03")])

    def test_month_by_month_cycle(self):
        # Tick it, the Lambda reopens it, tick it again next month...
        repo = FakeTaskRepository(done=[recurring()])
        use_case = ReopenRecurringTasks(repo)
        seen = []
        for _ in range(3):
            use_case.execute()
            seen.append(repo.tasks["t1"].due)
            repo.check("t1")
        self.assertEqual(seen, ["2026-12-21", "2027-01-21", "2027-02-21"])

    def test_keeps_the_time_of_datetime_tasks(self):
        repo = FakeTaskRepository(
            done=[recurring("2026-11-21T10:30:00.000-05:00", "Semanal")]
        )
        ReopenRecurringTasks(repo).execute()
        self.assertEqual(repo.reopened, [("t1", "2026-11-28T10:30:00.000-05:00")])

    def test_skips_tasks_without_date_or_with_unknown_interval(self):
        repo = FakeTaskRepository(
            done=[recurring(None), recurring(interval="Cada luna llena", task_id="t2")]
        )
        result = ReopenRecurringTasks(repo).execute()
        self.assertEqual(repo.reopened, [])
        self.assertEqual(result.rescheduled, [])

    def test_untitled_task_gets_a_placeholder(self):
        repo = FakeTaskRepository(done=[recurring(title="")])
        result = ReopenRecurringTasks(repo).execute()
        self.assertEqual(result.rescheduled[0].title, "(sin título)")

    def test_missing_property_is_not_fatal(self):
        repo = Mock()
        repo.find_done_recurring.side_effect = TaskStoreSchemaError("no Recurrencia")
        result = ReopenRecurringTasks(repo).execute()
        self.assertEqual((result.rescheduled, result.warnings), ([], []))

    def test_other_query_errors_propagate(self):
        repo = Mock()
        repo.find_done_recurring.side_effect = TaskStoreError("boom")
        with self.assertRaises(TaskStoreError):
            ReopenRecurringTasks(repo).execute()

    def test_permission_error_says_what_to_enable_and_stops(self):
        repo = Mock()
        repo.find_done_recurring.return_value = [recurring(), recurring(task_id="t2")]
        repo.reopen.side_effect = TaskStorePermissionError("Forbidden")

        result = ReopenRecurringTasks(repo).execute()

        self.assertEqual(result.warnings, [PERMISSION_HINT])
        self.assertIn("Update content", PERMISSION_HINT)
        repo.reopen.assert_called_once()

    def test_other_update_errors_continue_with_the_next_task(self):
        repo = Mock()
        repo.find_done_recurring.return_value = [
            recurring(title="Falla"),
            recurring(title="Pagar Vanti", task_id="t2"),
        ]
        repo.reopen.side_effect = [TaskStoreError("conflict"), None]

        result = ReopenRecurringTasks(repo).execute()

        self.assertEqual([r.title for r in result.rescheduled], ["Pagar Vanti"])
        self.assertEqual(result.warnings, ['No se pudo reprogramar "Falla".'])


if __name__ == "__main__":
    unittest.main()
