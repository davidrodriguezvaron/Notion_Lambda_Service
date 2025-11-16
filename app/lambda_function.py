from .logic.function import NotionLambda
def lambda_handler(event, context):
        '''
            event: Dict containing the Lambda function event data
            context: Lambda runtime context
        '''
        return NotionLambda().notion_lambda_function(event, context)
