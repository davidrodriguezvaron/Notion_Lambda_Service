"""Converts Notion pages into domain tasks."""

from typing import Any, Dict, List, Optional

from app.domain.task import Task
from app.infrastructure.notion import schema


def to_task(page: Dict[str, Any]) -> Task:
    properties = page.get("properties", {})
    return Task(
        id=page.get("id"),
        url=page.get("url"),
        title=_rich_text(properties, schema.TITLE, "title").strip(),
        due=_date_start(properties, schema.DUE),
        notes=_rich_text(properties, schema.NOTES, "rich_text").strip(),
        area=_select(properties, schema.AREA),
        recurrence=_select(properties, schema.RECURRENCE),
    )


def _rich_text(properties: Dict[str, Any], name: str, kind: str) -> str:
    """Joins every fragment, not only the first one."""
    fragments: List[Dict[str, Any]] = (properties.get(name) or {}).get(kind) or []
    return "".join(fragment.get("plain_text", "") for fragment in fragments)


def _date_start(properties: Dict[str, Any], name: str) -> Optional[str]:
    value = (properties.get(name) or {}).get("date")
    return value.get("start") if value else None


def _select(properties: Dict[str, Any], name: str) -> Optional[str]:
    value = (properties.get(name) or {}).get("select")
    return value.get("name") if value else None
