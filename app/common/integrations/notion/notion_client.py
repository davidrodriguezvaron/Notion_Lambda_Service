import requests
from typing import Optional, Dict, Any
from app.common.logger.logger import get_logger
from app.common.environment.environment_handler import environment_handler
from app.common.integrations.notion.exceptions import NotionApiError


class NotionClient:
    """
    A generic client for interacting with the Notion API.

    This client handles authentication, base URL configuration, and common request patterns.
    It is designed to be extended or used as a utility for specific Notion operations.
    """

    def __init__(self):
        """
        Initialize the NotionClient.

        Configuration is loaded from the EnvironmentHandler.

        Raises:
            ValueError: If the API key is not configured.
        """

        self.api_key = environment_handler.notion_api_key
        if not self.api_key:
            raise ValueError("Notion API key must be configured in environment.")

        self.notion_version = environment_handler.notion_version
        self.base_url = environment_handler.notion_base_url
        self.logger = get_logger(__name__)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to make HTTP requests to the Notion API.

        Args:
            method (str): HTTP method (GET, POST, PATCH, DELETE).
            endpoint (str): The API endpoint (e.g., "pages", "databases").
                            Should not include the base URL.
            payload (Optional[Dict[str, Any]]): The JSON payload for the request.

        Returns:
            Dict[str, Any]: The JSON response from the API.

        Raises:
            NotionApiError: If the request fails.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = requests.request(method, url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Notion API request failed: {str(e)}")
            status_code = e.response.status_code if e.response is not None else None
            error_message = e.response.text if e.response is not None else str(e)
            raise NotionApiError(
                f"Notion API request failed: {error_message}", status_code=status_code
            )
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Notion API request failed: {str(e)}")
            raise NotionApiError(f"Notion API connection error: {str(e)}")

    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform a GET request to the Notion API.

        Args:
            endpoint (str): The API endpoint.

        Returns:
            Dict[str, Any]: The JSON response.
        """
        return self._make_request("GET", endpoint)

    def post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a POST request to the Notion API.

        Args:
            endpoint (str): The API endpoint.
            payload (Dict[str, Any]): The JSON payload.

        Returns:
            Dict[str, Any]: The JSON response.
        """
        return self._make_request("POST", endpoint, payload)

    def patch(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a PATCH request to the Notion API.

        Args:
            endpoint (str): The API endpoint.
            payload (Dict[str, Any]): The JSON payload.

        Returns:
            Dict[str, Any]: The JSON response.
        """
        return self._make_request("PATCH", endpoint, payload)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform a DELETE request to the Notion API.

        Args:
            endpoint (str): The API endpoint.

        Returns:
            Dict[str, Any]: The JSON response.
        """
        return self._make_request("DELETE", endpoint)


# Lazy singleton - only created when first accessed
_notion_client_instance = None


def get_notion_client() -> NotionClient:
    """
    Get the singleton NotionClient instance.

    Uses lazy initialization to avoid creating the client
    at module import time, which would fail without environment variables.

    Returns:
        NotionClient: The singleton client instance.
    """
    global _notion_client_instance
    if _notion_client_instance is None:
        _notion_client_instance = NotionClient()
    return _notion_client_instance
