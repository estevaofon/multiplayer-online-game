#!/usr/bin/env python3
"""
Servidor WebSocket para Jogo Multiplayer
AWS Lambda + DynamoDB + API Gateway WebSocket
"""

import json
import boto3
import time
import uuid
import os
from typing import Dict, Any
from botocore.exceptions import ClientError


# Configurações
TABLE_NAME = os.environ.get("TABLE_NAME", "WebSocketConnections")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
API_GATEWAY_ENDPOINT = os.environ.get("API_GATEWAY_ENDPOINT")

# Clientes AWS
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
connections_table = dynamodb.Table(TABLE_NAME)


def get_api_gateway_client(domain_name, stage):
    """Cria cliente para enviar mensagens WebSocket"""
    endpoint_url = API_GATEWAY_ENDPOINT
    return boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url, region_name=AWS_REGION)


def lambda_handler(event, context):
    """
    Função principal para processar eventos WebSocket
    """
    try:
        print(f"📨 Evento recebido: {json.dumps(event, default=str)}")

        # Obtém informações da conexão
        connection_id = event["requestContext"]["connectionId"]
        domain_name = event["requestContext"]["domainName"]
        stage = event["requestContext"]["stage"]
        route_key = event["requestContext"]["routeKey"]

        print(f"🔌 Processando {route_key} para conexão {connection_id}")

        # Cria cliente para envio de mensagens
        api_gateway_client = get_api_gateway_client(domain_name, stage)

        # Processa diferentes tipos de eventos
        if route_key == "$connect":
            return handle_connect(connection_id)
        elif route_key == "$disconnect":
            return handle_disconnect(connection_id, api_gateway_client)
        elif route_key == "$default":
            # Mensagem customizada
            body = json.loads(event.get("body", "{}"))
            return handle_message(connection_id, body, api_gateway_client)
        else:
            print(f"❌ Rota não reconhecida: {route_key}")
            return {"statusCode": 400, "body": "Rota não reconhecida"}

    except Exception as e:
        print(f"❌ Erro no lambda_handler: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": f"Erro interno: {str(e)}"}


def handle_connect(connection_id: str):
    """
    Processa nova conexão WebSocket
    """
    try:
        print(f"🆕 Nova conexão: {connection_id}")

        # Registra conexão no DynamoDB
        connections_table.put_item(
            Item={
                "connection_id": connection_id,
                "connected_at": int(time.time()),
                "player_id": None,  # Será definido quando o jogador entrar
                "last_activity": int(time.time()),
                "expires_at": int(time.time()) + 3600,  # TTL de 1 hora
            }
        )

        print(f"✅ Conexão {connection_id} registrada no DynamoDB")
        return {"statusCode": 200, "body": "Conectado"}

    except Exception as e:
        print(f"❌ Erro ao conectar {connection_id}: {str(e)}")
        return {"statusCode": 500, "body": f"Erro na conexão: {str(e)}"}


def handle_disconnect(connection_id: str, api_gateway_client):
    """
    Processa desconexão WebSocket
    """
    try:
        print(f"👋 Desconexão: {connection_id}")

        # Obtém dados da conexão antes de remover
        player_id = None
        try:
            response = connections_table.get_item(Key={"connection_id": connection_id})
            connection_data = response.get("Item", {})
            player_id = connection_data.get("player_id")
            print(f"🔍 Player ID encontrado: {player_id}")
        except Exception as e:
            print(f"⚠️ Erro ao obter dados da conexão: {e}")

        # Remove conexão do DynamoDB
        try:
            connections_table.delete_item(Key={"connection_id": connection_id})
            print(f"🗑️ Conexão {connection_id} removida do DynamoDB")
        except Exception as e:
            print(f"⚠️ Erro ao remover conexão: {e}")

        # Notifica outros jogadores se havia um player_id
        if player_id:
            print(f"📢 Notificando saída do jogador {player_id}")
            broadcast_message(api_gateway_client, {"type": "player_left", "player_id": player_id, "timestamp": int(time.time())}, exclude_connection=connection_id)

        return {"statusCode": 200, "body": "Desconectado"}

    except Exception as e:
        print(f"❌ Erro ao desconectar {connection_id}: {str(e)}")
        return {"statusCode": 500, "body": f"Erro na desconexão: {str(e)}"}


