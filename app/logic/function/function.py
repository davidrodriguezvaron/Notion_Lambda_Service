from app.common.environment.environment_handler import environment_handler
from app.common.logger.logger import get_logger

logger = get_logger(__name__)


class NotionLambda:
    """
    Defines a Notion Lambda function handler to handle incoming events.
    """

    def __init__(self):
        self.env_handler = environment_handler

    def notion_lambda_function(self, event, context):
        """
        Main handler for the Notion Lambda function.
        event: Dict containing the Lambda function event data
        context: Lambda runtime context
        """
        logger.info(f"Processing request in {self.env_handler.environment} environment")

        # TODO - Añadir recursos de tracing y monitoring dependiendo del entorno
        # CloudWatch para prod, y en local quizás algo más simple

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
