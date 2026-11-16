"""
Use case: reopen recurring tasks that were marked as done.

- Only done tasks with a supported recurrence are touched. Unchecked tasks are
  never moved, so an unpaid bill keeps showing as overdue.
- Each task moves one interval forward from its own date, in a single update
  that also sets it back to not started. A second run the same day finds it
  not started and leaves it alone, so the use case is idempotent.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.application.errors import (
    TaskStoreError,
    TaskStorePermissionError,
    TaskStoreSchemaError,
)
from app.application.ports import TaskRepository
from app.domain import recurrence
from app.domain.recurrence import RescheduledTask
from app.domain.task import Task

logger = logging.getLogger(__name__)

PERMISSION_HINT = (
    "La integración de Notion no tiene permiso para editar páginas. "
    "Actívalo en notion.so/profile/integrations > tu integración > "
    "Capabilities > Update content, y confirma que la base Tareas esté "
    "conectada a la integración."
)


@dataclass
class ReopenResult:
    rescheduled: List[RescheduledTask] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ReopenRecurringTasks:
    def __init__(self, repository: TaskRepository):
        self._repository = repository

    def execute(self) -> ReopenResult:
        result = ReopenResult()
        try:
            tasks = self._repository.find_done_recurring()
        except TaskStoreSchemaError as e:
            # Usually: the Recurrencia property does not exist yet.
            logger.warning(f"Recurrence query skipped: {e}")
            return result

        for task in tasks:
            try:
                moved = self._reopen(task)
            except TaskStorePermissionError as e:
                logger.exception(f"{PERMISSION_HINT} ({e})")
                result.warnings.append(PERMISSION_HINT)
                break
            except TaskStoreError as e:
                logger.exception(f"Could not reschedule '{task.title}': {e}")
                result.warnings.append(f'No se pudo reprogramar "{task.title}".')
                continue
            if moved:
                result.rescheduled.append(moved)
        return result

    def _reopen(self, task: Task) -> Optional[RescheduledTask]:
        if not recurrence.is_supported(task.recurrence) or not task.due:
            logger.warning(
                f"Skipping '{task.title}': recurrence={task.recurrence}, due={task.due}"
            )
            return None

        previous_day, new_day, new_due = recurrence.next_start(
            task.due, task.recurrence
        )
        self._repository.reopen(task.id, new_due)
        logger.info(f"Rescheduled '{task.title}' from {task.due} to {new_due}")
        return RescheduledTask(
            title=task.title or "(sin título)",
            new_day=new_day,
            url=task.url,
            previous_day=previous_day,
        )
