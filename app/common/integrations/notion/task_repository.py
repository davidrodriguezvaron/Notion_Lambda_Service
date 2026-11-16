from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from app.common.logger.logger import get_logger

logger = get_logger(__name__)

PROP_TITLE = "Tarea"
PROP_DATE = "Fecha"
PROP_NOTES = "Notas"
PROP_STATUS = "Status"
PROP_AREA = "Área"
PROP_RECURRENCE = "Recurrencia"
PROP_ANCHOR = "Día ancla"

STATUS_NOT_STARTED = "Not Started"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"
PENDING_STATUSES = (STATUS_NOT_STARTED, STATUS_IN_PROGRESS)

# Properties the digest always needs, even if NOTION_DATABASE_FILTER_PROPERTIES
# is configured with an older, shorter list.
REQUIRED_PROPERTIES = (PROP_TITLE, PROP_DATE, PROP_NOTES, PROP_AREA)

PAGE_SIZE = 100
MAX_PAGES = 50  # Safety net: 5000 tasks per query is far beyond real usage.


class TaskRepository:
    """
    Repository for accessing task data from Notion.

    This class encapsulates the data access logic for tasks stored in Notion,
    providing a clean interface for querying and manipulating task data.
    """

    def __init__(
        self,
        notion_client,
        database_id: str,
        filter_properties: str = "Fecha,Tarea,Notas,Área",
    ):
        """
        Initialize the TaskRepository.

        Args:
            notion_client: The NotionClient instance for API calls.
            database_id: The Notion database ID containing tasks.
            filter_properties: Comma-separated list of properties to return.
        """
        self.notion_client = notion_client
        self.database_id = database_id
        self.filter_properties = filter_properties
        self.logger = logger

    # ------------------------------------------------------------------ queries

    def get_pending_tasks(
        self, today: date, upcoming_days: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Gets pending tasks ("Not Started" or "In Progress") whose date is on or
        before today + upcoming_days. Returns an empty list when there are none.

        Raises:
            NotionApiError: If the API request fails.
        """
        self.logger.info("Fetching pending tasks from Notion")
        # One extra day: Notion compares datetimes in UTC, so a task at 10 p. m.
        # in Bogota on the last day of the window is stored as the next UTC day.
        # The digest builder drops anything outside the local window.
        limit = today + timedelta(days=max(0, upcoming_days) + 1)
        payload = self._create_pending_tasks_payload(limit)
        endpoint = f"databases/{self.database_id}/query?{self._get_request_filters()}"
        results = self._query_all(endpoint, payload)
        return [self._map_task(task) for task in results]

    def get_done_recurring_tasks(self) -> List[Dict[str, Any]]:
        """
        Gets tasks in "Done" that have a recurrence configured.

        Raises:
            NotionApiError: If the API request fails (for example, 400 when the
            "Recurrencia" property does not exist yet).
        """
        payload = {
            "filter": {
                "and": [
                    {"property": PROP_STATUS, "status": {"equals": STATUS_DONE}},
                    {"property": PROP_RECURRENCE, "select": {"is_not_empty": True}},
                ]
            }
        }
        results = self._query_all(f"databases/{self.database_id}/query", payload)
        return [self._map_task(task) for task in results]

    def reschedule_task(
        self, task_id: str, new_start: str, anchor_day: Optional[int]
    ) -> Dict[str, Any]:
        """
        Reopens a recurring task with its next date (single PATCH, atomic).

        Args:
            task_id: Notion page id.
            new_start: New Fecha start (date or datetime ISO string).
            anchor_day: Day of month to remember for month based intervals.
        """
        properties: Dict[str, Any] = {
            PROP_STATUS: {"status": {"name": STATUS_NOT_STARTED}},
            PROP_DATE: {"date": {"start": new_start}},
        }
        if anchor_day is not None:
            properties[PROP_ANCHOR] = {"number": anchor_day}
        return self.notion_client.patch(f"pages/{task_id}", {"properties": properties})

    # ----------------------------------------------------------------- helpers

    def _query_all(self, endpoint: str, payload: Dict[str, Any]) -> List[Dict]:
        """Follows has_more / next_cursor until every page is read."""
        results: List[Dict[str, Any]] = []
        cursor = None
        for _ in range(MAX_PAGES):
            body = dict(payload, page_size=PAGE_SIZE)
            if cursor:
                body["start_cursor"] = cursor
            response = self.notion_client.post(endpoint, body)
            self.logger.debug(f"Response: {response}")
            results.extend(response.get("results", []))
            cursor = response.get("next_cursor")
            if not response.get("has_more") or not cursor:
                break
        else:
            self.logger.warning(f"Stopped paginating after {MAX_PAGES} pages")
        return results

    def _get_request_filters(self) -> str:
        """
        Builds the filter_properties query string. Required properties are
        always included and names are URL encoded ("Área").
        """
        configured = [p.strip() for p in self.filter_properties.split(",")]
        names: List[str] = []
        for name in configured + list(REQUIRED_PROPERTIES):
            if name and name not in names:
                names.append(name)
        return "&".join(f"filter_properties={quote(name)}" for name in names)

    def _map_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Maps a Notion page to the plain dict used by the rest of the app."""
        properties = task.get("properties", {})
        date_obj = (properties.get(PROP_DATE) or {}).get("date") or {}
        return {
            "id": task.get("id"),
            "url": task.get("url"),
            "titulo": self._extract_title(properties),
            "fecha": date_obj.get("start"),
            "notas": self._extract_notes(properties),
            "area": self._extract_select(properties, PROP_AREA),
            "recurrencia": self._extract_select(properties, PROP_RECURRENCE),
            "dia_ancla": self._extract_number(properties, PROP_ANCHOR),
        }

    @staticmethod
    def _join_rich_text(items: List[Dict[str, Any]]) -> str:
        return "".join(item.get("plain_text", "") for item in items or [])

    def _extract_title(self, properties: Dict[str, Any]) -> str:
        """Concatenates every rich text fragment of the title (Tarea)."""
        return self._join_rich_text((properties.get(PROP_TITLE) or {}).get("title"))

    def _extract_date(self, properties: Dict[str, Any]) -> Optional[str]:
        """Returns the Fecha start value, or None."""
        date_obj = (properties.get(PROP_DATE) or {}).get("date")
        return date_obj.get("start") if date_obj else None

    def _extract_notes(self, properties: Dict[str, Any]) -> str:
        """Concatenates every rich text fragment of Notas."""
        return self._join_rich_text((properties.get(PROP_NOTES) or {}).get("rich_text"))

    @staticmethod
    def _extract_select(properties: Dict[str, Any], name: str) -> Optional[str]:
        select = (properties.get(name) or {}).get("select")
        return select.get("name") if select else None

    @staticmethod
    def _extract_number(properties: Dict[str, Any], name: str) -> Optional[int]:
        value = (properties.get(name) or {}).get("number")
        return int(value) if isinstance(value, (int, float)) else None

    def _create_pending_tasks_payload(self, limit: date) -> Dict[str, Any]:
        """Filter: pending status and Fecha on or before the limit date."""
        return {
            "filter": {
                "and": [
                    {
                        "or": [
                            {"property": PROP_STATUS, "status": {"equals": status}}
                            for status in PENDING_STATUSES
                        ]
                    },
                    {
                        "property": PROP_DATE,
                        "date": {"on_or_before": limit.isoformat()},
                    },
                ]
            },
            "sorts": [{"property": PROP_DATE, "direction": "ascending"}],
        }
