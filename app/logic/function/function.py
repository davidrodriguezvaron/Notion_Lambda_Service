import json
from app.common.adapter.email_adapter import EmailAdapter
from app.common.integrations.ses.ses_client import SesClient
from app.common.environment.environment_handler import environment_handler
from app.common.integrations.notion.task_repository import TaskRepository
from app.common.logger.logger import get_logger


logger = get_logger(__name__)


class NotionLambda:
    """
    Defines a Notion Lambda function handler to handle incoming events.
    """

    def __init__(self, notion_client):
        self.notion_client = notion_client
        self.env_handler = environment_handler
        self.task_repository = TaskRepository(
            notion_client,
            self.env_handler.notion_database_id,
            self.env_handler.notion_database_filter_properties,
        )
        self.email_adapter = EmailAdapter()
        self.ses_client = SesClient()

    def notion_lambda_function(self):
        """
        Main handler for the Notion Lambda function.
        event: Dict containing the Lambda function event data
        context: Lambda runtime context
        """
        logger.info(f"Processing request in {self.env_handler.environment} environment")

        # Getting tasks from Notion API
        tasks = self.task_repository.get_pending_tasks()

        logger.debug(f"Retrieved {len(tasks)} pending tasks")
        logger.info(f"Tasks:\n{json.dumps(tasks, indent=2, ensure_ascii=False)}")

        # Convert tasks to email format
        subject, email_content = self.email_adapter.convert_to_email_format(tasks)
        sender, receiver = self.env_handler.ses_sender_and_receiver
        self.ses_client.send_email(
            sender=sender,
            receiver=[receiver],
            subject=subject,
            body=email_content,
        )

        response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "message": "Process executed successfully from NotionLambda"
                + f" in {self.env_handler.environment} environment."
            },
        }
        logger.info("Request processed successfully")
        return response
