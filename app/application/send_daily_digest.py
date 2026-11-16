"""
Use case: the daily run.

1. Reopen recurring tasks marked as done.
2. Read pending tasks up to today + upcoming days.
3. Send the digest, or skip it when there is nothing to report.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from app.application.ports import Clock, DigestComposer, EmailSender, TaskRepository
from app.application.reopen_recurring_tasks import ReopenRecurringTasks
from app.domain.agenda import build_agenda

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestOptions:
    timezone: ZoneInfo
    upcoming_days: int = 3
    send_empty_digest: bool = False

    def __post_init__(self):
        if self.upcoming_days < 0:
            raise ValueError("upcoming_days must be zero or positive")


@dataclass(frozen=True)
class DigestResult:
    email_sent: bool
    subject: str
    task_count: int
    rescheduled_count: int


class SendDailyDigest:
    def __init__(
        self,
        repository: TaskRepository,
        reopen_recurring: ReopenRecurringTasks,
        composer: DigestComposer,
        sender: EmailSender,
        clock: Clock,
        options: DigestOptions,
    ):
        self._repository = repository
        self._reopen_recurring = reopen_recurring
        self._composer = composer
        self._sender = sender
        self._clock = clock
        self._options = options

    def execute(self) -> DigestResult:
        reopened = self._reopen_recurring.execute()

        today = self._clock.today()
        logger.info(f"Today in {self._options.timezone}: {today.isoformat()}")
        until = today + timedelta(days=self._options.upcoming_days)
        tasks = self._repository.find_pending(until)
        logger.info(f"Retrieved {len(tasks)} pending tasks")

        agenda = build_agenda(
            tasks, today, self._options.upcoming_days, self._options.timezone
        )
        message = self._composer.compose(
            agenda, reopened.rescheduled, reopened.warnings
        )

        # Reschedules and warnings are always reported, even on an empty day.
        nothing_to_report = (
            agenda.is_empty and not reopened.rescheduled and not reopened.warnings
        )
        should_send = not nothing_to_report or self._options.send_empty_digest
        if should_send:
            self._sender.send(message)
            logger.info(f"Email sent: {message.subject}")
        else:
            logger.info("Nothing pending; email skipped (SEND_EMPTY_DIGEST=false).")

        return DigestResult(
            email_sent=should_send,
            subject=message.subject,
            task_count=agenda.total,
            rescheduled_count=len(reopened.rescheduled),
        )
