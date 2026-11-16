"""Errors the use cases understand, raised by repository implementations."""


class TaskStoreError(Exception):
    """The task store failed (network, server error, unexpected response)."""


class TaskStorePermissionError(TaskStoreError):
    """The integration is not allowed to read or change tasks."""


class TaskStoreSchemaError(TaskStoreError):
    """The request does not match the database, e.g. a missing property."""
