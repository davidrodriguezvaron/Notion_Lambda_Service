class NotionLambda:
    '''
    Defines a Notion Lambda function handler to handle incoming events.
    '''
    def notion_lambda_function(self, event, context):
        return {
            "statusCode": 200,
            "message": "Proccess executed successfully"
        }
