import unittest
import os
import logging
from unittest.mock import patch
from app.common.logger.logger import get_logger


class TestLogger(unittest.TestCase):

    def setUp(self):
        # Clear environment variables before each test
        if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            del os.environ["AWS_LAMBDA_FUNCTION_NAME"]
        if "LOG_LEVEL" in os.environ:
            del os.environ["LOG_LEVEL"]

    def test_get_logger_local(self):
        """Test logger configuration for local environment"""
        logger = get_logger("test_local")

        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

        # Check formatter
        formatter = logger.handlers[0].formatter
        self.assertIsNotNone(formatter)

    def test_get_logger_lambda(self):
        """Test logger configuration for Lambda environment"""
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "my-function", "ENVIRONMENT": ""}):
            logger = get_logger("test_lambda")

            self.assertEqual(logger.level, logging.INFO)
            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    def test_get_logger_custom_level(self):
        """Test logger configuration with custom log level"""
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            logger = get_logger("test_custom")
            self.assertEqual(logger.level, logging.WARNING)

    def test_get_logger_clears_handlers(self):
        """Test that get_logger clears existing handlers to avoid duplicates"""
        logger1 = get_logger("test_duplicate")
        self.assertEqual(len(logger1.handlers), 1)

        logger2 = get_logger("test_duplicate")
        self.assertEqual(len(logger2.handlers), 1)
        self.assertEqual(logger1, logger2)


if __name__ == "__main__":
    unittest.main()
