import unittest
from unittest.mock import patch
from app.common.environment.environment_handler import environment_handler


class TestEnvironmentHandler(unittest.TestCase):
    def test_environment_handler_init(self):
        # Since it's a singleton, we check the existing instance
        self.assertEqual(environment_handler.environment, "LOCAL")

    @patch.dict(
        "os.environ", {"AWS_LAMBDA_FUNCTION_NAME": "test_function", "ENVIRONMENT": ""}
    )
    def test_log_level_lambda_default(self):
        self.assertEqual(environment_handler.log_level, "INFO")

    def test_log_level_local_default(self):
        # Ensure environment is clean
        with patch.dict("os.environ", clear=True):
            self.assertEqual(environment_handler.log_level, "DEBUG")

    @patch.dict("os.environ", {"LOG_LEVEL": "WARNING"})
    def test_log_level_custom(self):
        self.assertEqual(environment_handler.log_level, "WARNING")

    @patch.dict(
        "os.environ",
        {
            "NOTION_API_KEY": "test_api_key",
            "NOTION_DATABASE_ID": "test_database_id",
            "SES_SENDER_EMAIL": "sender@example.com",
            "SES_RECEIVER_EMAIL": "receiver@example.com",
        },
    )
    def test_validate_success(self):
        """Test validate() passes when required variables are present"""
        try:
            environment_handler.validate()
        except ValueError:
            self.fail("validate() raised ValueError unexpectedly")

    def test_validate_with_missing_vars(self):
        """Test validate() raises ValueError when required vars are missing"""
        # Ensure specific vars are missing
        with patch.dict("os.environ", clear=True):
            # We need to re-instantiate or just call validate on the existing one,
            # but os.getenv will look at the patched environ.
            with self.assertRaises(ValueError) as cm:
                environment_handler.validate()

            self.assertIn("Missing required environment variables", str(cm.exception))
            self.assertIn("SES_SENDER_EMAIL", str(cm.exception))
            self.assertIn("NOTION_API_KEY", str(cm.exception))
            self.assertIn("NOTION_DATABASE_ID", str(cm.exception))

    @patch.dict(
        "os.environ",
        {
            "NOTION_API_KEY": "test_api_key",
            "NOTION_DATABASE_ID": "test_database_id",
            "SES_SENDER_EMAIL": "sender@example.com",
            "SES_RECEIVER_EMAIL": "receiver@example.com",
        },
    )
    def test_ses_sender_and_receiver(self):
        self.assertEqual(
            environment_handler.ses_sender_and_receiver,
            ("sender@example.com", "receiver@example.com"),
        )

    def test_new_variables_defaults(self):
        with patch.dict("os.environ", clear=True):
            self.assertEqual(environment_handler.timezone_name, "America/Bogota")
            self.assertEqual(str(environment_handler.timezone), "America/Bogota")
            self.assertFalse(environment_handler.send_empty_digest)
            self.assertEqual(environment_handler.upcoming_days, 3)
            self.assertEqual(environment_handler.notion_tasks_url, "")
            self.assertEqual(
                environment_handler.notion_database_filter_properties,
                "Notas,Tarea,Fecha,Área",
            )

    @patch.dict(
        "os.environ",
        {
            "TIMEZONE": "Europe/Madrid",
            "SEND_EMPTY_DIGEST": "TRUE",
            "UPCOMING_DAYS": "5",
            "NOTION_TASKS_URL": " https://www.notion.so/x ",
        },
    )
    def test_new_variables_custom(self):
        self.assertEqual(environment_handler.timezone_name, "Europe/Madrid")
        self.assertTrue(environment_handler.send_empty_digest)
        self.assertEqual(environment_handler.upcoming_days, 5)
        self.assertEqual(
            environment_handler.notion_tasks_url, "https://www.notion.so/x"
        )

    @patch.dict("os.environ", {"UPCOMING_DAYS": "muchos"})
    def test_upcoming_days_invalid_falls_back(self):
        self.assertEqual(environment_handler.upcoming_days, 3)

    @patch.dict("os.environ", {"UPCOMING_DAYS": "-2"})
    def test_upcoming_days_never_negative(self):
        self.assertEqual(environment_handler.upcoming_days, 0)

    def test_notion_tasks_url_from_database_id(self):
        with patch.dict("os.environ", {"NOTION_DATABASE_ID": "1fab-4158"}, clear=True):
            self.assertEqual(
                environment_handler.notion_tasks_url, "https://www.notion.so/1fab4158"
            )

    @patch.dict(
        "os.environ",
        {
            "SES_SENDER_EMAIL": "a@example.com",
            "SES_RECEIVER_EMAIL": "b@example.com",
            "NOTION_API_KEY": "secret",
            "NOTION_DATABASE_ID": "db",
            "TIMEZONE": "America/Nowhere",
        },
    )
    def test_validate_rejects_invalid_timezone(self):
        with self.assertRaises(ValueError) as cm:
            environment_handler.validate()
        self.assertIn("Invalid TIMEZONE", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
