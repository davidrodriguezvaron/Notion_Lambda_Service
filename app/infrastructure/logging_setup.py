"""Logging configuration, applied once at startup."""

import logging
import sys

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(level: str) -> None:
    """
    Sets the level on the root logger. The Lambda runtime already installs a
    handler; locally a stdout handler is added if there is none.
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setLevel(level)
