from app.logic.environment.environment_handler import EnvironmentHandler


class NotionLambda:
    '''
    Defines a Notion Lambda function handler to handle incoming events.
    '''

    def __init__(self):
        self.env_handler = EnvironmentHandler()

    def notion_lambda_function(self, event, context):
        '''
        Main handler for the Notion Lambda function.
        event: Dict containing the Lambda function event data
        context: Lambda runtime context
        '''
        # TODO - Creater factory pattern to handle different logging, print for local and cloudwatch for prod, depending on environment
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {"message": "Process executed successfully from NotionLambda" + f" in {self.env_handler.environment} environment."}
        }
