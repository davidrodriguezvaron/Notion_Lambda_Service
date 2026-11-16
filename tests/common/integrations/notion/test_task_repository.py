import unittest
from datetime import date
from unittest.mock import Mock

from app.common.integrations.notion.exceptions import NotionApiError
from app.common.integrations.notion.task_repository import TaskRepository

TODAY = date(2026, 11, 16)


def page(page_id, title="Tarea", **props):
    properties = {"Tarea": {"title": [{"plain_text": title}]}}
    properties.update(props)
    return {
        "id": page_id,
        "url": f"https://www.notion.so/{page_id}",
        "properties": properties,
    }


class TestTaskRepository(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.post.return_value = {"results": [page("1")], "has_more": False}
        self.repo = TaskRepository(self.client, "db-id", "Fecha,Tarea,Notas")

    def _payload(self, call=0):
        return self.client.post.call_args_list[call][0][1]

    # ------------------------------------------------------------ init/filters

    def test_init_stores_values(self):
        self.assertEqual(self.repo.notion_client, self.client)
        self.assertEqual(self.repo.database_id, "db-id")
        self.assertEqual(self.repo.filter_properties, "Fecha,Tarea,Notas")

    def test_default_filter_properties(self):
        self.assertEqual(
            TaskRepository(self.client, "db").filter_properties,
            "Fecha,Tarea,Notas,Área",
        )

    def test_request_filters_always_include_required_and_encode_accents(self):
        result = self.repo._get_request_filters()
        self.assertEqual(
            result,
            "filter_properties=Fecha&filter_properties=Tarea"
            "&filter_properties=Notas&filter_properties=%C3%81rea",
        )

    def test_request_filters_deduplicates(self):
        repo = TaskRepository(self.client, "db", "Status, Tarea,,Tarea")
        self.assertEqual(repo._get_request_filters().count("Tarea"), 1)
        self.assertTrue(
            repo._get_request_filters().startswith("filter_properties=Status")
        )

    # ---------------------------------------------------------- pending query

    def test_pending_uses_database_query_endpoint(self):
        self.repo.get_pending_tasks(TODAY, 3)
        endpoint = self.client.post.call_args[0][0]
        self.assertTrue(endpoint.startswith("databases/db-id/query?filter_properties="))

    def test_pending_includes_not_started_and_in_progress(self):
        self.repo.get_pending_tasks(TODAY, 3)
        status_filter = self._payload()["filter"]["and"][0]["or"]
        self.assertEqual(
            [f["status"]["equals"] for f in status_filter],
            ["Not Started", "In Progress"],
        )

    def test_pending_date_window_has_one_day_margin(self):
        self.repo.get_pending_tasks(TODAY, 3)
        date_filter = self._payload()["filter"]["and"][1]
        self.assertEqual(date_filter["date"]["on_or_before"], "2026-11-20")

    def test_pending_without_upcoming_days(self):
        self.repo.get_pending_tasks(TODAY)
        self.assertEqual(
            self._payload()["filter"]["and"][1]["date"]["on_or_before"], "2026-11-17"
        )

    def test_pending_sorted_by_date(self):
        self.repo.get_pending_tasks(TODAY, 3)
        self.assertEqual(
            self._payload()["sorts"], [{"property": "Fecha", "direction": "ascending"}]
        )

    def test_empty_results_return_empty_list(self):
        self.client.post.return_value = {"results": [], "has_more": False}
        self.assertEqual(self.repo.get_pending_tasks(TODAY, 3), [])

    def test_api_errors_propagate(self):
        self.client.post.side_effect = NotionApiError("Unauthorized", status_code=401)
        with self.assertRaises(NotionApiError) as ctx:
            self.repo.get_pending_tasks(TODAY, 3)
        self.assertEqual(ctx.exception.status_code, 401)

    # ------------------------------------------------------------- pagination

    def test_follows_next_cursor_until_has_more_is_false(self):
        self.client.post.side_effect = [
            {"results": [page("1")], "has_more": True, "next_cursor": "c1"},
            {"results": [page("2")], "has_more": True, "next_cursor": "c2"},
            {"results": [page("3")], "has_more": False, "next_cursor": None},
        ]
        tasks = self.repo.get_pending_tasks(TODAY, 3)

        self.assertEqual([t["id"] for t in tasks], ["1", "2", "3"])
        self.assertEqual(self.client.post.call_count, 3)
        self.assertNotIn("start_cursor", self._payload(0))
        self.assertEqual(self._payload(1)["start_cursor"], "c1")
        self.assertEqual(self._payload(2)["start_cursor"], "c2")
        self.assertEqual(self._payload(0)["page_size"], 100)

    def test_stops_when_cursor_missing(self):
        self.client.post.return_value = {"results": [page("1")], "has_more": True}
        self.repo.get_pending_tasks(TODAY, 3)
        self.assertEqual(self.client.post.call_count, 1)

    def test_safety_limit_on_pages(self):
        self.client.post.return_value = {
            "results": [],
            "has_more": True,
            "next_cursor": "x",
        }
        self.repo._query_all("databases/db/query", {})
        self.assertEqual(self.client.post.call_count, 50)

    # ---------------------------------------------------------------- mapping

    def test_map_task_extracts_every_field(self):
        raw = page(
            "abc",
            Fecha={"date": {"start": "2026-11-21T10:30:00.000-05:00", "end": None}},
            Notas={"rich_text": [{"plain_text": "Uno. "}, {"plain_text": "Dos."}]},
            **{
                "Área": {"select": {"name": "Finanzas"}},
                "Recurrencia": {"select": {"name": "Mensual"}},
            },
        )
        result = self.repo._map_task(raw)
        self.assertEqual(
            result,
            {
                "id": "abc",
                "url": "https://www.notion.so/abc",
                "titulo": "Tarea",
                "fecha": "2026-11-21T10:30:00.000-05:00",
                "notas": "Uno. Dos.",
                "area": "Finanzas",
                "recurrencia": "Mensual",
            },
        )

    def test_map_task_handles_missing_properties(self):
        result = self.repo._map_task(
            {"id": "x", "properties": {"Fecha": {"date": None}}}
        )
        self.assertEqual(result["titulo"], "")
        self.assertIsNone(result["fecha"])
        self.assertIsNone(result["area"])

    def test_title_concatenates_all_fragments(self):
        props = {
            "Tarea": {
                "title": [
                    {"plain_text": "Pagar "},
                    {"plain_text": "ENEL"},
                    {"plain_text": " (link)"},
                ]
            }
        }
        self.assertEqual(self.repo._extract_title(props), "Pagar ENEL (link)")

    def test_title_empty(self):
        self.assertEqual(self.repo._extract_title({"Tarea": {"title": []}}), "")

    def test_extract_date(self):
        self.assertEqual(
            self.repo._extract_date({"Fecha": {"date": {"start": "2026-12-05"}}}),
            "2026-12-05",
        )
        self.assertIsNone(self.repo._extract_date({"Fecha": {"date": None}}))

    def test_extract_notes(self):
        self.assertEqual(self.repo._extract_notes({"Notas": {"rich_text": []}}), "")

    # ------------------------------------------------------------- recurrence

    def test_done_recurring_query(self):
        self.repo.get_done_recurring_tasks()
        endpoint, payload = self.client.post.call_args[0]
        self.assertEqual(endpoint, "databases/db-id/query")
        self.assertEqual(
            payload["filter"]["and"],
            [
                {"property": "Status", "status": {"equals": "Done"}},
                {"property": "Recurrencia", "select": {"is_not_empty": True}},
            ],
        )

    def test_reschedule_task_patches_status_and_date_together(self):
        self.repo.reschedule_task("page-1", "2026-12-21")
        self.client.patch.assert_called_once_with(
            "pages/page-1",
            {
                "properties": {
                    "Status": {"status": {"name": "Not Started"}},
                    "Fecha": {"date": {"start": "2026-12-21"}},
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
