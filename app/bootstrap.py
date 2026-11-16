"""
Composition root: the only place that knows the concrete classes and wires
them together from the settings.
"""

import boto3

from app.application.clock import ZonedClock
from app.application.reopen_recurring_tasks import ReopenRecurringTasks
from app.application.send_daily_digest import DigestOptions, SendDailyDigest
from app.config.settings import Settings
from app.infrastructure.notion.client import NotionClient
from app.infrastructure.notion.task_repository import NotionTaskRepository
from app.infrastructure.ses.email_sender import SesEmailSender
from app.presentation.email.composer import DigestEmailComposer
from app.presentation.email.html_renderer import PaperHtmlRenderer
from app.presentation.email.text_renderer import PlainTextRenderer


def build_composer(notion_tasks_url: str) -> DigestEmailComposer:
    return DigestEmailComposer(
        html_renderer=PaperHtmlRenderer(notion_tasks_url),
        text_renderer=PlainTextRenderer(notion_tasks_url),
    )


def build_send_daily_digest(settings: Settings) -> SendDailyDigest:
    repository = NotionTaskRepository(
        client=NotionClient(
            api_key=settings.notion_api_key,
            version=settings.notion_version,
            base_url=settings.notion_base_url,
        ),
        database_id=settings.notion_database_id,
        filter_properties=settings.notion_filter_properties,
    )
    sender = SesEmailSender(
        ses_client=boto3.client("ses", region_name=settings.aws_region),
        sender=settings.ses_sender,
        recipients=[settings.ses_receiver],
    )
    options = DigestOptions(
        timezone=settings.timezone,
        upcoming_days=settings.upcoming_days,
        send_empty_digest=settings.send_empty_digest,
    )
    return SendDailyDigest(
        repository=repository,
        reopen_recurring=ReopenRecurringTasks(repository),
        composer=build_composer(settings.notion_tasks_url),
        sender=sender,
        clock=ZonedClock(options.timezone),
        options=options,
    )
