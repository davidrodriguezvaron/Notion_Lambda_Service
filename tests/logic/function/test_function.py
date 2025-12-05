import unittest
from unittest.mock import Mock, patch
from app.logic.function.function import NotionLambda


class TestNotionLambda(unittest.TestCase):

    @patch("app.logic.function.function.SesClient")
    @patch("app.logic.function.function.environment_handler")
    def setUp(self, mock_env_handler, mock_ses_client_class):
        """Set up test fixtures"""
        self.mock_env_handler = mock_env_handler
        # Configure env handler mocking
        self.mock_env_handler.ses_sender_and_receiver = (
            "sender@example.com",
            "receiver@example.com",
        )
        self.mock_env_handler.notion_database_id = "test_db_id"
        self.mock_env_handler.environment = "TEST"
        self.mock_env_handler.notion_database_filter_properties = "test_props"

        self.mock_ses_client = mock_ses_client_class.return_value

        self.mock_notion_client = Mock()
        # Configure the mock to return a proper response structure
        self.mock_notion_client.post.return_value = {
            "results": [{"id": "1", "properties": {}}]
        }
        self.notion_lambda = NotionLambda(self.mock_notion_client)

    @patch("app.logic.function.function.environment_handler")
    def test_init_uses_environment_handler(self, mock_env_handler_instance):
        """Test that __init__ uses the singleton EnvironmentHandler"""
        # We need to ensure that the NotionLambda class uses the mocked instance
        # The patch above replaces the 'environment_handler' imported in 'app.logic.function.function'
        mock_client = Mock()
        notion_lambda = NotionLambda(mock_client)
        self.assertEqual(notion_lambda.env_handler, mock_env_handler_instance)
        self.assertEqual(notion_lambda.notion_client, mock_client)

    def test_notion_lambda_function_returns_success_response(self):
        """Test that notion_lambda_function returns a successful response"""
        response = self.notion_lambda.notion_lambda_function()

        self.assertEqual(response["statusCode"], 200)

    def test_notion_lambda_function_has_correct_headers(self):
        """Test that response has correct Content-Type header"""
        response = self.notion_lambda.notion_lambda_function()

        self.assertIn("headers", response)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")

    def test_notion_lambda_function_has_correct_body(self):
        """Test that response body contains success message"""
        response = self.notion_lambda.notion_lambda_function()

        self.assertIn("body", response)
        self.assertIn(
            "Process executed successfully from NotionLambda",
            response["body"]["message"],
        )

    def test_notion_lambda_function_response_structure(self):
        """Test that response has all required fields"""
        response = self.notion_lambda.notion_lambda_function()

        self.assertIn("statusCode", response)
        self.assertIn("headers", response)
        self.assertIn("body", response)

    def test_notion_lambda_function_sends_email(self):
        """Test that email is sent using SesClient"""
        self.notion_lambda.notion_lambda_function()

        self.mock_ses_client.send_email.assert_called_once()
        _, kwargs = self.mock_ses_client.send_email.call_args
        self.assertEqual(kwargs["sender"], "sender@example.com")
        self.assertEqual(kwargs["receiver"], ["receiver@example.com"])
        self.assertEqual(kwargs["subject"], "Task List: 1 Item Pending")
        self.assertIsInstance(kwargs["body"], str)


if __name__ == "__main__":
    unittest.main()
