"""Names of the properties and status options in the "Tareas" database."""

TITLE = "Tarea"
DUE = "Fecha"
NOTES = "Notas"
STATUS = "Status"
AREA = "Área"
RECURRENCE = "Recurrencia"

STATUS_NOT_STARTED = "Not Started"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"
PENDING_STATUSES = (STATUS_NOT_STARTED, STATUS_IN_PROGRESS)

# Always requested in the pending query, even if NOTION_DATABASE_FILTER_PROPERTIES
# is configured with an older, shorter list.
REQUIRED_PROPERTIES = (TITLE, DUE, NOTES, AREA)
