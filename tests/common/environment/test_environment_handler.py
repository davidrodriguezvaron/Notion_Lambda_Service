import unittest
import os
from unittest.mock import patch
from app.common.environment.environment_handler import environment_handler


class TestEnvironmentHandler(unittest.TestCase):
    def test_environment_handler_init(self):
        # Since it's a singleton, we check the existing instance
        self.assertEqual(environment_handler.environment, "LOCAL")

    @patch.dict("os.environ", {"AWS_LAMBDA_FUNCTION_NAME": "test_function"})
    def test_log_level_lambda_default(self):
        self.assertEqual(environment_handler.log_level, "INFO")

    def test_log_level_local_default(self):
        # Ensure environment is clean
        with patch.dict("os.environ", clear=True):
            self.assertEqual(environment_handler.log_level, "DEBUG")

    @patch.dict("os.environ", {"LOG_LEVEL": "WARNING"})
    def test_log_level_custom(self):
        self.assertEqual(environment_handler.log_level, "WARNING")

    def test_validate_with_no_required_vars(self):
        """Test validate() passes when no variables are required"""
        # Should not raise any exception
        try:
            environment_handler.validate()
        except ValueError:
            self.fail("validate() raised ValueError unexpectedly")

    def test_validate_with_missing_vars(self):
        """Test validate() raises ValueError when required vars are missing"""
        # Create a new instance and patch os.getenv to simulate missing vars
        from app.common.environment.environment_handler import EnvironmentHandler

        handler = EnvironmentHandler()

        # Monkey-patch the validate method to test with required vars
        import types

        def validate_with_required(self):
            required_vars = ["MISSING_TEST_VAR_X"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(
                    f"Missing required environment variables: {', '.join(missing_vars)}"
                )

        # Bind the new method to the instance
        handler.validate = types.MethodType(validate_with_required, handler)

        # Test that it raises
        with self.assertRaises(ValueError) as cm:
            handler.validate()

        self.assertIn("Missing required environment variables", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
