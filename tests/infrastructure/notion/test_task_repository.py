import unittest
from datetime import date
from unittest.mock import Mock

from app.application.errors import (
    TaskStoreError,
    TaskStorePermissionError,
    TaskStoreSchemaError,
)
from app.infrastructure.notion.client import NotionApiError
from app.infrastructure.notion.task_repository import NotionTaskRepository

PAGE = {"id": "1", "properties": {"Tarea": {"title": [{"plain_text": "Pagar ENEL"}]}}}


class TestNotionTaskRepository(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.query_data_source.return_value = [PAGE]
        self.repo = NotionTaskRepository(self.client, "db", ("Notas", "Tarea", "Fecha"))

    def query(self):
        data_source_id, body, filter_properties = (
            self.client.query_data_source.call_args.args
        )
        return data_source_id, body, filter_properties

    def test_find_pending_maps_pages_to_tasks(self):
        tasks = self.repo.find_pending(date(2026, 11, 19))
        self.assertEqual([t.title for t in tasks], ["Pagar ENEL"])

    def test_find_pending_filters_status_and_date_with_one_day_margin(self):
        self.repo.find_pending(date(2026, 11, 19))
        data_source_id, body, _ = self.query()

        self.assertEqual(data_source_id, "db")
        statuses, due = body["filter"]["and"]
        self.assertEqual(
            [f["status"]["equals"] for f in statuses["or"]],
            ["Not Started", "In Progress"],
        )
        self.assertEqual(
            due, {"property": "Fecha", "date": {"on_or_before": "2026-11-20"}}
        )
        self.assertEqual(
            body["sorts"], [{"property": "Fecha", "direction": "ascending"}]
        )

    def test_find_pending_always_requests_required_properties(self):
        self.repo.find_pending(date(2026, 11, 19))
        self.assertEqual(self.query()[2], ["Notas", "Tarea", "Fecha", "Área"])

    def test_filter_properties_are_trimmed_and_deduplicated(self):
        repo = NotionTaskRepository(
            self.client, "db", (" Status", "Tarea", "Tarea", "")
        )
        repo.find_pending(date(2026, 11, 19))
        self.assertEqual(self.query()[2], ["Status", "Tarea", "Fecha", "Notas", "Área"])

    def test_find_done_recurring(self):
        self.repo.find_done_recurring()
        _, body, filter_properties = self.query()
        self.assertEqual(
            body["filter"]["and"],
            [
                {"property": "Status", "status": {"equals": "Done"}},
                {"property": "Recurrencia", "select": {"is_not_empty": True}},
            ],
        )
        self.assertEqual(filter_properties, ())

    def test_reopen_updates_status_and_date_together(self):
        self.repo.reopen("page-1", "2026-12-21")
        self.client.update_page.assert_called_once_with(
            "page-1",
            {
                "Status": {"status": {"name": "Not Started"}},
                "Fecha": {"date": {"start": "2026-12-21"}},
            },
        )

    def test_translates_notion_errors(self):
        cases = {
            401: TaskStorePermissionError,
            403: TaskStorePermissionError,
            400: TaskStoreSchemaError,
            500: TaskStoreError,
            None: TaskStoreError,
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                self.client.update_page.side_effect = NotionApiError("x", status)
                with self.assertRaises(expected):
                    self.repo.reopen("p", "2026-12-21")

    def test_query_errors_are_translated_too(self):
        self.client.query_data_source.side_effect = NotionApiError("x", 400)
        with self.assertRaises(TaskStoreSchemaError):
            self.repo.find_done_recurring()


if __name__ == "__main__":
    unittest.main()
