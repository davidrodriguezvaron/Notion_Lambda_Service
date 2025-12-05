from .logic.function import NotionLambda
from .common.integrations.notion.notion_client import get_notion_client
from .common.logger.logger import get_logger
from .common.environment.environment_handler import environment_handler

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    event: Dict containing the Lambda function event data
    context: Lambda runtime context
    """
    logger.info("Lambda handler started")
    logger.debug(f"Event received: {event}")

    # Validate environment
    try:
        environment_handler.validate()
    except ValueError as e:
        logger.error(f"Environment validation failed: {str(e)}")
        raise e

    try:
        return NotionLambda(get_notion_client()).notion_lambda_function(event, context)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": {"message": f"Error processing request: {str(e)}"},
        }
