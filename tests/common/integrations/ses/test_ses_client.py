import unittest
from unittest.mock import MagicMock, patch
from app.common.integrations.ses.ses_client import SesClient


class TestSesClient(unittest.TestCase):
    @patch("app.common.integrations.ses.ses_client.boto3")
    def test_init(self, mock_boto3):
        # Setup mock for environment_handler if needed, but defaults should work
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        client = SesClient()

        # Check if boto3.client was called with correct arguments
        # Note: environment_handler.region defaults to "us-east-1"
        mock_boto3.client.assert_called_once_with("ses", region_name="us-east-1")
        self.assertEqual(client.client, mock_client)

    @patch("app.common.integrations.ses.ses_client.boto3")
    def test_send_email(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        client = SesClient()
        sender = "sender@example.com"
        receiver = ["receiver@example.com"]
        subject = "Test Subject"
        body = "<p>Test Body</p>"

        client.send_email(sender, receiver, subject, body)

        mock_client.send_email.assert_called_once_with(
            Source=sender,
            Destination={"ToAddresses": receiver},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": body, "Charset": "UTF-8"},
                    "Text": {
                        "Data": "Your email client does not support HTML.",
                        "Charset": "UTF-8",
                    },
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
