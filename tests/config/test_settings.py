import os
import tempfile
import unittest
from unittest.mock import patch

from app.config.settings import ConfigurationError, Settings
from tests.fakes import BASE_ENV


def settings(**overrides):
    return Settings.from_env(dict(BASE_ENV, **overrides))


class TestSettings(unittest.TestCase):
    def test_defaults(self):
        s = settings()
        self.assertEqual(s.environment, "LOCAL")
        self.assertEqual(s.log_level, "DEBUG")
        self.assertEqual(s.notion_version, "2026-03-11")
        self.assertEqual(s.notion_base_url, "https://api.notion.com/v1")
        self.assertEqual(
            s.notion_filter_properties, ("Notas", "Tarea", "Fecha", "Área")
        )
        self.assertEqual(s.notion_tasks_url, "https://www.notion.so/1fab4158")
        self.assertEqual(s.aws_region, "us-east-1")
        self.assertEqual(str(s.timezone), "America/Bogota")
        self.assertEqual(s.upcoming_days, 3)
        self.assertFalse(s.send_empty_digest)

    def test_custom_values_are_trimmed(self):
        s = settings(
            TIMEZONE="Europe/Madrid",
            SEND_EMPTY_DIGEST="TRUE",
            UPCOMING_DAYS="5",
            NOTION_TASKS_URL=" https://www.notion.so/x ",
            NOTION_DATABASE_FILTER_PROPERTIES="Tarea, ,Fecha",
            SES_SENDER_EMAIL=" a@example.com ",
        )
        self.assertEqual(str(s.timezone), "Europe/Madrid")
        self.assertTrue(s.send_empty_digest)
        self.assertEqual(s.upcoming_days, 5)
        self.assertEqual(s.notion_tasks_url, "https://www.notion.so/x")
        self.assertEqual(s.notion_filter_properties, ("Tarea", "Fecha"))
        self.assertEqual(s.ses_sender, "a@example.com")

    def test_environment_and_log_level(self):
        self.assertEqual(
            settings(AWS_LAMBDA_FUNCTION_NAME="fn").environment, "PRODUCTION"
        )
        self.assertEqual(settings(AWS_LAMBDA_FUNCTION_NAME="fn").log_level, "INFO")
        self.assertEqual(settings(ENVIRONMENT="TEST").environment, "TEST")
        self.assertEqual(settings(LOG_LEVEL="WARNING").log_level, "WARNING")
        self.assertEqual(settings(LOG_LEVEL=" info ").log_level, "INFO")

    def test_invalid_log_level(self):
        with self.assertRaises(ConfigurationError):
            settings(LOG_LEVEL="verbose")

    def test_upcoming_days_fallbacks(self):
        self.assertEqual(settings(UPCOMING_DAYS="muchos").upcoming_days, 3)
        self.assertEqual(settings(UPCOMING_DAYS="-2").upcoming_days, 0)

    def test_missing_required_variables(self):
        with self.assertRaises(ConfigurationError) as cm:
            Settings.from_env({"SES_SENDER_EMAIL": "a@example.com"})
        message = str(cm.exception)
        self.assertIn("Missing required environment variables", message)
        self.assertIn("NOTION_API_KEY", message)
        self.assertIn("NOTION_DATA_SOURCE_ID", message)
        self.assertNotIn("SES_SENDER_EMAIL", message)

    def test_data_source_id_is_read_and_trimmed(self):
        s = settings(NOTION_DATA_SOURCE_ID=" ad1c-51ed ")
        self.assertEqual(s.notion_data_source_id, "ad1c-51ed")

    def test_invalid_timezone(self):
        with self.assertRaises(ConfigurationError) as cm:
            settings(TIMEZONE="America/Nowhere")
        self.assertIn("Invalid TIMEZONE", str(cm.exception))

    def test_configuration_error_is_a_value_error(self):
        self.assertTrue(issubclass(ConfigurationError, ValueError))

    def test_reads_os_environ_and_dotenv(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, ".env"), "w") as f:
                f.write("UPCOMING_DAYS=6\n")
            cwd = os.getcwd()
            os.chdir(folder)
            try:
                with patch.dict(os.environ, BASE_ENV, clear=True):
                    s = Settings.from_env()
            finally:
                os.chdir(cwd)
        self.assertEqual(s.upcoming_days, 6)


if __name__ == "__main__":
    unittest.main()
