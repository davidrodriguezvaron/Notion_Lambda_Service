import unittest
import requests
from unittest.mock import patch, MagicMock, PropertyMock
from app.common.integrations.notion.notion_client import NotionClient


class TestNotionClient(unittest.TestCase):

    def setUp(self):
        # We need to patch the properties on the class, not instances, or use PropertyMock
        self.api_key_patcher = patch(
            "app.common.environment.environment_handler.EnvironmentHandler.notion_api_key",
            new_callable=PropertyMock,
        )
        self.version_patcher = patch(
            "app.common.environment.environment_handler.EnvironmentHandler.notion_version",
            new_callable=PropertyMock,
        )
        self.base_url_patcher = patch(
            "app.common.environment.environment_handler.EnvironmentHandler.notion_base_url",
            new_callable=PropertyMock,
        )

        self.mock_api_key = self.api_key_patcher.start()
        self.mock_version = self.version_patcher.start()
        self.mock_base_url = self.base_url_patcher.start()

        self.mock_api_key.return_value = "test_api_key"
        self.mock_version.return_value = "2022-06-28"
        self.mock_base_url.return_value = "https://api.notion.com/v1"

        self.client = NotionClient()

    def tearDown(self):
        self.api_key_patcher.stop()
        self.version_patcher.stop()
        self.base_url_patcher.stop()

    def test_init_raises_error_without_api_key(self):
        self.mock_api_key.return_value = None
        with self.assertRaises(ValueError):
            NotionClient()

    @patch("requests.request")
    def test_make_request_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        response = self.client._make_request("GET", "pages/123")

        self.assertEqual(response, {"id": "123"})
        mock_request.assert_called_once_with(
            "GET",
            "https://api.notion.com/v1/pages/123",
            headers={
                "Authorization": "Bearer test_api_key",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json=None,
        )

    @patch("requests.request")
    def test_get_method(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_request.return_value = mock_response

        self.client.get("databases")
        mock_request.assert_called_with(
            "GET",
            "https://api.notion.com/v1/databases",
            headers=self.client.headers,
            json=None,
        )

    @patch("requests.request")
    def test_post_method(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "new"}
        mock_request.return_value = mock_response

        payload = {"title": "Test"}
        self.client.post("pages", payload)
        mock_request.assert_called_with(
            "POST",
            "https://api.notion.com/v1/pages",
            headers=self.client.headers,
            json=payload,
        )

    @patch("requests.request")
    def test_patch_method(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "updated"}
        mock_request.return_value = mock_response

        payload = {"archived": True}
        self.client.patch("pages/123", payload)
        mock_request.assert_called_with(
            "PATCH",
            "https://api.notion.com/v1/pages/123",
            headers=self.client.headers,
            json=payload,
        )

    @patch("requests.request")
    def test_delete_method(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "deleted"}
        mock_request.return_value = mock_response

        self.client.delete("blocks/123")
        mock_request.assert_called_with(
            "DELETE",
            "https://api.notion.com/v1/blocks/123",
            headers=self.client.headers,
            json=None,
        )

    @patch("requests.request")
    def test_make_request_failure(self, mock_request):
        # Simulate an HTTP error
        mock_response = MagicMock()
        error = requests.exceptions.HTTPError("404 Client Error")
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        # Verify that the exception is re-raised
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client._make_request("GET", "invalid_endpoint")
