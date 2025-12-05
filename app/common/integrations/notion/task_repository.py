from datetime import datetime
from typing import Dict, Any, List, Optional
from app.common.logger.logger import get_logger
from app.common.integrations.notion.exceptions import NotionDataNotFoundError

logger = get_logger(__name__)


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
        filter_properties: str = "Fecha,Tarea,Notas",
    ):
        """
        Initialize the TaskRepository.

        Args:
            notion_client: The NotionClient instance for API calls.
            database_id: The Notion database ID containing tasks.
            filter_properties: Comma-separated list of properties to filter in the response.
        """
        self.notion_client = notion_client
        self.database_id = database_id
        self.filter_properties = filter_properties
        self.logger = logger

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Gets pending tasks from the Notion database.

        Retrieves tasks that are "Not Started" and have a date on or before today.

        Returns:
            List[Dict[str, Any]]: List of mapped tasks with id, titulo, fecha, and notas.

        Raises:
            NotionApiError: If the API request fails.
            NotionDataNotFoundError: If no tasks are found.
        """
        self.logger.info("Fetching pending tasks from Notion")
        payload = self._create_pending_tasks_payload()

        # NotionClient raises NotionApiError on HTTP errors
        response = self.notion_client.post(
            f"databases/{self.database_id}/query?{self._get_request_filters()}", payload
        )

        self.logger.debug(f"Response: {response}")

        # Check for empty results
        if not response.get("results"):
            raise NotionDataNotFoundError("No tasks found in Notion")

        return self._map_response(response)

    def _get_request_filters(self) -> str:
        """
        Gets the request filters for the Notion API.

        Returns:
            str: The request filters for the Notion API.
        """
        return "&".join(
            [f"filter_properties={prop}" for prop in self.filter_properties.split(",")]
        )

    def _map_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Maps the API response to a list of task data.

        Extracts fecha (date), notas (notes), and titulo (title) from each task.

        Args:
            response: The API response containing task data.

        Returns:
            List[Dict[str, Any]]: List of mapped tasks with fecha, notas, and titulo.
        """
        results = response.get("results", [])
        return [self._map_task(task) for task in results]

    def _map_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps a single task from the Notion API response.

        Args:
            task: A single page/task object from Notion.

        Returns:
            Dict[str, Any]: Mapped task with id, fecha, notas, and titulo.
        """
        properties = task.get("properties", {})

        return {
            "id": task.get("id"),
            "titulo": self._extract_title(properties),
            "fecha": self._extract_date(properties),
            "notas": self._extract_notes(properties),
        }

    def _extract_title(self, properties: Dict[str, Any]) -> str:
        """
        Extracts the title (Tarea) from task properties.

        Args:
            properties: The properties object from a Notion page.

        Returns:
            str: The task title, or empty string if not found.
        """
        tarea = properties.get("Tarea", {})
        title_list = tarea.get("title", [])
        if title_list:
            return title_list[0].get("plain_text", "")
        return ""

    def _extract_date(self, properties: Dict[str, Any]) -> Optional[str]:
        """
        Extracts the date (Fecha) from task properties.

        Args:
            properties: The properties object from a Notion page.

        Returns:
            Optional[str]: The task date in YYYY-MM-DD format, or None if not set.
        """
        fecha = properties.get("Fecha", {})
        date_obj = fecha.get("date")
        if date_obj:
            return date_obj.get("start")
        return None

    def _extract_notes(self, properties: Dict[str, Any]) -> str:
        """
        Extracts the notes (Notas) from task properties.

        Args:
            properties: The properties object from a Notion page.

        Returns:
            str: The concatenated notes text, or empty string if none.
        """
        notas = properties.get("Notas", {})
        rich_text_list = notas.get("rich_text", [])
        if rich_text_list:
            return "".join(item.get("plain_text", "") for item in rich_text_list)
        return ""

    def _create_pending_tasks_payload(self) -> Dict[str, Any]:
        """
        Creates the search payload for pending tasks.

        Returns:
            Dict[str, Any]: The filter and sort configuration for the query.
        """
        return {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"equals": "Not Started"}},
                    {
                        "property": "Fecha",
                        "date": {"on_or_before": self._get_current_date()},
                    },
                ]
            },
            "sorts": [{"property": "Fecha", "direction": "ascending"}],
        }

    def _get_current_date(self) -> str:
        """
        Gets the current date in ISO format.

        Returns:
            str: Current date in YYYY-MM-DD format.
        """
        return datetime.now().strftime("%Y-%m-%d")
