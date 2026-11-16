import json
from app.common.adapter.email_adapter import EmailAdapter
from app.common.integrations.ses.ses_client import SesClient
from app.common.environment.environment_handler import environment_handler
from app.common.integrations.notion.task_repository import TaskRepository
from app.common.logger.logger import get_logger
from app.common.utils.dates import today_in
from app.logic.recurrence.recurrence_service import RecurrenceService

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
        self.recurrence_service = RecurrenceService(self.task_repository)
        self.email_adapter = EmailAdapter(
            tz=self.env_handler.timezone,
            notion_tasks_url=self.env_handler.notion_tasks_url,
        )
        self.ses_client = SesClient()

    def notion_lambda_function(self, now=None):
        """
        Main flow:
        1. Reopen recurring tasks marked as Done (idempotent).
        2. Read pending tasks up to today + UPCOMING_DAYS.
        3. Send the digest (or skip it when there is nothing to report).

        Args:
            now: Optional aware datetime to override the clock (tests).
        """
        env = self.env_handler
        logger.info(f"Processing request in {env.environment} environment")
        today = today_in(env.timezone, now)
        upcoming_days = env.upcoming_days
        logger.info(f"Today in {env.timezone_name}: {today.isoformat()}")

        recurrence = self.recurrence_service.process()

        tasks = self.task_repository.get_pending_tasks(today, upcoming_days)
        logger.info(f"Retrieved {len(tasks)} pending tasks")
        logger.debug(f"Tasks:\n{json.dumps(tasks, indent=2, ensure_ascii=False)}")

        content = self.email_adapter.build_digest(
            tasks,
            today,
            upcoming_days,
            rescheduled=recurrence.rescheduled,
            warnings=recurrence.warnings,
        )
        sections = content.sections
        nothing_pending = sections.total == 0

        if nothing_pending and not env.send_empty_digest:
            message = "Nothing pending; email skipped (SEND_EMPTY_DIGEST=false)."
            email_sent = False
        else:
            sender, receiver = env.ses_sender_and_receiver
            self.ses_client.send_email(
                sender=sender,
                receiver=[receiver],
                subject=content.subject,
                body=content.html,
                text_body=content.text,
            )
            message = f"Email sent: {content.subject}"
            email_sent = True
        logger.info(message)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "message": "Process executed successfully from NotionLambda"
                + f" in {env.environment} environment. {message}",
                "email_sent": email_sent,
                "tasks": sections.total,
                "rescheduled": len(recurrence.rescheduled),
            },
        }
