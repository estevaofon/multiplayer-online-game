#!/usr/bin/env python3
"""
Servidor WebSocket para Jogo Multiplayer - Modo Captura de Bandeira
AWS Lambda + DynamoDB + API Gateway WebSocket
"""

import json
import boto3
import time
import uuid
import os
import math
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from decimal import Decimal


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


def to_dynamodb_value(value):
    """Converte valor para formato aceito pelo DynamoDB"""
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, int):
        return value
    elif isinstance(value, (list, dict)):
        return json.loads(json.dumps(value), parse_float=Decimal)
    else:
        return value


def to_json_serializable(value):
    """Converte valor para formato serializável em JSON"""
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (list, dict)):
        return json.loads(json.dumps(value, default=str))
    else:
        return value


def convert_decimals_recursive(obj, path=""):
    """Converte recursivamente todos os valores Decimal em um objeto"""
    try:
        if isinstance(obj, Decimal):
            print(f"   Conversão Decimal em {path}: {obj} -> {float(obj)}")
            return float(obj)
        elif isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                result[key] = convert_decimals_recursive(value, new_path)
            return result
        elif isinstance(obj, list):
            result = []
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                result.append(convert_decimals_recursive(item, new_path))
            return result
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            print(f"⚠️ Tipo não esperado encontrado em {path}: {type(obj)} - {obj}")
            return str(obj)
    except Exception as e:
        print(f"❌ Erro ao converter Decimal em {path}: {e} - Tipo: {type(obj)} - Valor: {obj}")
        return str(obj)


# Configurações do jogo
GAME_WIDTH = 800
GAME_HEIGHT = 600
FLAG_SIZE = 30
BASE_SIZE = 100
BULLET_SPEED = 8
BULLET_DAMAGE = 25
PLAYER_MAX_HP = 100
RESPAWN_TIME = 5  # segundos

# Times
TEAMS = {
    "red": {
        "name": "Time Vermelho",
        "color": [255, 100, 100],
        "base_x": 50,
        "base_y": GAME_HEIGHT // 2,
        "flag_x": 50,
        "flag_y": GAME_HEIGHT // 2,
        "spawn_x": 100,
        "spawn_y": GAME_HEIGHT // 2
    },
    "blue": {
        "name": "Time Azul", 
        "color": [100, 100, 255],
        "base_x": GAME_WIDTH - 50,
        "base_y": GAME_HEIGHT // 2,
        "flag_x": GAME_WIDTH - 50,
        "flag_y": GAME_HEIGHT // 2,
        "spawn_x": GAME_WIDTH - 100,
        "spawn_y": GAME_HEIGHT // 2
    }
}

