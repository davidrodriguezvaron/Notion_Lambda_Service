import unittest
from datetime import date
from zoneinfo import ZoneInfo

from app.application.ports import EmailMessage
from app.application.reopen_recurring_tasks import ReopenRecurringTasks
from app.application.send_daily_digest import DigestOptions, SendDailyDigest
from tests.fakes import FakeTaskRepository, FixedClock, RecordingSender, task

TZ = ZoneInfo("America/Bogota")
TODAY = date(2026, 11, 16)


class RecordingComposer:
    def __init__(self):
        self.calls = []

    def compose(self, agenda, rescheduled, warnings):
        self.calls.append((agenda, list(rescheduled), list(warnings)))
        return EmailMessage(subject=f"{agenda.total} tareas", html="<p>", text="t")


class TestSendDailyDigest(unittest.TestCase):
    def run_digest(self, repo, send_empty=False, upcoming_days=3):
        self.sender = RecordingSender()
        self.composer = RecordingComposer()
        use_case = SendDailyDigest(
            repository=repo,
            reopen_recurring=ReopenRecurringTasks(repo),
            composer=self.composer,
            sender=self.sender,
            clock=FixedClock(TODAY),
            options=DigestOptions(TZ, upcoming_days, send_empty),
        )
        return use_case.execute()

    def test_sends_the_digest_of_pending_tasks(self):
        repo = FakeTaskRepository(pending=[task("Hoy", "2026-11-16")])
        result = self.run_digest(repo)

        self.assertTrue(result.email_sent)
        self.assertEqual(result.task_count, 1)
        self.assertEqual(result.subject, "1 tareas")
        self.assertEqual(len(self.sender.sent), 1)
        agenda = self.composer.calls[0][0]
        self.assertEqual(agenda.today, TODAY)

    def test_asks_for_tasks_up_to_the_end_of_the_window(self):
        repo = FakeTaskRepository()
        self.run_digest(repo, upcoming_days=3)
        self.assertEqual(repo.pending_until, date(2026, 11, 19))

    def test_negative_window_is_rejected(self):
        with self.assertRaises(ValueError):
            DigestOptions(TZ, -1)

    def test_empty_day_succeeds_without_email(self):
        result = self.run_digest(FakeTaskRepository())
        self.assertFalse(result.email_sent)
        self.assertEqual(self.sender.sent, [])

    def test_empty_day_sends_when_enabled(self):
        result = self.run_digest(FakeTaskRepository(), send_empty=True)
        self.assertTrue(result.email_sent)
        self.assertEqual(len(self.sender.sent), 1)

    def test_reschedules_run_first_and_are_always_reported(self):
        done = task("Pagar ENEL", "2026-11-14", recurrence="Mensual", task_id="e")
        repo = FakeTaskRepository(done=[done])

        result = self.run_digest(repo)

        self.assertTrue(result.email_sent)
        self.assertEqual(result.rescheduled_count, 1)
        _, rescheduled, _ = self.composer.calls[0]
        self.assertEqual(rescheduled[0].new_day, date(2026, 12, 14))


if __name__ == "__main__":
    unittest.main()
