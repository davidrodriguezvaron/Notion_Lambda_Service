import os
from dotenv import load_dotenv


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
        return os.getenv("NOTION_DATABASE_FILTER_PROPERTIES", "Notas,Tarea,Fecha")

    def validate(self):
        """
        Validates that required environment variables are present.
        Raises ValueError if any required variable is missing.
        """
        required_vars = []
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )


environment_handler = EnvironmentHandler()