def handle_message(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa mensagens recebidas via WebSocket
    """
    try:
        action = message.get("action", "unknown")
        print(f"🎯 Ação recebida: {action} de {connection_id}")

        if action == "join":
            return handle_join_game(connection_id, message, api_gateway_client)
        elif action == "update":
            return handle_update_position(connection_id, message, api_gateway_client)
        elif action == "leave":
            return handle_leave_game(connection_id, message, api_gateway_client)
        elif action == "ping":
            return handle_ping(connection_id, api_gateway_client)
        else:
            print(f"❌ Ação desconhecida: {action}")
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": f"Ação desconhecida: {action}"})
            return {"statusCode": 400, "body": "Ação desconhecida"}

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": f"Erro no processamento: {str(e)}"}


def handle_join_game(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa entrada de jogador no jogo
    """
    try:
        player_id = message.get("player_id")
        x = message.get("x", 400)
        y = message.get("y", 300)

        if not player_id:
            player_id = str(uuid.uuid4())[:8]

        print(f"🎮 Jogador {player_id} entrando no jogo na posição ({x}, {y})")

        # Cores disponíveis para jogadores
        colors = [
            [255, 100, 100],  # Vermelho claro
            [100, 255, 100],  # Verde claro
            [100, 100, 255],  # Azul claro
            [255, 255, 100],  # Amarelo
            [255, 100, 255],  # Magenta
            [100, 255, 255],  # Ciano
            [255, 150, 100],  # Laranja
            [150, 100, 255],  # Roxo
        ]

        active_players = get_active_players()
        used_colors = [player.get("color", []) for player in active_players.values()]

        # Escolhe primeira cor disponível
        player_color = colors[0]  # Padrão
        for color in colors:
            if color not in used_colors:
                player_color = color
                break

        print(f"🎨 Cor escolhida para {player_id}: {player_color}")

        # Atualiza conexão com dados do jogador
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET player_id = :pid, x = :x, y = :y, color = :color, last_activity = :activity, expires_at = :expires",
            ExpressionAttributeValues={
                ":pid": player_id,
                ":x": x,
                ":y": y,
                ":color": player_color,
                ":activity": int(time.time()),
                ":expires": int(time.time()) + 3600,  # TTL de 1 hora
            },
        )

        print(f"💾 Dados do jogador {player_id} salvos no DynamoDB")

        # Envia confirmação para o jogador
        send_message_to_connection(api_gateway_client, connection_id, {"type": "player_joined", "player_id": player_id, "color": player_color, "x": x, "y": y})

        # Envia estado atual do jogo para o novo jogador
        if active_players:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "game_state", "players": active_players})
            print(f"📊 Estado do jogo enviado para {player_id}")

        # Notifica outros jogadores
        broadcast_message(api_gateway_client, {"type": "player_joined", "player_id": player_id, "color": player_color, "x": x, "y": y}, exclude_connection=connection_id)

        print(f"✅ Jogador {player_id} entrou no jogo com sucesso")
        return {"statusCode": 200, "body": "Entrou no jogo"}

    except Exception as e:
        print(f"❌ Erro ao entrar no jogo: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"statusCode": 500, "body": f"Erro: {str(e)}"}


def handle_update_position(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa atualização de posição do jogador
    """
    try:
        player_id = message.get("player_id")
        x = message.get("x", 0)
        y = message.get("y", 0)

        if not player_id:
            print("❌ player_id não fornecido na atualização")
            return {"statusCode": 400, "body": "player_id obrigatório"}

        # Atualiza posição na conexão
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET x = :x, y = :y, last_activity = :activity, expires_at = :expires",
            ExpressionAttributeValues={
                ":x": x,
                ":y": y,
                ":activity": int(time.time()),
                ":expires": int(time.time()) + 3600,  # Renova TTL
            },
        )

        # Obtém cor do jogador
        player_color = [255, 255, 255]  # Padrão branco
        try:
            response = connections_table.get_item(Key={"connection_id": connection_id})
            player_color = response.get("Item", {}).get("color", [255, 255, 255])
        except Exception as e:
            print(f"⚠️ Erro ao obter cor do jogador: {e}")

        # Notifica outros jogadores da nova posição
        broadcast_message(api_gateway_client, {"type": "player_update", "player_id": player_id, "x": x, "y": y, "color": player_color}, exclude_connection=connection_id)

        return {"statusCode": 200, "body": "Posição atualizada"}

    except Exception as e:
        print(f"❌ Erro ao atualizar posição: {str(e)}")
        return {"statusCode": 500, "body": f"Erro: {str(e)}"}


def handle_leave_game(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa saída do jogador do jogo
    """
    try:
        player_id = message.get("player_id")
        print(f"👋 Jogador {player_id} saindo do jogo")

        # Remove player_id da conexão (mas mantém a conexão)
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="REMOVE player_id, x, y, color SET last_activity = :activity, expires_at = :expires",
            ExpressionAttributeValues={":activity": int(time.time()), ":expires": int(time.time()) + 3600},
        )

        # Notifica outros jogadores
        if player_id:
            broadcast_message(api_gateway_client, {"type": "player_left", "player_id": player_id}, exclude_connection=connection_id)

        print(f"✅ Jogador {player_id} saiu do jogo")
        return {"statusCode": 200, "body": "Saiu do jogo"}

    except Exception as e:
        print(f"❌ Erro ao sair do jogo: {str(e)}")
        return {"statusCode": 500, "body": f"Erro: {str(e)}"}


def handle_ping(connection_id: str, api_gateway_client):
    """
    Responde a ping para manter conexão viva
    """
    try:
        # Atualiza atividade
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET last_activity = :activity, expires_at = :expires",
            ExpressionAttributeValues={":activity": int(time.time()), ":expires": int(time.time()) + 3600},
        )

        # Responde com pong
        send_message_to_connection(api_gateway_client, connection_id, {"type": "pong", "timestamp": int(time.time())})

        return {"statusCode": 200, "body": "Pong enviado"}

    except Exception as e:
        print(f"❌ Erro no ping: {str(e)}")
        return {"statusCode": 500, "body": f"Erro: {str(e)}"}


def get_active_players() -> Dict[str, Any]:
    """
    Obtém todos os jogadores ativos
    """
    try:
        cleanup_inactive_connections()

        # Busca apenas conexões com player_id
        response = connections_table.scan(FilterExpression="attribute_exists(player_id)")

        players = {}
        for item in response["Items"]:
            player_id = item.get("player_id")
            if player_id:
                players[player_id] = {"x": item.get("x", 0), "y": item.get("y", 0), "color": item.get("color", [255, 255, 255])}

        print(f"🎮 Jogadores ativos encontrados: {len(players)}")
        return players

    except Exception as e:
        print(f"❌ Erro ao obter jogadores ativos: {str(e)}")
        return {}


def cleanup_inactive_connections():
    """
    Remove conexões inativas (mais de 60 segundos sem atividade)
    """
    try:
        current_time = int(time.time())
        cutoff_time = current_time - 60  # 60 segundos

        response = connections_table.scan()

        inactive_count = 0
        for item in response["Items"]:
            last_activity = item.get("last_activity", 0)
            if last_activity < cutoff_time:
                connection_id = item["connection_id"]
                connections_table.delete_item(Key={"connection_id": connection_id})
                print(f"🧹 Removida conexão inativa: {connection_id}")
                inactive_count += 1

        if inactive_count > 0:
            print(f"🧹 Limpeza concluída: {inactive_count} conexões inativas removidas")

    except Exception as e:
        print(f"❌ Erro na limpeza de conexões: {str(e)}")


def send_message_to_connection(api_gateway_client, connection_id: str, message: Dict[str, Any]) -> bool:
    """
    Envia mensagem para uma conexão específica
    """
    try:
        api_gateway_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message, default=str).encode("utf-8"))
        return True
    except api_gateway_client.exceptions.GoneException:
        # Conexão já foi fechada, remove do DynamoDB
        print(f"🔌 Conexão {connection_id} já fechada, removendo do DynamoDB")
        try:
            connections_table.delete_item(Key={"connection_id": connection_id})
        except Exception as e:
            print(f"⚠️ Erro ao remover conexão órfã: {e}")
        return False
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "GoneException":
            # Mesmo tratamento que acima
            print(f"🔌 Conexão {connection_id} não existe mais")
            try:
                connections_table.delete_item(Key={"connection_id": connection_id})
            except:
                pass
        else:
            print(f"❌ Erro AWS ao enviar mensagem para {connection_id}: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral ao enviar mensagem para {connection_id}: {str(e)}")
        return False


def broadcast_message(api_gateway_client, message: Dict[str, Any], exclude_connection: str = None):
    """
    Envia mensagem para todas as conexões ativas
    """
    try:
        response = connections_table.scan()

        sent_count = 0
        failed_count = 0

        for item in response["Items"]:
            connection_id = item["connection_id"]

            # Pula a conexão excluída
            if exclude_connection and connection_id == exclude_connection:
                continue

            # Só envia para conexões com jogadores ativos
            if "player_id" in item and item["player_id"]:
                if send_message_to_connection(api_gateway_client, connection_id, message):
                    sent_count += 1
                else:
                    failed_count += 1

        print(f"📡 Broadcast: {sent_count} enviadas, {failed_count} falharam")

    except Exception as e:
        print(f"❌ Erro no broadcast: {str(e)}")


def get_connection_stats():
    """
    Retorna estatísticas das conexões para debug
    """
    try:
        response = connections_table.scan()

        total_connections = len(response["Items"])
        active_players = len([item for item in response["Items"] if "player_id" in item])

        return {"total_connections": total_connections, "active_players": active_players, "timestamp": int(time.time())}
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return {"total_connections": 0, "active_players": 0, "error": str(e)}


def debug_handler(event, context):
    """
    Função para debug - mostra estatísticas das conexões
    """
    stats = get_connection_stats()
    print(f"📊 Estatísticas de conexões: {json.dumps(stats, indent=2)}")

    return {"statusCode": 200, "body": json.dumps(stats, indent=2)}
