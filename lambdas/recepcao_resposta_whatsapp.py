import json
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    mensagem_sns = event['Records'][0]['Sns']['Message']
    dados_aws = json.loads(mensagem_sns)
    dados_whatsapp = json.loads(dados_aws['whatsAppWebhookEntry'])

    mudanca = dados_whatsapp['changes'][0]
    valor = mudanca['value']

    if 'messages' not in valor:
        return {'statusCode': 200, 'body': json.dumps('Evento de status recebido, ignorado.')}

    mensagem = valor['messages'][0]
    numero_remetente = mensagem['from']

    if not numero_remetente.startswith('+'):
        numero_remetente = '+' + numero_remetente

    tipo_mensagem = mensagem['type']
    texto_resposta = mensagem['button']['text'] if tipo_mensagem == 'button' else None

    dynamodb = boto3.resource('dynamodb')
    tabela_interacoes = dynamodb.Table('Tabela-de-Interacoes')

    resposta_busca = tabela_interacoes.query(
        IndexName='indice-por-numero',
        KeyConditionExpression=Key('numero_whatsapp').eq(numero_remetente),
        ScanIndexForward=False,
        Limit=1
    )

    interacoes_encontradas = resposta_busca['Items']
    if len(interacoes_encontradas) == 0:
        return {'statusCode': 200, 'body': json.dumps('Nenhuma interação em aberto encontrada para esse número.')}

    interacao_atual = interacoes_encontradas[0]
    status_atual = interacao_atual['status']
    ID = interacao_atual['ID']
    tarefa_data_atual = interacao_atual['tarefa_data']
    nome_usuario = interacao_atual['nome']

    if status_atual != 'aguardando_resposta':
        return {'statusCode': 200, 'body': json.dumps('Nenhuma ação necessária.')}

    cliente_whatsapp = boto3.client('socialmessaging')

    if texto_resposta == 'Está feito':

        tabela_interacoes.update_item(
            Key={'ID': ID, 'tarefa_data': tarefa_data_atual},
            UpdateExpression='SET #s = :novo_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':novo_status': 'concluido'}
        )

        tabela_tarefas = dynamodb.Table('Tabela-de-Tarefas')
        agora = datetime.now() - timedelta(hours=3)
        hora_atual = agora.strftime("%H:%M")

        dias_semana_map = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
        dia_hoje = dias_semana_map[agora.weekday()]

        resposta_tarefas = tabela_tarefas.query(
            KeyConditionExpression=Key('ID').eq(ID),
            FilterExpression=Key('hora_tarefa').gt(hora_atual) & Attr('dias_semana').contains(dia_hoje)
        )
        proximas_tarefas = resposta_tarefas['Items']

        if len(proximas_tarefas) > 0:
            proxima = proximas_tarefas[0]
            texto_proxima = f"{nome_usuario}, sua próxima atividade é {proxima['tarefa']} às {proxima['hora_tarefa']}."
        else:
            texto_proxima = f"{nome_usuario}, essa era sua última atividade do dia. Bom trabalho!"

        cliente_whatsapp.send_whatsapp_message(
            originationPhoneNumberId='SEU ID DO TELEFONE VINCULADO AQUI',
            metaApiVersion='v20.0',
            message=json.dumps({
                'messaging_product': 'whatsapp', 'to': numero_remetente,
                'type': 'text', 'text': {'body': texto_proxima}
            }).encode('utf-8')
        )

    elif texto_resposta == 'Ainda não fiz':
        tabela_interacoes.update_item(
            Key={'ID': ID, 'tarefa_data': tarefa_data_atual},
            UpdateExpression='SET #s = :novo_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':novo_status': 'nao_feito'}
        )

        cliente_whatsapp.send_whatsapp_message(
            originationPhoneNumberId='SEU ID DO TELEFONE VINCULADO AQUI',
            metaApiVersion='v20.0',
            message=json.dumps({
                'messaging_product': 'whatsapp', 'to': numero_remetente,
                'type': 'text', 'text': {'body': 'Entendido! Anotado como não feito.'}
            }).encode('utf-8')
        )

    elif texto_resposta == 'Preciso de ajuda':
        tabela_interacoes.update_item(
            Key={'ID': ID, 'tarefa_data': tarefa_data_atual},
            UpdateExpression='SET #s = :novo_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':novo_status': 'pediu_ajuda'}
        )

        cliente_whatsapp.send_whatsapp_message(
            originationPhoneNumberId='SEU ID DO TELEFONE VINCULADO AQUI',
            metaApiVersion='v20.0',
            message=json.dumps({
                'messaging_product': 'whatsapp', 'to': numero_remetente,
                'type': 'text', 'text': {'body': 'Entendido! Aguarde até que alguém possa te ajudar.'}
            }).encode('utf-8')
        )

    return {'statusCode': 200, 'body': json.dumps('Interação processada com sucesso.')}
