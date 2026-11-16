"""AWS Lambda entry point: load settings, run the daily digest, answer."""

import logging

from app.application.send_daily_digest import DigestResult
from app.bootstrap import build_send_daily_digest
from app.config.settings import Settings
from app.infrastructure.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Args:
        event: EventBridge event (unused).
        context: Lambda runtime context (unused).

    Errors are logged and re-raised so the invocation is marked as failed.
    """
    try:
        settings = Settings.from_env()
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        raise

    configure_logging(settings.log_level)
    logger.info("Lambda handler started")
    logger.debug(f"Event received: {event}")
    logger.info(f"Processing request in {settings.environment} environment")

    try:
        result = build_send_daily_digest(settings).execute()
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise
    return to_response(result, settings.environment)


def to_response(result: DigestResult, environment: str) -> dict:
    if result.email_sent:
        outcome = f"Email sent: {result.subject}"
    else:
        outcome = "Nothing pending; email skipped (SEND_EMPTY_DIGEST=false)."
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "message": "Process executed successfully from NotionLambda"
            + f" in {environment} environment. {outcome}",
            "email_sent": result.email_sent,
            "tasks": result.task_count,
            "rescheduled": result.rescheduled_count,
        },
    }
