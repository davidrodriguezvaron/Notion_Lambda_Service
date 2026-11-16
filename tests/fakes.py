"""In-memory doubles for the application ports."""

from datetime import date
from typing import Dict, List, Optional

from app.application.ports import EmailMessage
from app.domain.task import Task

BASE_ENV = {
    "NOTION_API_KEY": "secret",
    "NOTION_DATABASE_ID": "1fab-4158",
    "NOTION_DATA_SOURCE_ID": "ad1c-51ed",
    "SES_SENDER_EMAIL": "sender@example.com",
    "SES_RECEIVER_EMAIL": "receiver@example.com",
}


def task(
    title: str = "Pagar ENEL",
    due: Optional[str] = "2026-11-21",
    recurrence: Optional[str] = None,
    task_id: Optional[str] = None,
    **extra,
) -> Task:
    return Task(
        id=task_id or title,
        title=title,
        due=due,
        recurrence=recurrence,
        url=extra.pop("url", f"https://www.notion.so/{task_id or title}"),
        **extra,
    )


class FakeTaskRepository:
    """
    Behaves like the Tareas database: tasks have a status, only done tasks
    with a recurrence come back as recurring, and reopen changes the stored
    status and date.
    """

    def __init__(self, pending: List[Task] = (), done: List[Task] = ()):
        self.status: Dict[str, str] = {}
        self.tasks: Dict[str, Task] = {}
        for item in pending:
            self._store(item, "Not Started")
        for item in done:
            self._store(item, "Done")
        self.reopened: List[tuple] = []
        self.pending_until: Optional[date] = None

    def _store(self, item: Task, status: str) -> None:
        self.tasks[item.id] = item
        self.status[item.id] = status

    def find_pending(self, until: date) -> List[Task]:
        self.pending_until = until
        return [t for t in self.tasks.values() if self.status[t.id] == "Not Started"]

    def find_done_recurring(self) -> List[Task]:
        return [
            t
            for t in self.tasks.values()
            if self.status[t.id] == "Done" and t.recurrence
        ]

    def reopen(self, task_id: str, new_due: str) -> None:
        self.reopened.append((task_id, new_due))
        old = self.tasks[task_id]
        self._store(
            Task(
                id=old.id,
                title=old.title,
                due=new_due,
                notes=old.notes,
                area=old.area,
                recurrence=old.recurrence,
                url=old.url,
            ),
            "Not Started",
        )

    def check(self, task_id: str) -> None:
        """Simulates ticking the Status checkbox in the "Todo" view."""
        self.status[task_id] = "Done"


class RecordingSender:
    def __init__(self):
        self.sent: List[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class FixedClock:
    def __init__(self, today: date):
        self._today = today

    def today(self) -> date:
        return self._today
