"""Task repository backed by the Notion "Tareas" database."""

from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any, Dict, Iterator, List, Sequence

from app.application.errors import (
    TaskStoreError,
    TaskStorePermissionError,
    TaskStoreSchemaError,
)
from app.domain.task import Task
from app.infrastructure.notion import schema
from app.infrastructure.notion.client import NotionApiError, NotionClient
from app.infrastructure.notion.task_mapper import to_task


class NotionTaskRepository:
    def __init__(
        self,
        client: NotionClient,
        database_id: str,
        filter_properties: Sequence[str] = (),
    ):
        self._client = client
        self._database_id = database_id
        self._filter_properties = _with_required(filter_properties)

    def find_pending(self, until: date) -> List[Task]:
        # One extra day: Notion compares datetimes in UTC, so a task at 10 p. m.
        # in Bogota on the last day of the window is stored as the next UTC day.
        # The agenda drops anything outside the local window.
        limit = until + timedelta(days=1)
        body = {
            "filter": {
                "and": [
                    {
                        "or": [
                            {"property": schema.STATUS, "status": {"equals": status}}
                            for status in schema.PENDING_STATUSES
                        ]
                    },
                    {
                        "property": schema.DUE,
                        "date": {"on_or_before": limit.isoformat()},
                    },
                ]
            },
            "sorts": [{"property": schema.DUE, "direction": "ascending"}],
        }
        return self._query(body, self._filter_properties)

    def find_done_recurring(self) -> List[Task]:
        body = {
            "filter": {
                "and": [
                    {
                        "property": schema.STATUS,
                        "status": {"equals": schema.STATUS_DONE},
                    },
                    {"property": schema.RECURRENCE, "select": {"is_not_empty": True}},
                ]
            }
        }
        return self._query(body)

    def reopen(self, task_id: str, new_due: str) -> None:
        """Status and due date change in one update, never half applied."""
        properties = {
            schema.STATUS: {"status": {"name": schema.STATUS_NOT_STARTED}},
            schema.DUE: {"date": {"start": new_due}},
        }
        with _translate_errors():
            self._client.update_page(task_id, properties)

    def _query(
        self, body: Dict[str, Any], filter_properties: Sequence[str] = ()
    ) -> List[Task]:
        with _translate_errors():
            pages = self._client.query_database(
                self._database_id, body, filter_properties
            )
        return [to_task(page) for page in pages]


def _with_required(names: Sequence[str]) -> List[str]:
    result: List[str] = []
    for name in list(names) + list(schema.REQUIRED_PROPERTIES):
        name = name.strip()
        if name and name not in result:
            result.append(name)
    return result


@contextmanager
def _translate_errors() -> Iterator[None]:
    """Maps Notion API errors to the errors the use cases understand."""
    try:
        yield
    except NotionApiError as e:
        if e.status_code in (401, 403):
            raise TaskStorePermissionError(str(e)) from e
        if e.status_code == 400:
            raise TaskStoreSchemaError(str(e)) from e
        raise TaskStoreError(str(e)) from e
