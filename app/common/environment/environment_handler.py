import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

TRUE_VALUES = {"1", "true", "yes", "si", "sí", "on"}


class EnvironmentHandler:
    def __init__(self):
        if os.path.exists(".env"):
            load_dotenv()

    @property
    def environment(self):
        """Returns the current environment (LOCAL, PRODUCTION, etc)."""
        # If ENVIRONMENT is explicitly set, use it
        if os.getenv("ENVIRONMENT"):
            return os.getenv("ENVIRONMENT")

        # If running in Lambda (and ENVIRONMENT not set), default to PRODUCTION
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return "PRODUCTION"

        # Default to LOCAL
        return "LOCAL"

    @property
    def log_level(self):
        """Returns the configured log level based on environment."""
        default_level = "INFO" if self.environment == "PRODUCTION" else "DEBUG"
        return os.getenv("LOG_LEVEL", default_level)

    @property
    def notion_api_key(self):
        """Returns the Notion API key."""
        return os.getenv("NOTION_API_KEY")

    @property
    def notion_version(self):
        """Returns the Notion API version."""
        return os.getenv("NOTION_VERSION", "2022-06-28")

    @property
    def notion_base_url(self):
        """Returns the Notion API base URL."""
        return os.getenv("NOTION_BASE_URL", "https://api.notion.com/v1")

    @property
    def notion_database_id(self):
        """Returns the Notion database ID."""
        return os.getenv("NOTION_DATABASE_ID")

    @property
    def notion_database_filter_properties(self):
        """Returns the Notion database filter properties."""
        return os.getenv("NOTION_DATABASE_FILTER_PROPERTIES", "Notas,Tarea,Fecha,Área")

    @property
    def timezone_name(self):
        """Returns the IANA time zone used to decide what "today" is."""
        return os.getenv("TIMEZONE", "America/Bogota").strip() or "America/Bogota"

    @property
    def timezone(self):
        """Returns the configured time zone as a ZoneInfo object."""
        return ZoneInfo(self.timezone_name)

    @property
    def send_empty_digest(self):
        """Whether to send a short email when there is nothing pending."""
        return os.getenv("SEND_EMPTY_DIGEST", "false").strip().lower() in TRUE_VALUES

    @property
    def upcoming_days(self):
        """Number of days ahead included in the "Próximos días" section."""
        raw = os.getenv("UPCOMING_DAYS", "3").strip()
        try:
            return max(0, int(raw))
        except ValueError:
            return 3

    @property
    def notion_tasks_url(self):
        """Link to the Tareas database shown in the email footer."""
        url = os.getenv("NOTION_TASKS_URL")
        if url:
            return url.strip()
        database_id = (self.notion_database_id or "").replace("-", "")
        return f"https://www.notion.so/{database_id}" if database_id else ""

    @property
    def ses_sender_and_receiver(self):
        """Returns the sender and receiver email addresses."""
        sender = os.getenv("SES_SENDER_EMAIL")
        receiver = os.getenv("SES_RECEIVER_EMAIL")
        return (sender.strip() if sender else None), (
            receiver.strip() if receiver else None
        )

    @property
    def region(self):
        """Returns the AWS region."""
        return os.getenv("AWS_REGION", "us-east-1")

    def validate(self):
        """
        Validates that required environment variables are present.
        Raises ValueError if any required variable is missing.
        """
        required_vars = [
            "NOTION_API_KEY",
            "NOTION_DATABASE_ID",
            "SES_SENDER_EMAIL",
            "SES_RECEIVER_EMAIL",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        try:
            self.timezone
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"Invalid TIMEZONE '{self.timezone_name}': {e}") from e


environment_handler = EnvironmentHandler()