# Estado global do jogo
game_state = {
    "flags": {
        "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
        "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
    },
    "bullets": [],
    "scores": {"red": 0, "blue": 0},
    "game_started": False
}

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
                "player_id": None,
                "team": None,
                "hp": PLAYER_MAX_HP,
                "x": 0,
                "y": 0,
                "last_activity": int(time.time()),
                "expires_at": int(time.time()) + 3600,
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
        player_data = None
        try:
            response = connections_table.get_item(Key={"connection_id": connection_id})
            connection_data = response.get("Item", {})
            player_data = {
                "player_id": connection_data.get("player_id"),
                "team": connection_data.get("team")
            }
            print(f"🔍 Player ID encontrado: {player_data}")
        except Exception as e:
            print(f"⚠️ Erro ao obter dados da conexão: {e}")

        # Remove conexão do DynamoDB
        try:
            connections_table.delete_item(Key={"connection_id": connection_id})
            print(f"🗑️ Conexão {connection_id} removida do DynamoDB")
        except Exception as e:
            print(f"⚠️ Erro ao remover conexão: {e}")

        # Notifica outros jogadores se havia um player_id
        if player_data and player_data["player_id"]:
            print(f"📢 Notificando saída do jogador {player_data['player_id']}")
            broadcast_message(api_gateway_client, {
                "type": "player_left", 
                "player_id": player_data["player_id"],
                "team": player_data["team"],
                "timestamp": int(time.time())
            }, exclude_connection=connection_id)

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
        elif action == "shoot":
            return handle_shoot(connection_id, message, api_gateway_client)
        elif action == "capture_flag":
            return handle_capture_flag(connection_id, message, api_gateway_client)
        elif action == "drop_flag":
            return handle_drop_flag(connection_id, message, api_gateway_client)
        elif action == "respawn":
            return handle_respawn(connection_id, message, api_gateway_client)
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
        team = message.get("team")  # "red" ou "blue"

        if not player_id:
            player_id = str(uuid.uuid4())[:8]

        # Se não especificou time, escolhe automaticamente
        if not team:
            print(f"🎯 Atribuindo time automaticamente para {player_id}")
            active_players = get_active_players()
            red_count = sum(1 for p in active_players.values() if p.get("team") == "red")
            blue_count = sum(1 for p in active_players.values() if p.get("team") == "blue")
            
            print(f"   Jogadores ativos: {len(active_players)}")
            print(f"   Time vermelho: {red_count} jogadores")
            print(f"   Time azul: {blue_count} jogadores")
            
            if red_count <= blue_count:
                team = "red"
                print(f"   ➡️ Atribuindo time VERMELHO (menos jogadores)")
            else:
                team = "blue"
                print(f"   ➡️ Atribuindo time AZUL (menos jogadores)")
        else:
            print(f"🎯 Jogador {player_id} especificou time: {team}")

        # Posição inicial baseada no time
        spawn_x = TEAMS[team]["spawn_x"]
        spawn_y = TEAMS[team]["spawn_y"]

        print(f"🎮 Jogador {player_id} entrando no jogo no time {team} na posição ({spawn_x}, {spawn_y})")

        # Atualiza conexão com dados do jogador (converte float para Decimal)
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET player_id = :pid, team = :team, hp = :hp, x = :x, y = :y, last_activity = :time",
            ExpressionAttributeValues={
                ":pid": player_id,
                ":team": team,
                ":hp": PLAYER_MAX_HP,
                ":x": Decimal(str(spawn_x)),
                ":y": Decimal(str(spawn_y)),
                ":time": int(time.time())
            }
        )

        # Notifica o jogador sobre sua entrada
        player_data = {
            "player_id": player_id,
            "team": team,
            "color": TEAMS[team]["color"],
            "x": spawn_x,
            "y": spawn_y,
            "hp": PLAYER_MAX_HP
        }

        send_message_to_connection(api_gateway_client, connection_id, {
            "type": "player_joined",
            "player_data": player_data,
            "timestamp": int(time.time())
        })

        # Notifica outros jogadores
        print(f"📢 Notificando entrada do jogador {player_id} para outros jogadores")
        broadcast_message(api_gateway_client, {
            "type": "player_joined",
            "player_id": player_id,
            "team": team,
            "color": TEAMS[team]["color"],
            "x": spawn_x,
            "y": spawn_y,
            "hp": float(PLAYER_MAX_HP),  # Garante que é float
            "timestamp": int(time.time())
        }, exclude_connection=connection_id)

        # Envia estado atual do jogo para o novo jogador
        print(f"🎯 Chamando send_game_state para {connection_id}")
        send_game_state(api_gateway_client, connection_id)
        print(f"🎯 send_game_state concluído para {connection_id}")

        return {"statusCode": 200, "body": "Jogador entrou no jogo"}

    except Exception as e:
        print(f"❌ Erro ao entrar no jogo: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao entrar no jogo: {str(e)}"}


