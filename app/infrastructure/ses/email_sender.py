"""Sends the digest through AWS SES."""

from typing import Any, Sequence

from app.application.ports import EmailMessage


class SesEmailSender:
    def __init__(self, ses_client: Any, sender: str, recipients: Sequence[str]):
        self._client = ses_client
        self._sender = sender
        self._recipients = list(recipients)

    def send(self, message: EmailMessage) -> None:
        """Multipart email: HTML plus a real plain text alternative."""
        self._client.send_email(
            Source=self._sender,
            Destination={"ToAddresses": self._recipients},
            Message={
                "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": message.html, "Charset": "UTF-8"},
                    "Text": {"Data": message.text, "Charset": "UTF-8"},
                },
            },
        )
