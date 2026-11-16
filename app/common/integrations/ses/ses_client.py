import boto3
from app.common.environment.environment_handler import environment_handler


class SesClient:
    def __init__(self):
        self.client = boto3.client("ses", region_name=environment_handler.region)

    def send_email(self, sender, receiver, subject, body, text_body):
        """
        Sends a multipart email: HTML plus a real plain text alternative.
        """
        self.client.send_email(
            Source=sender,
            Destination={"ToAddresses": receiver},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )
