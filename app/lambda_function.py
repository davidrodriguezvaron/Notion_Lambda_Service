from .logic.function import NotionLambda


def lambda_handler(event, context):
    '''
    event: Dict containing the Lambda function event data
    context: Lambda runtime context
    '''
    # TODO subir el coverage de esta clase al 75% y del environment handler al 75% por lo menos
    # TODO modificar el deploy_all para que falle si el coverage es menor al 75% - excluyendo las clases __init__.py
    # TODO hacer github action
    # TODO - agregar logging dependiendo del environment
    # TODO - agregar test global

    # TODO - verificar que la historia se haya guardado correctamente
    return NotionLambda().notion_lambda_function(event, context)
