import unittest
from unittest.mock import Mock, patch
from app.common.integrations.notion.task_repository import TaskRepository
from app.common.integrations.notion.exceptions import (
    NotionApiError,
    NotionDataNotFoundError,
)


class TestTaskRepository(unittest.TestCase):
    """Test cases for TaskRepository class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_notion_client = Mock()
        self.database_id = "test-database-id"
        self.filter_properties = "Fecha,Tarea,Notas"
        self.task_repository = TaskRepository(
            self.mock_notion_client, self.database_id, self.filter_properties
        )

    def test_init_stores_notion_client(self):
        """Test that __init__ stores the notion client."""
        self.assertEqual(self.task_repository.notion_client, self.mock_notion_client)

    def test_init_stores_database_id(self):
        """Test that __init__ stores the database ID."""
        self.assertEqual(self.task_repository.database_id, self.database_id)

    def test_get_pending_tasks_calls_notion_client_post(self):
        """Test that get_pending_tasks calls notion_client.post."""
        expected_response = {"results": [{"id": "task-1", "properties": {}}]}
        self.mock_notion_client.post.return_value = expected_response

        self.task_repository.get_pending_tasks()

        self.mock_notion_client.post.assert_called_once()

    def test_get_pending_tasks_uses_correct_endpoint(self):
        """Test that get_pending_tasks uses the correct database endpoint with filters."""
        self.mock_notion_client.post.return_value = {
            "results": [{"id": "1", "properties": {}}]
        }

        self.task_repository.get_pending_tasks()

        call_args = self.mock_notion_client.post.call_args
        endpoint = call_args[0][0]
        self.assertTrue(endpoint.startswith(f"databases/{self.database_id}/query?"))
        self.assertIn("filter_properties=", endpoint)

    def test_get_pending_tasks_includes_status_filter(self):
        """Test that payload includes Status filter for 'Not Started'."""
        self.mock_notion_client.post.return_value = {
            "results": [{"id": "1", "properties": {}}]
        }

        self.task_repository.get_pending_tasks()

        call_args = self.mock_notion_client.post.call_args
        payload = call_args[0][1]
        filters = payload["filter"]["and"]

        status_filter = next(
            (f for f in filters if f.get("property") == "Status"), None
        )
        self.assertIsNotNone(status_filter)
        self.assertEqual(status_filter["status"]["equals"], "Not Started")

    def test_get_pending_tasks_includes_date_filter(self):
        """Test that payload includes Fecha date filter."""
        self.mock_notion_client.post.return_value = {
            "results": [{"id": "1", "properties": {}}]
        }

        self.task_repository.get_pending_tasks()

        call_args = self.mock_notion_client.post.call_args
        payload = call_args[0][1]
        filters = payload["filter"]["and"]

        date_filter = next((f for f in filters if f.get("property") == "Fecha"), None)
        self.assertIsNotNone(date_filter)
        self.assertIn("on_or_before", date_filter["date"])

    def test_get_pending_tasks_includes_sort_by_date(self):
        """Test that payload includes sort by Fecha ascending."""
        self.mock_notion_client.post.return_value = {
            "results": [{"id": "1", "properties": {}}]
        }

        self.task_repository.get_pending_tasks()

        call_args = self.mock_notion_client.post.call_args
        payload = call_args[0][1]
        sorts = payload["sorts"]

        self.assertEqual(len(sorts), 1)
        self.assertEqual(sorts[0]["property"], "Fecha")
        self.assertEqual(sorts[0]["direction"], "ascending")

    def test_get_pending_tasks_raises_notion_api_error_on_failure(self):
        """Test that get_pending_tasks propagates NotionApiError from NotionClient."""
        # NotionClient now raises NotionApiError on HTTP errors
        self.mock_notion_client.post.side_effect = NotionApiError(
            "Unauthorized", status_code=401
        )

        with self.assertRaises(NotionApiError) as context:
            self.task_repository.get_pending_tasks()

        self.assertIn("Unauthorized", str(context.exception))
        self.assertEqual(context.exception.status_code, 401)

    def test_get_pending_tasks_raises_not_found_error_on_empty_results(self):
        """Test that get_pending_tasks raises NotionDataNotFoundError when no tasks found."""
        self.mock_notion_client.post.return_value = {"results": []}

        with self.assertRaises(NotionDataNotFoundError) as context:
            self.task_repository.get_pending_tasks()

        self.assertIn("No tasks found in Notion", str(context.exception))

    @patch("app.common.integrations.notion.task_repository.datetime")
    def test_get_current_date_returns_formatted_date(self, mock_datetime):
        """Test that _get_current_date returns date in YYYY-MM-DD format."""
        mock_datetime.now.return_value.strftime.return_value = "2025-12-05"

        result = self.task_repository._get_current_date()

        self.assertEqual(result, "2025-12-05")
        mock_datetime.now.return_value.strftime.assert_called_once_with("%Y-%m-%d")

    def test_map_response_returns_mapped_tasks(self):
        """Test that _map_response returns a list of mapped tasks."""
        response = {
            "results": [
                {
                    "id": "task-1",
                    "properties": {
                        "Tarea": {"title": [{"plain_text": "Test Task"}]},
                        "Fecha": {"date": {"start": "2025-12-05"}},
                        "Notas": {"rich_text": [{"plain_text": "Test notes"}]},
                    },
                }
            ]
        }

        result = self.task_repository._map_response(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "task-1")
        self.assertEqual(result[0]["titulo"], "Test Task")
        self.assertEqual(result[0]["fecha"], "2025-12-05")
        self.assertEqual(result[0]["notas"], "Test notes")

    def test_map_response_handles_empty_results(self):
        """Test that _map_response handles empty results."""
        response = {"results": []}

        result = self.task_repository._map_response(response)

        self.assertEqual(result, [])

    def test_map_task_extracts_all_fields(self):
        """Test that _map_task extracts id, titulo, fecha, and notas."""
        task = {
            "id": "abc-123",
            "properties": {
                "Tarea": {"title": [{"plain_text": "My Task"}]},
                "Fecha": {"date": {"start": "2025-11-24"}},
                "Notas": {"rich_text": [{"plain_text": "Some notes"}]},
            },
        }

        result = self.task_repository._map_task(task)

        self.assertEqual(result["id"], "abc-123")
        self.assertEqual(result["titulo"], "My Task")
        self.assertEqual(result["fecha"], "2025-11-24")
        self.assertEqual(result["notas"], "Some notes")

    def test_extract_title_returns_plain_text(self):
        """Test that _extract_title returns the title plain text."""
        properties = {"Tarea": {"title": [{"plain_text": "Task Title"}]}}

        result = self.task_repository._extract_title(properties)

        self.assertEqual(result, "Task Title")

    def test_extract_title_returns_empty_string_when_no_title(self):
        """Test that _extract_title returns empty string when title is missing."""
        properties = {"Tarea": {"title": []}}

        result = self.task_repository._extract_title(properties)

        self.assertEqual(result, "")

    def test_extract_date_returns_start_date(self):
        """Test that _extract_date returns the start date."""
        properties = {"Fecha": {"date": {"start": "2025-12-05", "end": None}}}

        result = self.task_repository._extract_date(properties)

        self.assertEqual(result, "2025-12-05")

    def test_extract_date_returns_none_when_no_date(self):
        """Test that _extract_date returns None when date is not set."""
        properties = {"Fecha": {"date": None}}

        result = self.task_repository._extract_date(properties)

        self.assertIsNone(result)

    def test_extract_notes_returns_concatenated_text(self):
        """Test that _extract_notes returns concatenated rich text."""
        properties = {
            "Notas": {
                "rich_text": [
                    {"plain_text": "First part. "},
                    {"plain_text": "Second part."},
                ]
            }
        }

        result = self.task_repository._extract_notes(properties)

        self.assertEqual(result, "First part. Second part.")

    def test_extract_notes_returns_empty_string_when_no_notes(self):
        """Test that _extract_notes returns empty string when notes are empty."""
        properties = {"Notas": {"rich_text": []}}

        result = self.task_repository._extract_notes(properties)

        self.assertEqual(result, "")

    def test_init_stores_filter_properties(self):
        """Test that __init__ stores the filter properties."""
        self.assertEqual(self.task_repository.filter_properties, self.filter_properties)

    def test_init_uses_default_filter_properties(self):
        """Test that __init__ uses default filter properties when not provided."""
        repo = TaskRepository(self.mock_notion_client, self.database_id)
        self.assertEqual(repo.filter_properties, "Fecha,Tarea,Notas")

    def test_get_request_filters_returns_formatted_string(self):
        """Test that _get_request_filters returns correctly formatted query params."""
        result = self.task_repository._get_request_filters()

        self.assertIn("filter_properties=Fecha", result)
        self.assertIn("filter_properties=Tarea", result)
        self.assertIn("filter_properties=Notas", result)
        self.assertEqual(result.count("&"), 2)

    def test_get_request_filters_with_single_property(self):
        """Test that _get_request_filters works with single property."""
        repo = TaskRepository(self.mock_notion_client, self.database_id, "Status")

        result = repo._get_request_filters()

        self.assertEqual(result, "filter_properties=Status")


if __name__ == "__main__":
    unittest.main()
