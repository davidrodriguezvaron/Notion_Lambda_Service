"""
Interfaces the use cases depend on. Infrastructure and presentation provide
the implementations; the use cases never import them directly.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Protocol, Sequence

from app.domain.agenda import Agenda
from app.domain.recurrence import RescheduledTask
from app.domain.task import Task


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    html: str
    text: str


class TaskRepository(Protocol):
    def find_pending(self, until: date) -> List[Task]:
        """Pending tasks (not started or in progress) due on or before `until`."""

    def find_done_recurring(self) -> List[Task]:
        """Done tasks that have a recurrence."""

    def reopen(self, task_id: str, new_due: str) -> None:
        """Marks a task as not started and moves its due date."""


class DigestComposer(Protocol):
    def compose(
        self,
        agenda: Agenda,
        rescheduled: Sequence[RescheduledTask],
        warnings: Sequence[str],
    ) -> EmailMessage:
        """Builds the email for an agenda."""


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Delivers the message."""


class Clock(Protocol):
    def today(self) -> date:
        """Current date in the user's time zone."""
