import unittest
from unittest.mock import Mock, patch
from app.lambda_function import lambda_handler


class TestLambdaFunction(unittest.TestCase):

    @patch("app.lambda_function.get_notion_client")
    @patch("app.lambda_function.NotionLambda")
    def test_lambda_handler(self, mock_notion_lambda_class, mock_get_notion_client):
        # Setup
        mock_client = Mock()
        mock_get_notion_client.return_value = mock_client
        mock_instance = mock_notion_lambda_class.return_value
        expected_response = {"statusCode": 200, "body": "Success"}
        mock_instance.notion_lambda_function.return_value = expected_response

        event = {}
        context = Mock()

        # Execute
        response = lambda_handler(event, context)

        # Verify
        mock_get_notion_client.assert_called_once()
        mock_notion_lambda_class.assert_called_once_with(mock_client)
        mock_instance.notion_lambda_function.assert_called_once_with()
        self.assertEqual(response, expected_response)

    @patch("app.lambda_function.environment_handler")
    def test_lambda_handler_validation_failure(self, mock_env_handler):
        """Test lambda_handler when environment validation fails"""
        # Setup
        mock_env_handler.validate.side_effect = ValueError("Missing required vars")
        event = {}
        context = Mock()

        # Execute and verify
        with self.assertRaises(ValueError) as cm:
            lambda_handler(event, context)

        self.assertIn("Missing required vars", str(cm.exception))
        mock_env_handler.validate.assert_called_once()

    @patch("app.lambda_function.get_notion_client")
    @patch("app.lambda_function.NotionLambda")
    def test_lambda_handler_exception_handling(
        self, mock_notion_lambda_class, mock_get_notion_client
    ):
        """Test lambda_handler re-raises exceptions to mark Lambda as failed"""
        # Setup
        mock_client = Mock()
        mock_get_notion_client.return_value = mock_client
        mock_instance = mock_notion_lambda_class.return_value
        mock_instance.notion_lambda_function.side_effect = Exception("Test error")

        event = {}
        context = Mock()

        # Execute and verify exception is re-raised
        with self.assertRaises(Exception) as cm:
            lambda_handler(event, context)

        self.assertIn("Test error", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
