"""
Application settings, read once from environment variables.

Settings is an immutable object built at startup and passed to whoever needs
it, so no other module reads os.environ directly.
"""

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

TRUE_VALUES = {"1", "true", "yes", "si", "sí", "on"}
REQUIRED_VARS = (
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "SES_SENDER_EMAIL",
    "SES_RECEIVER_EMAIL",
)
DEFAULT_TIMEZONE = "America/Bogota"
DEFAULT_UPCOMING_DAYS = 3


class ConfigurationError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass(frozen=True)
class Settings:
    environment: str
    log_level: str
    notion_api_key: str
    notion_version: str
    notion_base_url: str
    notion_database_id: str
    notion_filter_properties: Tuple[str, ...]
    notion_tasks_url: str
    ses_sender: str
    ses_receiver: str
    aws_region: str
    timezone: ZoneInfo
    upcoming_days: int
    send_empty_digest: bool

    @classmethod
    def from_env(
        cls, env: Optional[Mapping[str, str]] = None, load_dotenv_file: bool = True
    ) -> "Settings":
        """
        Builds and validates settings.

        Args:
            env: Variables to read; defaults to os.environ.
            load_dotenv_file: Load a local .env first (only if it exists).

        Raises:
            ConfigurationError: If a required variable is missing or TIMEZONE
                is not a valid IANA time zone.
        """
        if env is None:
            if load_dotenv_file and os.path.exists(".env"):
                load_dotenv(".env")
            env = os.environ

        def get(name: str, default: str = "") -> str:
            return (env.get(name) or default).strip()

        missing = [name for name in REQUIRED_VARS if not get(name)]
        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        environment = _environment(get("ENVIRONMENT"), get("AWS_LAMBDA_FUNCTION_NAME"))
        database_id = get("NOTION_DATABASE_ID")
        return cls(
            environment=environment,
            log_level=_log_level(
                get("LOG_LEVEL", "INFO" if environment == "PRODUCTION" else "DEBUG")
            ),
            notion_api_key=get("NOTION_API_KEY"),
            notion_version=get("NOTION_VERSION", "2022-06-28"),
            notion_base_url=get("NOTION_BASE_URL", "https://api.notion.com/v1"),
            notion_database_id=database_id,
            notion_filter_properties=_split(
                get("NOTION_DATABASE_FILTER_PROPERTIES", "Notas,Tarea,Fecha,Área")
            ),
            notion_tasks_url=get("NOTION_TASKS_URL")
            or f"https://www.notion.so/{database_id.replace('-', '')}",
            ses_sender=get("SES_SENDER_EMAIL"),
            ses_receiver=get("SES_RECEIVER_EMAIL"),
            aws_region=get("AWS_REGION", "us-east-1"),
            timezone=_timezone(get("TIMEZONE", DEFAULT_TIMEZONE)),
            upcoming_days=_non_negative_int(
                get("UPCOMING_DAYS"), DEFAULT_UPCOMING_DAYS
            ),
            send_empty_digest=get("SEND_EMPTY_DIGEST", "false").lower() in TRUE_VALUES,
        )


def _environment(explicit: str, lambda_name: str) -> str:
    if explicit:
        return explicit
    return "PRODUCTION" if lambda_name else "LOCAL"


def _split(value: str) -> Tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _log_level(name: str) -> str:
    level = name.upper()
    if not isinstance(logging.getLevelName(level), int):
        raise ConfigurationError(f"Invalid LOG_LEVEL '{name}'")
    return level


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ConfigurationError(f"Invalid TIMEZONE '{name}': {e}") from e


def _non_negative_int(value: str, default: int) -> int:
    try:
        return max(0, int(value))
    except ValueError:
        return default
