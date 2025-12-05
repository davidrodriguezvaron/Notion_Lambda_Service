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

    @patch.dict(
        "os.environ",
        {
            "SES_SENDER_EMAIL": "sender@example.com",
            "SES_RECEIVER_EMAIL": "receiver@example.com",
        },
    )
    def test_ses_sender_and_receiver(self):
        self.assertEqual(
            environment_handler.ses_sender_and_receiver,
            ("sender@example.com", "receiver@example.com"),
        )


if __name__ == "__main__":
    unittest.main()
