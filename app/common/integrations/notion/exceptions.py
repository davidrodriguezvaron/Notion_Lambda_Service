"""
Custom exceptions for Notion integration.

This module defines specific exception types for handling errors
that occur during Notion API interactions.
"""


class NotionApiError(Exception):
    """
    Base exception for Notion API errors.

    Raised when a request to the Notion API fails or returns an error response.

    Attributes:
        message: A description of the error.
        status_code: The HTTP status code from the API response (if available).
    """

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class NotionDataNotFoundError(NotionApiError):
    """
    Exception raised when expected data is not found in Notion.

    Raised when a query returns no results or expected data is missing.
    """

    def __init__(self, message: str = "No data found in Notion"):
        super().__init__(message)
