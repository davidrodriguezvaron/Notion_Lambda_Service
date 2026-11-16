"""Thin HTTP client for the Notion REST API: auth, errors and pagination."""

import logging
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# (connect, read) timeout in seconds, so a stalled Notion API cannot hang the Lambda
REQUEST_TIMEOUT = (5, 30)
PAGE_SIZE = 100
MAX_PAGES = 50  # Safety net: 5000 rows per query is far beyond real usage.


class NotionApiError(Exception):
    """A request to the Notion API failed."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class NotionClient:
    def __init__(
        self,
        api_key: str,
        version: str,
        base_url: str = "https://api.notion.com/v1",
        session: Optional[requests.Session] = None,
    ):
        if not api_key:
            raise ValueError("Notion API key must be configured.")
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": version,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------ operations

    def query_data_source(
        self,
        data_source_id: str,
        body: Dict[str, Any],
        filter_properties: Iterable[str] = (),
    ) -> List[Dict[str, Any]]:
        """Runs a data source query and follows has_more / next_cursor."""
        endpoint = f"data_sources/{data_source_id}/query"
        query = "&".join(
            f"filter_properties={quote(name)}" for name in filter_properties
        )
        if query:
            endpoint = f"{endpoint}?{query}"

        results: List[Dict[str, Any]] = []
        cursor = None
        for _ in range(MAX_PAGES):
            page_body = dict(body, page_size=PAGE_SIZE)
            if cursor:
                page_body["start_cursor"] = cursor
            response = self.request("POST", endpoint, page_body)
            results.extend(response.get("results", []))
            cursor = response.get("next_cursor")
            if not response.get("has_more") or not cursor:
                break
        else:
            logger.warning(f"Stopped paginating after {MAX_PAGES} pages")
        return results

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("PATCH", f"pages/{page_id}", {"properties": properties})

    # ----------------------------------------------------------------- HTTP

    def request(
        self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends a request and returns the JSON body.

        Raises:
            NotionApiError: With the HTTP status when the API answers an error,
                or without it when the connection fails.
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making {method} request to {url}")
        try:
            response = self._session.request(
                method,
                url,
                headers=self._headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            detail = e.response.text if e.response is not None else str(e)
            logger.exception(f"Notion API request failed: {e}")
            raise NotionApiError(
                f"Notion API request failed: {detail}", status_code=status
            ) from e
        except requests.exceptions.RequestException as e:
            logger.exception(f"Notion API request failed: {e}")
            raise NotionApiError(f"Notion API connection error: {e}") from e