def handle_update_position(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa atualização de posição do jogador
    """
    try:
        player_id = message.get("player_id")
        x = message.get("x", 0)
        y = message.get("y", 0)

        if not player_id:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "player_id é obrigatório"})
            return {"statusCode": 400, "body": "player_id é obrigatório"}

        # Atualiza posição no DynamoDB (converte float para Decimal)
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET x = :x, y = :y, last_activity = :time",
            ExpressionAttributeValues={
                ":x": Decimal(str(x)),
                ":y": Decimal(str(y)),
                ":time": int(time.time())
            }
        )

        # Obtém dados do jogador para broadcast
        response = connections_table.get_item(Key={"connection_id": connection_id})
        player_data = response.get("Item", {})
        team = player_data.get("team")
        hp = player_data.get("hp", PLAYER_MAX_HP)
        
        # Converte hp de Decimal para float se necessário
        if isinstance(hp, Decimal):
            hp = float(hp)

        # Broadcast para outros jogadores
        broadcast_message(api_gateway_client, {
            "type": "player_update",
            "player_id": player_id,
            "team": team,
            "color": TEAMS[team]["color"],
            "x": x,
            "y": y,
            "hp": hp,
            "timestamp": int(time.time())
        }, exclude_connection=connection_id)

        # Verifica se alguma bandeira foi levada para a base
        check_flag_scoring(api_gateway_client)

        return {"statusCode": 200, "body": "Posição atualizada"}

    except Exception as e:
        print(f"❌ Erro ao atualizar posição: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao atualizar posição: {str(e)}"}


def handle_shoot(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa tiro do jogador
    """
    try:
        player_id = message.get("player_id")
        target_x = message.get("target_x")
        target_y = message.get("target_y")
        player_x = message.get("player_x")
        player_y = message.get("player_y")

        if not all([player_id, target_x, target_y, player_x, player_y]):
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Dados de tiro incompletos"})
            return {"statusCode": 400, "body": "Dados de tiro incompletos"}

        # Obtém dados do jogador
        response = connections_table.get_item(Key={"connection_id": connection_id})
        player_data = response.get("Item", {})
        team = player_data.get("team")
        hp = player_data.get("hp", PLAYER_MAX_HP)

        if hp <= 0:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Jogador morto não pode atirar"})
            return {"statusCode": 400, "body": "Jogador morto não pode atirar"}

        # Cria projétil
        bullet_id = str(uuid.uuid4())[:8]
        dx = target_x - player_x
        dy = target_y - player_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            dx = dx / distance * BULLET_SPEED
            dy = dy / distance * BULLET_SPEED
        else:
            dx = 0
            dy = BULLET_SPEED

        bullet = {
            "id": bullet_id,
            "shooter_id": player_id,
            "shooter_team": team,
            "x": player_x,
            "y": player_y,
            "dx": dx,
            "dy": dy,
            "created_at": int(time.time())
        }

        game_state["bullets"].append(bullet)

        # Broadcast do tiro
        broadcast_message(api_gateway_client, {
            "type": "bullet_shot",
            "bullet": bullet,
            "timestamp": int(time.time())
        })

        # Processa colisões de projéteis
        process_bullet_collisions(api_gateway_client)

        return {"statusCode": 200, "body": "Tiro processado"}

    except Exception as e:
        print(f"❌ Erro ao processar tiro: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao processar tiro: {str(e)}"}


def handle_capture_flag(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa captura de bandeira
    """
    try:
        player_id = message.get("player_id")
        flag_team = message.get("flag_team")  # "red" ou "blue"

        if not all([player_id, flag_team]):
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Dados de captura incompletos"})
            return {"statusCode": 400, "body": "Dados de captura incompletos"}

        # Obtém dados do jogador
        response = connections_table.get_item(Key={"connection_id": connection_id})
        player_data = response.get("Item", {})
        player_team = player_data.get("team")
        hp = player_data.get("hp", PLAYER_MAX_HP)

        if hp <= 0:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Jogador morto não pode capturar bandeira"})
            return {"statusCode": 400, "body": "Jogador morto não pode capturar bandeira"}

        # Verifica se pode capturar (time oposto)
        if player_team == flag_team:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Não pode capturar bandeira do próprio time"})
            return {"statusCode": 400, "body": "Não pode capturar bandeira do próprio time"}

        # Verifica se a bandeira está disponível
        flag = game_state["flags"][flag_team]
        if flag["captured"]:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Bandeira já foi capturada"})
            return {"statusCode": 400, "body": "Bandeira já foi capturada"}

        # Captura a bandeira
        flag["captured"] = True
        flag["carrier"] = player_id

        # Broadcast da captura
        broadcast_message(api_gateway_client, {
            "type": "flag_captured",
            "flag_team": flag_team,
            "carrier_id": player_id,
            "carrier_team": player_team,
            "timestamp": int(time.time())
        })

        return {"statusCode": 200, "body": "Bandeira capturada"}

    except Exception as e:
        print(f"❌ Erro ao capturar bandeira: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao capturar bandeira: {str(e)}"}


def handle_drop_flag(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa soltura de bandeira
    """
    try:
        player_id = message.get("player_id")
        x = message.get("x")
        y = message.get("y")

        if not all([player_id, x, y]):
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Dados de soltura incompletos"})
            return {"statusCode": 400, "body": "Dados de soltura incompletos"}

        # Encontra bandeira carregada pelo jogador
        for flag_team, flag in game_state["flags"].items():
            if flag["captured"] and flag["carrier"] == player_id:
                # Solta a bandeira
                flag["captured"] = False
                flag["carrier"] = None
                flag["x"] = x
                flag["y"] = y

                # Broadcast da soltura
                broadcast_message(api_gateway_client, {
                    "type": "flag_dropped",
                    "flag_team": flag_team,
                    "x": x,
                    "y": y,
                    "timestamp": int(time.time())
                })
                break

        return {"statusCode": 200, "body": "Bandeira solta"}

    except Exception as e:
        print(f"❌ Erro ao soltar bandeira: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao soltar bandeira: {str(e)}"}


def handle_respawn(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa respawn do jogador
    """
    try:
        player_id = message.get("player_id")

        if not player_id:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "player_id é obrigatório"})
            return {"statusCode": 400, "body": "player_id é obrigatório"}

        # Obtém dados do jogador
        response = connections_table.get_item(Key={"connection_id": connection_id})
        player_data = response.get("Item", {})
        team = player_data.get("team")

        if not team:
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Time não definido"})
            return {"statusCode": 400, "body": "Time não definido"}

        # Posição de respawn baseada no time
        spawn_x = TEAMS[team]["spawn_x"]
        spawn_y = TEAMS[team]["spawn_y"]

        # Atualiza jogador
        connections_table.update_item(
            Key={"connection_id": connection_id},
            UpdateExpression="SET hp = :hp, x = :x, y = :y, last_activity = :time",
            ExpressionAttributeValues={
                ":hp": PLAYER_MAX_HP,
                ":x": spawn_x,
                ":y": spawn_y,
                ":time": int(time.time())
            }
        )

        # Broadcast do respawn
        broadcast_message(api_gateway_client, {
            "type": "player_respawned",
            "player_id": player_id,
            "team": team,
            "x": spawn_x,
            "y": spawn_y,
            "hp": PLAYER_MAX_HP,
            "timestamp": int(time.time())
        })

        return {"statusCode": 200, "body": "Jogador respawnou"}

    except Exception as e:
        print(f"❌ Erro ao respawnar: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao respawnar: {str(e)}"}


def handle_ping(connection_id: str, api_gateway_client):
    """
    Processa ping para manter conexão viva
    """
    try:
        send_message_to_connection(api_gateway_client, connection_id, {"type": "pong", "timestamp": int(time.time())})
        return {"statusCode": 200, "body": "Pong"}
    except Exception as e:
        print(f"❌ Erro no ping: {str(e)}")
        return {"statusCode": 500, "body": f"Erro no ping: {str(e)}"}


def process_bullet_collisions(api_gateway_client):
    """
    Processa colisões de projéteis com jogadores
    """
    try:
        current_time = int(time.time())
        active_players = get_active_players()
        bullets_to_remove = []

        for bullet in game_state["bullets"]:
            # Remove projéteis antigos (mais de 5 segundos)
            if current_time - bullet["created_at"] > 5:
                bullets_to_remove.append(bullet)
                continue

            # Atualiza posição do projétil
            bullet["x"] += bullet["dx"]
            bullet["y"] += bullet["dy"]

            # Verifica colisão com jogadores
            for player_id, player_data in active_players.items():
                if player_data.get("team") == bullet["shooter_team"]:
                    continue  # Não atira no próprio time

                player_x = player_data.get("x", 0)
                player_y = player_data.get("y", 0)
                
                # Distância entre projétil e jogador
                dx = bullet["x"] - player_x
                dy = bullet["y"] - player_y
                distance = math.sqrt(dx*dx + dy*dy)

                if distance < 20:  # Raio de colisão
                    # Atingiu jogador
                    new_hp = max(0, player_data.get("hp", PLAYER_MAX_HP) - BULLET_DAMAGE)
                    
                    # Atualiza HP no DynamoDB
                    connection_id = get_connection_by_player_id(player_id)
                    if connection_id:
                        connections_table.update_item(
                            Key={"connection_id": connection_id},
                            UpdateExpression="SET hp = :hp, last_activity = :time",
                            ExpressionAttributeValues={
                                ":hp": new_hp,
                                ":time": current_time
                            }
                        )

                    # Broadcast do dano
                    broadcast_message(api_gateway_client, {
                        "type": "player_hit",
                        "player_id": player_id,
                        "damage": BULLET_DAMAGE,
                        "new_hp": new_hp,
                        "shooter_id": bullet["shooter_id"],
                        "timestamp": current_time
                    })

                    bullets_to_remove.append(bullet)
                    break

            # Remove projéteis que saíram da tela
            if (bullet["x"] < 0 or bullet["x"] > GAME_WIDTH or 
                bullet["y"] < 0 or bullet["y"] > GAME_HEIGHT):
                bullets_to_remove.append(bullet)

        # Remove projéteis processados
        for bullet in bullets_to_remove:
            if bullet in game_state["bullets"]:
                game_state["bullets"].remove(bullet)

        # Broadcast da posição atualizada dos projéteis
        if game_state["bullets"]:
            broadcast_message(api_gateway_client, {
                "type": "bullets_update",
                "bullets": game_state["bullets"],
                "timestamp": current_time
            })

    except Exception as e:
        print(f"❌ Erro ao processar colisões: {str(e)}")


def check_flag_scoring(api_gateway_client):
    """
    Verifica se alguma bandeira foi levada para a base
    """
    try:
        current_time = int(time.time())
        print(f"🏁 Verificando pontuação de bandeiras...")
        
        for flag_team, flag in game_state["flags"].items():
            if not flag["captured"]:
                continue

            carrier_id = flag["carrier"]
            if not carrier_id:
                continue

            print(f"   Bandeira {flag_team} capturada por {carrier_id}")

            # Obtém dados do portador
            connection_id = get_connection_by_player_id(carrier_id)
            if not connection_id:
                print(f"   ❌ Conexão não encontrada para {carrier_id}")
                continue

            response = connections_table.get_item(Key={"connection_id": connection_id})
            player_data = response.get("Item", {})
            carrier_team = player_data.get("team")
            carrier_x = player_data.get("x", 0)
            carrier_y = player_data.get("y", 0)

            if not carrier_team:
                print(f"   ❌ Time não encontrado para {carrier_id}")
                continue

            print(f"   Portador {carrier_id} ({carrier_team}) em ({carrier_x}, {carrier_y})")

            # Verifica se está na base do time oposto
            enemy_team = "blue" if flag_team == "red" else "red"
            base_x = TEAMS[enemy_team]["base_x"]
            base_y = TEAMS[enemy_team]["base_y"]

            dx = carrier_x - base_x
            dy = carrier_y - base_y
            distance = math.sqrt(dx*dx + dy*dy)

            print(f"   Distância até base {enemy_team} ({base_x}, {base_y}): {distance}")

            if distance < BASE_SIZE // 2:
                print(f"🏆 PONTO! {carrier_team} marcou ponto com bandeira {flag_team}!")
                
                # Ponto para o time do portador
                game_state["scores"][carrier_team] += 1

                # Reseta a bandeira
                flag["captured"] = False
                flag["carrier"] = None
                flag["x"] = TEAMS[flag_team]["flag_x"]
                flag["y"] = TEAMS[flag_team]["flag_y"]

                # Broadcast do ponto
                broadcast_message(api_gateway_client, {
                    "type": "flag_scored",
                    "scoring_team": carrier_team,
                    "flag_team": flag_team,
                    "scores": game_state["scores"],
                    "timestamp": current_time
                })
            else:
                print(f"   Ainda não chegou na base (precisa < {BASE_SIZE // 2})")

    except Exception as e:
        print(f"❌ Erro ao verificar pontuação: {str(e)}")
        import traceback
        traceback.print_exc()


def send_game_state(api_gateway_client, connection_id):
    """
    Envia estado completo do jogo para um jogador
    """
    try:
        print(f"🔍 Iniciando send_game_state para {connection_id}")
        
        active_players = get_active_players()
        print(f"📊 Enviando game_state para {connection_id} com {len(active_players)} jogadores ativos")
        print(f"   Jogadores encontrados: {list(active_players.keys())}")
        
        # Monta o game_state_message
        game_state_message = {
            "type": "game_state",
            "players": active_players,
            "flags": game_state["flags"],
            "bullets": game_state["bullets"],
            "scores": game_state["scores"],
            "teams": TEAMS,
            "timestamp": int(time.time())
        }
        
        # Converte recursivamente todos os valores Decimal
        print(f"🔧 Convertendo valores Decimal...")
        
        # Log detalhado antes da conversão
        print(f"   game_state antes da conversão:")
        print(f"     - players: {type(active_players)} com {len(active_players)} itens")
        print(f"     - flags: {type(game_state['flags'])}")
        print(f"     - bullets: {type(game_state['bullets'])} com {len(game_state['bullets'])} itens")
        print(f"     - scores: {type(game_state['scores'])}")
        print(f"     - teams: {type(TEAMS)}")
        
        game_state_message = convert_decimals_recursive(game_state_message)
        print(f"✅ Conversão Decimal concluída")
        
        print(f"📤 Tentando enviar game_state para {connection_id}")
        print(f"   Tamanho da mensagem: {len(str(game_state_message))} caracteres")
        
        success = send_message_to_connection(api_gateway_client, connection_id, game_state_message)
        
        if success:
            print(f"✅ game_state enviado com sucesso para {connection_id}")
        else:
            print(f"❌ Falha ao enviar game_state para {connection_id}")

    except Exception as e:
        print(f"❌ Erro ao enviar estado do jogo: {str(e)}")
        import traceback
        traceback.print_exc()


def get_connection_by_player_id(player_id: str) -> str:
    """
    Obtém connection_id pelo player_id
    """
    try:
        response = connections_table.scan(
            FilterExpression="player_id = :pid",
            ExpressionAttributeValues={":pid": player_id}
        )
        
        items = response.get("Items", [])
        if items:
            return items[0]["connection_id"]
        return None

    except Exception as e:
        print(f"❌ Erro ao buscar conexão por player_id: {str(e)}")
        return None


def get_active_players() -> Dict[str, Any]:
    """
    Obtém todos os jogadores ativos
    """
    try:
        response = connections_table.scan(
            FilterExpression="player_id <> :null",
            ExpressionAttributeValues={":null": None},
            ConsistentRead=True  # <--- leitura consistente
        )
        
        players = {}
        for item in response.get("Items", []):
            if item.get("player_id"):
                team = item.get("team")
                print(f"🔍 Processando jogador {item['player_id']} com team: {team}")
                
                # Verifica se o team existe em TEAMS
                if team not in TEAMS:
                    print(f"⚠️ Team '{team}' não encontrado em TEAMS: {list(TEAMS.keys())}")
                    team = "red"  # fallback
                
                players[item["player_id"]] = {
                    "team": team,
                    "x": float(item.get("x", 0)) if isinstance(item.get("x"), Decimal) else item.get("x", 0),
                    "y": float(item.get("y", 0)) if isinstance(item.get("y"), Decimal) else item.get("y", 0),
                    "hp": float(item.get("hp", PLAYER_MAX_HP)) if isinstance(item.get("hp"), Decimal) else item.get("hp", PLAYER_MAX_HP),
                    "color": TEAMS[team]["color"]
                }
        
        return players

    except Exception as e:
        print(f"❌ Erro ao obter jogadores ativos: {str(e)}")
        return {}


def cleanup_inactive_connections():
    """
    Remove conexões inativas
    """
    try:
        current_time = int(time.time())
        response = connections_table.scan()
        
        for item in response.get("Items", []):
            last_activity = item.get("last_activity", 0)
            if current_time - last_activity > 300:  # 5 minutos
                connections_table.delete_item(Key={"connection_id": item["connection_id"]})
                print(f"🗑️ Conexão inativa removida: {item['connection_id']}")

    except Exception as e:
        print(f"❌ Erro ao limpar conexões inativas: {str(e)}")


def send_message_to_connection(api_gateway_client, connection_id: str, message: Dict[str, Any]) -> bool:
    """
    Envia mensagem para uma conexão específica
    """
    try:
        try:
            # Log detalhado para debug - verifica se há Decimal antes da serialização
            print(f"🔍 Verificando mensagem antes da serialização para {connection_id}")
            
            def find_decimals(obj, path=""):
                """Encontra todos os valores Decimal em um objeto"""
                if isinstance(obj, Decimal):
                    print(f"❌ DECIMAL ENCONTRADO em {path}: {obj} (tipo: {type(obj)})")
                    return True
                elif isinstance(obj, dict):
                    found = False
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if find_decimals(value, new_path):
                            found = True
                    return found
                elif isinstance(obj, list):
                    found = False
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]" if path else f"[{i}]"
                        if find_decimals(item, new_path):
                            found = True
                    return found
                return False
            
            # Procura por Decimals antes de tentar serializar
            if find_decimals(message, "message"):
                print(f"❌ DECIMAIS ENCONTRADOS na mensagem para {connection_id}")
                print(f"   Estrutura da mensagem: {type(message)}")
                print(f"   Chaves da mensagem: {list(message.keys()) if isinstance(message, dict) else 'N/A'}")
            
            # Log detalhado para debug
            print(f"📝 Enviando para {connection_id}: {json.dumps(message, default=str)[:500]}")
            data_str = json.dumps(message)
        except Exception as e:
            print(f"❌ Erro ao serializar mensagem para {connection_id}: {e}")
            print(f"   Tipo da mensagem: {type(message)}")
            print(f"   Conteúdo da mensagem: {message}")
            return False
        response = api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=data_str
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'GoneException':
            # Conexão foi fechada, remove do DynamoDB
            try:
                connections_table.delete_item(Key={"connection_id": connection_id})
                print(f"🗑️ Conexão fechada removida: {connection_id}")
            except:
                pass
        else:
            print(f"❌ Erro ao enviar mensagem para {connection_id}: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para {connection_id}: {e}")
        return False


def broadcast_message(api_gateway_client, message: Dict[str, Any], exclude_connection: str = None):
    """
    Envia mensagem para todos os jogadores conectados
    """
    try:
        response = connections_table.scan()
        
        for item in response.get("Items", []):
            connection_id = item["connection_id"]
            player_id = item.get("player_id")
            
            # Só envia para conexões que têm player_id (jogadores ativos)
            if not player_id:
                continue
                
            if exclude_connection and connection_id == exclude_connection:
                continue
                
            print(f"📡 Broadcast para {player_id} ({connection_id})")
            send_message_to_connection(api_gateway_client, connection_id, message)

    except Exception as e:
        print(f"❌ Erro no broadcast: {str(e)}")


def get_connection_stats():
    """
    Obtém estatísticas das conexões
    """
    try:
        response = connections_table.scan()
        items = response.get("Items", [])
        
        total_connections = len(items)
        active_players = len([item for item in items if item.get("player_id")])
        
        return {
            "total_connections": total_connections,
            "active_players": active_players,
            "game_state": game_state
        }

    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {str(e)}")
        return {}


def debug_handler(event, context):
    """
    Função de debug para testar o sistema
    """
    try:
        stats = get_connection_stats()
        print(f"📊 Estatísticas: {json.dumps(stats, default=str)}")
        
        return {
            "statusCode": 200,
            "body": json.dumps(stats, default=str)
        }

    except Exception as e:
        print(f"❌ Erro no debug: {str(e)}")
        return {"statusCode": 501, "body": f"Erro no debug: {str(e)}"}
