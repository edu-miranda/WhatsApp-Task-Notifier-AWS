import json
import boto3
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'SEU ID DE DOMINIO AQUI',
                'Access-Control-Allow-Headers': 'Authorization,Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': ''
        }


    parametros = event.get('queryStringParameters') or {}
    ID = parametros.get('ID')


    if not ID:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps('Parâmetro ID é obrigatório.')
        }


    dynamodb = boto3.resource('dynamodb')
    tabela = dynamodb.Table('Tabela-de-Interacoes')


    resposta = tabela.query(
        KeyConditionExpression=Key('ID').eq(ID)
    )


    itens = resposta['Items']
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(itens)
    }
