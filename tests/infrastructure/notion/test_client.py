import unittest
from unittest.mock import MagicMock

import requests

from app.infrastructure.notion.client import (
    MAX_PAGES,
    REQUEST_TIMEOUT,
    NotionApiError,
    NotionClient,
)

HEADERS = {
    "Authorization": "Bearer key",
    "Notion-Version": "2026-03-11",
    "Content-Type": "application/json",
}


def response(json_body=None, error=None):
    mock = MagicMock()
    mock.json.return_value = json_body or {}
    if error:
        mock.raise_for_status.side_effect = error
    return mock


class TestNotionClient(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.client = NotionClient("key", "2026-03-11", session=self.session)

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            NotionClient("", "2026-03-11", session=self.session)

    def test_request_sends_auth_headers_and_timeout(self):
        self.session.request.return_value = response({"id": "123"})

        result = self.client.request("GET", "/pages/123")

        self.assertEqual(result, {"id": "123"})
        self.session.request.assert_called_once_with(
            "GET",
            "https://api.notion.com/v1/pages/123",
            headers=HEADERS,
            json=None,
            timeout=REQUEST_TIMEOUT,
        )

    def test_http_error_keeps_the_status_and_body(self):
        failed = MagicMock(status_code=400, text="Other Error")
        error = requests.exceptions.HTTPError("400 Client Error")
        error.response = failed
        self.session.request.return_value = response(error=error)

        with self.assertRaises(NotionApiError) as cm:
            self.client.request("GET", "x")

        self.assertEqual(cm.exception.status_code, 400)
        self.assertEqual(
            str(cm.exception), "[400] Notion API request failed: Other Error"
        )

    def test_http_error_without_response(self):
        self.session.request.return_value = response(
            error=requests.exceptions.HTTPError("boom")
        )
        with self.assertRaises(NotionApiError) as cm:
            self.client.request("GET", "x")
        self.assertIsNone(cm.exception.status_code)

    def test_connection_error(self):
        self.session.request.side_effect = requests.exceptions.ConnectionError(
            "refused"
        )
        with self.assertRaises(NotionApiError) as cm:
            self.client.request("GET", "x")
        self.assertIn("connection error", str(cm.exception).lower())
        self.assertNotIn("[", str(cm.exception))

    def test_update_page(self):
        self.session.request.return_value = response({"id": "p"})
        self.client.update_page("p", {"Status": {}})
        args, kwargs = self.session.request.call_args
        self.assertEqual(args, ("PATCH", "https://api.notion.com/v1/pages/p"))
        self.assertEqual(kwargs["json"], {"properties": {"Status": {}}})


class TestQueryDatabase(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.client = NotionClient("key", "v", session=self.session)

    def bodies(self):
        return [c.kwargs["json"] for c in self.session.request.call_args_list]

    def test_follows_next_cursor_until_has_more_is_false(self):
        self.session.request.side_effect = [
            response({"results": [1], "has_more": True, "next_cursor": "c1"}),
            response({"results": [2], "has_more": True, "next_cursor": "c2"}),
            response({"results": [3], "has_more": False, "next_cursor": None}),
        ]

        results = self.client.query_data_source("db", {"filter": {}})

        self.assertEqual(results, [1, 2, 3])
        bodies = self.bodies()
        self.assertNotIn("start_cursor", bodies[0])
        self.assertEqual(bodies[1]["start_cursor"], "c1")
        self.assertEqual(bodies[2]["start_cursor"], "c2")
        self.assertEqual(bodies[0]["page_size"], 100)
        self.assertEqual(bodies[0]["filter"], {})

    def test_stops_when_the_cursor_is_missing(self):
        self.session.request.return_value = response({"results": [1], "has_more": True})
        self.client.query_data_source("db", {})
        self.assertEqual(self.session.request.call_count, 1)

    def test_safety_limit_on_pages(self):
        self.session.request.return_value = response(
            {"results": [], "has_more": True, "next_cursor": "x"}
        )
        self.client.query_data_source("db", {})
        self.assertEqual(self.session.request.call_count, MAX_PAGES)

    def test_filter_properties_are_url_encoded(self):
        self.session.request.return_value = response({"results": []})
        self.client.query_data_source("db", {}, ["Tarea", "Área"])
        url = self.session.request.call_args.args[1]
        self.assertEqual(
            url,
            "https://api.notion.com/v1/data_sources/db/query"
            "?filter_properties=Tarea&filter_properties=%C3%81rea",
        )

    def test_without_filter_properties(self):
        self.session.request.return_value = response({"results": []})
        self.client.query_data_source("db", {})
        self.assertTrue(self.session.request.call_args.args[1].endswith("/query"))


if __name__ == "__main__":
    unittest.main()
