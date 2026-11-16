import unittest
from unittest.mock import MagicMock

from app.application.ports import EmailMessage
from app.infrastructure.ses.email_sender import SesEmailSender


class TestSesEmailSender(unittest.TestCase):
    def test_sends_html_and_plain_text(self):
        client = MagicMock()
        sender = SesEmailSender(client, "from@example.com", ["to@example.com"])

        sender.send(
            EmailMessage(subject="Tareas: 1 hoy", html="<p>Hola</p>", text="Hola")
        )

        client.send_email.assert_called_once_with(
            Source="from@example.com",
            Destination={"ToAddresses": ["to@example.com"]},
            Message={
                "Subject": {"Data": "Tareas: 1 hoy", "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": "<p>Hola</p>", "Charset": "UTF-8"},
                    "Text": {"Data": "Hola", "Charset": "UTF-8"},
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
