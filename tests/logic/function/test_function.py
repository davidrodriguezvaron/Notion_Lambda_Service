import unittest
from unittest.mock import Mock, patch
from app.logic.function.function import NotionLambda


class TestNotionLambda(unittest.TestCase):

    @patch('app.logic.function.function.EnvironmentHandler')
    def setUp(self, mock_env_handler):
        """Set up test fixtures"""
        self.mock_env_handler = mock_env_handler
        self.notion_lambda = NotionLambda()

    @patch('app.logic.function.function.EnvironmentHandler')
    def test_init_creates_environment_handler(self, mock_env_handler):
        """Test that __init__ instantiates EnvironmentHandler"""
        notion_lambda = NotionLambda()
        mock_env_handler.assert_called_once()
        self.assertIsNotNone(notion_lambda.env_handler)

    def test_notion_lambda_function_returns_success_response(self):
        """Test that notion_lambda_function returns a successful response"""
        event = {}
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertEqual(response['statusCode'], 200)

    def test_notion_lambda_function_has_correct_headers(self):
        """Test that response has correct Content-Type header"""
        event = {}
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertIn('headers', response)
        self.assertEqual(response['headers']
                         ['Content-Type'], 'application/json')

    def test_notion_lambda_function_has_correct_body(self):
        """Test that response body contains success message"""
        event = {}
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertIn('body', response)
        self.assertIn(
            'Process executed successfully from NotionLambda', response['body']['message'])

    def test_notion_lambda_function_with_none_event(self):
        """Test function handles None event"""
        event = None
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertEqual(response['statusCode'], 200)

    def test_notion_lambda_function_with_none_context(self):
        """Test function handles None context"""
        event = {}
        context = None

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertEqual(response['statusCode'], 200)

    def test_notion_lambda_function_with_populated_event(self):
        """Test function handles event with data"""
        event = {
            'key1': 'value1',
            'key2': 'value2'
        }
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertEqual(response['statusCode'], 200)
        self.assertIsInstance(response, dict)

    def test_notion_lambda_function_response_structure(self):
        """Test that response has all required fields"""
        event = {}
        context = Mock()

        response = self.notion_lambda.notion_lambda_function(event, context)

        self.assertIn('statusCode', response)
        self.assertIn('headers', response)
        self.assertIn('body', response)


if __name__ == '__main__':
    unittest.main()
