import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta

def lambda_handler(event, context):
    agora = datetime.now() - timedelta(hours=3)
    hora_atual = agora.strftime("%H:%M")
    hora_limite_inferior = (agora - timedelta(minutes=4)).strftime("%H:%M")

    dias_semana_map = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
    dia_hoje = dias_semana_map[agora.weekday()]

    dynamodb = boto3.resource('dynamodb')
    tabela = dynamodb.Table('Tabela-de-Tarefas')

    resposta = tabela.query(
        IndexName='indice-por-horario',
        KeyConditionExpression=Key('isg_particao').eq('TAREFA') & Key('hora_tarefa').between(hora_limite_inferior, hora_atual),
        FilterExpression=Attr('dias_semana').contains(dia_hoje)
    )

    itens = resposta['Items']

    if len(itens) == 0:
        return {'statusCode': 200, 'body': json.dumps('Nenhuma tarefa neste horário.')}

    for item in itens:
        nome = item['nome']
        tarefa = item['tarefa']
        numero = item['numero_whatsapp']
        ID = item['ID']
        cliente_whatsapp = boto3.client('socialmessaging')

        resposta_envio = cliente_whatsapp.send_whatsapp_message(
            originationPhoneNumberId='SEU ID DE TELEFONE VINCULADO AQUI',
            metaApiVersion='v20.0',
            message=json.dumps({
                'messaging_product': 'whatsapp',
                'to': numero,
                'type': 'template',
                'template': {
                    'name': 'notificacao_tarefa',
                    'language': {'code': 'pt_BR'},
                    'components': [
                        {
                            'type': 'body',
                            'parameters': [
                                {'type': 'text', 'text': nome},
                                {'type': 'text', 'text': tarefa}
                            ]
                        }
                    ]
                }
            }).encode('utf-8')
        )
        print(f"Resposta do envio: {resposta_envio}")

        tabela_interacoes = dynamodb.Table('Tabela-de-Interacoes')
        chave_composta = f"{agora.isoformat()}#{tarefa}"

        tabela_interacoes.put_item(
            Item={
                'ID': ID,
                'tarefa_data': chave_composta,
                'status': 'aguardando_resposta',
                'nome': nome,
                'tarefa': tarefa,
                'numero_whatsapp': numero,
            }
        )

    return {'statusCode': 200, 'body': json.dumps(f'{len(itens)} notificação(ões) enviada(s) com sucesso.')}
