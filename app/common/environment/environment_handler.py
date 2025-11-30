import os
from dotenv import load_dotenv


class EnvironmentHandler:
    def __init__(self):
        if os.path.exists(".env"):
            load_dotenv()

    @property
    def environment(self):
        """Returns the current environment (LOCAL, PRODUCTION, etc)."""
        return os.getenv("ENVIRONMENT", "LOCAL")

    @property
    def log_level(self):
        """Returns the configured log level based on environment."""
        default_level = "INFO" if self.environment == "PRODUCTION" else "DEBUG"
        return os.getenv("LOG_LEVEL", default_level)

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
