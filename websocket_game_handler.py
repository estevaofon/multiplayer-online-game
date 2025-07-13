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


# Versão do servidor para verificar se foi deployado
SERVER_VERSION = "2.1.0-bullet-fix"

# Configurações
TABLE_NAME = os.environ.get("TABLE_NAME", "WebSocketConnections")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
API_GATEWAY_ENDPOINT = os.environ.get("API_GATEWAY_ENDPOINT")

# Clientes AWS
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
connections_table = dynamodb.Table(TABLE_NAME)

# DynamoDB table para balas
bullets_table = dynamodb.Table("game_bullets")

# DynamoDB table para estado do jogo
game_state_table = dynamodb.Table("game_state")


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

def load_game_state():
    """Carrega o estado do jogo do DynamoDB"""
    try:
        print("🔄 Carregando estado do jogo do DynamoDB...")
        print("🔍 ID da tabela: current_game")
        print("🔍 Nome da tabela: game_state")
        
        response = game_state_table.get_item(Key={"id": "current_game"})
        
        print(f"🔍 Resposta completa do DynamoDB: {json.dumps(response, default=str)}")
        print(f"🔍 'Item' presente na resposta: {'Item' in response}")
        
        if "Item" in response:
            item = response["Item"]
            print(f"✅ Estado do jogo carregado do DynamoDB")
            print(f"🔍 Item completo: {json.dumps(item, default=str)}")
            
            loaded_scores = item.get("scores", {"red": 0, "blue": 0})
            print(f"🔍 Scores carregados do DynamoDB: {loaded_scores}")
            print(f"🔍 Tipo dos scores: {type(loaded_scores)}")
            
            result = {
                "flags": item.get("flags", {
                    "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                    "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
                }),
                "bullets": item.get("bullets", []),
                "scores": loaded_scores,
                "game_started": item.get("game_started", False)
            }
            
            print(f"🔍 Estado retornado: {json.dumps(result, default=str)}")
            return result
        else:
            print("📝 NENHUM ESTADO PERSISTIDO ENCONTRADO - USANDO ESTADO PADRÃO")
            default_scores = {"red": 0, "blue": 0}
            print(f"🔍 Scores padrão definidos: {default_scores}")
            
            result = {
                "flags": {
                    "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                    "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
                },
                "bullets": [],
                "scores": default_scores,
                "game_started": False
            }
            
            print(f"🔍 Estado padrão retornado: {json.dumps(result, default=str)}")
            return result
    except Exception as e:
        print(f"❌ Erro ao carregar estado do jogo: {str(e)}")
        # Retorna estado padrão em caso de erro
        return {
            "flags": {
                "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 0, "blue": 0},
            "game_started": False
        }

def save_game_state():
    """Salva o estado do jogo no DynamoDB"""
    try:
        print(f"💾 Salvando estado do jogo: scores={game_state['scores']}")
        game_state_table.put_item(
            Item={
                "id": "current_game",
                "flags": game_state["flags"],
                "bullets": game_state["bullets"],
                "scores": game_state["scores"],
                "game_started": game_state["game_started"],
                "last_updated": int(time.time()),
                "expires_at": int(time.time()) + 86400  # Expira em 24 horas
            }
        )
        print("✅ Estado do jogo salvo com sucesso")
    except Exception as e:
        print(f"❌ Erro ao salvar estado do jogo: {str(e)}")

def reset_game_state():
    """Reseta o estado do jogo para valores padrão"""
    try:
        print("🔄 RESETANDO ESTADO DO JOGO")
        
        # Reseta o estado global
        global game_state
        game_state = {
            "flags": {
                "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 0, "blue": 0},
            "game_started": False
        }
        
        print(f"🔍 Estado resetado: scores={game_state['scores']}")
        
        # Salva no DynamoDB
        save_game_state()
        
        print("✅ Estado do jogo resetado e salvo no DynamoDB")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao resetar estado do jogo: {str(e)}")
        return False

# Estado global do jogo
print("🚀 INICIALIZANDO ESTADO GLOBAL DO JOGO")
game_state = load_game_state()
print(f"🎮 Estado inicial do jogo carregado: scores={game_state['scores']}")
print(f"🔍 Tipo do game_state: {type(game_state)}")
print(f"🔍 Tipo dos scores: {type(game_state['scores'])}")
print(f"🔍 Conteúdo completo do game_state: {json.dumps(game_state, default=str)}")


def lambda_handler(event, context):
    """
    Função principal para processar eventos WebSocket
    """
    try:
        print(f"🚀 Servidor versão: {SERVER_VERSION}")
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
        print(f"   Mensagem completa: {message}")

        if action == "join":
            return handle_join_game(connection_id, message, api_gateway_client)
        elif action == "update":
            return handle_update_position(connection_id, message, api_gateway_client)
        elif action == "shoot":
            print(f"   🎯 Chamando handle_shoot para {connection_id}")
            print(f"   📋 Dados da mensagem shoot: {message}")
            result = handle_shoot(connection_id, message, api_gateway_client)
            print(f"   ✅ handle_shoot retornou: {result}")
            return result
        elif action == "capture_flag":
            return handle_capture_flag(connection_id, message, api_gateway_client)
        elif action == "drop_flag":
            return handle_drop_flag(connection_id, message, api_gateway_client)
        elif action == "respawn":
            return handle_respawn(connection_id, message, api_gateway_client)
        elif action == "ping":
            return handle_ping(connection_id, api_gateway_client)
        elif action == "bullet_update":
            return handle_bullet_update(connection_id, message, api_gateway_client)
        elif action == "reset_game":
            return handle_reset_game(connection_id, api_gateway_client)

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

        print(f"🎮 Jogador {player_id} entrando no jogo no time {team} na posição ({spawn_x}, {spawn_y}) - Servidor v{SERVER_VERSION}")

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

        # Broadcast para outros jogadores (SEM incluir HP para evitar conflitos)
        broadcast_message(api_gateway_client, {
            "type": "player_update",
            "player_id": player_id,
            "team": team,
            "color": TEAMS[team]["color"],
            "x": x,
            "y": y,
            "timestamp": int(time.time())
        }, exclude_connection=connection_id)

        # Verifica se alguma bandeira foi levada para a base
        check_flag_scoring(api_gateway_client)

        # Verifica colisões de balas periodicamente
        check_bullet_collisions_periodic(api_gateway_client)

        return {"statusCode": 200, "body": "Posição atualizada"}

    except Exception as e:
        print(f"❌ Erro ao atualizar posição: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao atualizar posição: {str(e)}"}


def handle_shoot(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa tiro do jogador
    """
    try:
        print(f"🔫 Processando tiro para connection {connection_id}")
        player_id = message.get("player_id")
        target_x = message.get("target_x")
        target_y = message.get("target_y")
        player_x = message.get("player_x")
        player_y = message.get("player_y")

        print(f"   Dados do tiro: player_id={player_id}, target=({target_x}, {target_y}), pos=({player_x}, {player_y})")

        if not all([player_id, target_x, target_y, player_x, player_y]):
            print(f"   ❌ Dados de tiro incompletos")
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

        current_time = time.time()  # Use float para created_at
        bullet = {
            "id": bullet_id,
            "shooter_id": player_id,
            "shooter_team": team,
            "x": player_x,
            "y": player_y,
            "dx": dx,
            "dy": dy,
            "created_at": current_time,
            "ttl": int(current_time) + 180  # TTL pode ser int
        }

        print(f"   💾 Chamando save_bullet_dynamo para bala {bullet_id} - Servidor v{SERVER_VERSION}")
        save_bullet_dynamo(bullet)
        print(f"   ✅ Bala {bullet_id} salva no DynamoDB com TTL de 3 minutos")

        # Broadcast do tiro para todos os clientes
        broadcast_message(api_gateway_client, {
            "type": "bullet_shot",
            "bullet": bullet,
            "timestamp": int(time.time())
        })

        print(f"   📤 Broadcast do tiro enviado para todos os clientes")
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

        # Salva o estado do jogo no DynamoDB
        save_game_state()

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

                # Salva o estado do jogo no DynamoDB
                save_game_state()

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

        # Broadcast específico de HP para sincronização (sem log redundante)
        broadcast_message(api_gateway_client, {
            "type": "player_hp_update",
            "player_id": player_id,
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

def handle_reset_game(connection_id: str, api_gateway_client):
    """
    Reseta o estado do jogo
    """
    try:
        print("🔄 RESETANDO JOGO SOLICITADO")
        
        # Reseta o estado
        if reset_game_state():
            # Notifica todos os jogadores
            broadcast_message(api_gateway_client, {
                "type": "game_reset",
                "scores": {"red": 0, "blue": 0},
                "timestamp": int(time.time())
            })
            
            print("✅ Jogo resetado com sucesso")
            return {"statusCode": 200, "body": "Jogo resetado"}
        else:
            print("❌ Falha ao resetar jogo")
            return {"statusCode": 500, "body": "Falha ao resetar jogo"}

    except Exception as e:
        print(f"❌ Erro ao resetar jogo: {str(e)}")
        return {"statusCode": 500, "body": f"Erro ao resetar jogo: {str(e)}"}


def handle_bullet_update(connection_id: str, message: Dict[str, Any], api_gateway_client):
    """
    Processa atualização de posição de bala do cliente
    """
    try:
        bullet_id = message.get("bullet_id")
        x = message.get("x")
        y = message.get("y")
        shooter_id = message.get("shooter_id")

        print(f"📝 Recebida atualização de bala: {bullet_id} para ({x}, {y}) do shooter {shooter_id}")

        if not all([bullet_id, x, y, shooter_id]):
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Dados de atualização de bala incompletos"})
            return {"statusCode": 400, "body": "Dados de atualização de bala incompletos"}

        # Busca a bala no DynamoDB
        try:
            print(f"🔍 Buscando bala {bullet_id} no DynamoDB...")
            response = bullets_table.get_item(Key={"id": bullet_id})
            bullet = response.get("Item")
            
            if not bullet:
                print(f"❌ Bala {bullet_id} não encontrada no DynamoDB")
                print(f"   Response completo: {response}")
                
                # Lista todas as balas para debug
                all_bullets_response = bullets_table.scan()
                all_bullets = all_bullets_response.get("Items", [])
                print(f"   Balas existentes no DynamoDB: {len(all_bullets)}")
                for b in all_bullets:
                    print(f"     - {b.get('id')}: ({b.get('x')}, {b.get('y')}) - shooter: {b.get('shooter_id')}")
                
                send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Bala não encontrada"})
                return {"statusCode": 400, "body": "Bala não encontrada"}
            
            print(f"✅ Bala {bullet_id} encontrada no DynamoDB")
            print(f"   Dados da bala: {bullet}")
        except Exception as e:
            print(f"❌ Erro ao buscar bala no DynamoDB: {e}")
            import traceback
            traceback.print_exc()
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Erro ao buscar bala"})
            return {"statusCode": 500, "body": "Erro ao buscar bala"}

        # Verifica se o cliente que enviou é o atirador (para evitar cheating)
        if bullet["shooter_id"] != shooter_id:
            print(f"❌ Tentativa de atualizar bala de outro jogador: {bullet['shooter_id']} != {shooter_id}")
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Apenas o atirador pode atualizar a bala"})
            return {"statusCode": 400, "body": "Apenas o atirador pode atualizar a bala"}

        # Atualiza posição da bala
        bullet["x"] = x
        bullet["y"] = y
        
        # Atualiza posição no DynamoDB
        print(f"💾 Atualizando bala {bullet_id} no DynamoDB para ({x}, {y})")
        update_success = update_bullet_dynamo(bullet_id, x, y)
        
        if not update_success:
            print(f"❌ Falha ao atualizar bala {bullet_id} no DynamoDB")
            send_message_to_connection(api_gateway_client, connection_id, {"type": "error", "message": "Erro ao atualizar bala no servidor"})
            return {"statusCode": 500, "body": "Erro ao atualizar bala"}
        
        print(f"✅ Bala {bullet_id} atualizada com sucesso no DynamoDB")

        # Verifica se a bala saiu da tela
        if (x is not None and y is not None and 
            (float(x) < 0 or float(x) > GAME_WIDTH or float(y) < 0 or float(y) > GAME_HEIGHT)):
            print(f"🗑️ Bala {bullet_id} saiu da tela - removendo")
            delete_bullet_dynamo(bullet_id)  # Remove do DynamoDB
            # Broadcast da remoção da bala
            broadcast_message(api_gateway_client, {
                "type": "bullet_removed",
                "bullet_id": bullet_id,
                "timestamp": int(time.time())
            })
            return {"statusCode": 200, "body": "Bala removida"}

        # Verifica colisões de balas imediatamente após atualização
        print(f"🔍 Verificando colisões para bala {bullet_id}")
        if bullet_id and x is not None and y is not None:
            check_bullet_collisions_immediate(api_gateway_client, str(bullet_id), float(x), float(y))

        # Verifica novamente se a bala ainda existe (pode ter sido removida por colisão)
        try:
            response = bullets_table.get_item(Key={"id": bullet_id})
            bullet_still_exists = response.get("Item") is not None
            
            if bullet_still_exists:
                print(f"✅ Bala {bullet_id} ainda existe após verificação de colisão - enviando broadcast")
                # Se não houve colisão, broadcast da nova posição para outros clientes
                broadcast_message(api_gateway_client, {
                    "type": "bullet_position_update",
                    "bullet_id": bullet_id,
                    "x": x,
                    "y": y,
                    "timestamp": int(time.time())
                }, exclude_connection=connection_id)
            else:
                print(f"🗑️ Bala {bullet_id} foi removida por colisão - não enviando broadcast")
        except Exception as e:
            print(f"❌ Erro ao verificar se bala ainda existe: {e}")

        return {"statusCode": 200, "body": "Posição da bala atualizada"}

    except Exception as e:
        print(f"❌ Erro ao processar atualização de bala: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"statusCode": 500, "body": f"Erro ao processar atualização de bala: {str(e)}"}





def check_bullet_collisions_immediate(api_gateway_client, bullet_id: str, bullet_x: float, bullet_y: float):
    """
    Verifica colisões de uma bala específica imediatamente
    """
    try:
        current_time = int(time.time())
        active_players = get_active_players()
        
        print(f"🎯 Verificação imediata de colisão para bala {bullet_id} em ({bullet_x:.1f}, {bullet_y:.1f})")

        if not active_players:
            print("   👥 Nenhum jogador ativo para verificar")
            return False

        # Busca a bala específica no DynamoDB
        try:
            response = bullets_table.get_item(Key={"id": bullet_id})
            bullet = response.get("Item")
            
            if not bullet:
                print(f"   ❌ Bala {bullet_id} não encontrada no DynamoDB")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao buscar bala {bullet_id}: {e}")
            return False

        # Verifica colisão com jogadores
        for player_id, player_data in active_players.items():
            if player_data.get("team") == bullet["shooter_team"]:
                continue  # Não atira no próprio time

            player_x = player_data.get("x", 0)
            player_y = player_data.get("y", 0)
            player_hp = player_data.get("hp", PLAYER_MAX_HP)
            
            # Distância entre projétil e jogador
            if (bullet_x is not None and bullet_y is not None and 
                player_x is not None and player_y is not None):
                dx = bullet_x - player_x
                dy = bullet_y - player_y
                distance = math.sqrt(dx*dx + dy*dy)

                print(f"   vs jogador {player_id} ({player_x:.1f}, {player_y:.1f}) - distância: {distance:.2f}")

                # Raio de colisão de 30 pixels
                if distance < 30:
                    print(f"🎯 COLISÃO IMEDIATA DETECTADA! Bala {bullet_id} atingiu jogador {player_id}")
                    
                    # Atingiu jogador
                    current_hp = player_data.get("hp", PLAYER_MAX_HP)
                    if isinstance(current_hp, Decimal):
                        current_hp = float(current_hp)
                    
                    new_hp = max(0, current_hp - BULLET_DAMAGE)
                    print(f"   HP atual: {current_hp} -> Novo HP: {new_hp}")
                    
                    # Atualiza HP no DynamoDB
                    player_connection_id = get_connection_by_player_id(player_id)
                    
                    if player_connection_id:
                        try:
                            connections_table.update_item(
                                Key={"connection_id": player_connection_id},
                                UpdateExpression="SET hp = :hp, last_activity = :time",
                                ExpressionAttributeValues={
                                    ":hp": Decimal(str(new_hp)),
                                    ":time": current_time
                                }
                            )
                            print(f"   ✅ HP atualizado no DynamoDB para {new_hp}")
                        except Exception as e:
                            print(f"   ❌ Erro ao atualizar HP no DynamoDB: {e}")
                            return False

                    # Remove a bala
                    delete_bullet_dynamo(bullet_id)

                    # Broadcast do dano e remoção da bala
                    broadcast_message(api_gateway_client, {
                        "type": "player_hit",
                        "player_id": player_id,
                        "damage": BULLET_DAMAGE,
                        "new_hp": new_hp,
                        "shooter_id": bullet["shooter_id"],
                        "timestamp": current_time
                    })

                    broadcast_message(api_gateway_client, {
                        "type": "player_hp_update",
                        "player_id": player_id,
                        "hp": new_hp,
                        "timestamp": current_time
                    })

                    broadcast_message(api_gateway_client, {
                        "type": "bullet_removed",
                        "bullet_id": bullet_id,
                        "timestamp": current_time
                    })

                    return True  # Colisão detectada e processada

        return False  # Nenhuma colisão detectada

    except Exception as e:
        print(f"❌ Erro na verificação imediata de colisões: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_bullet_collisions_periodic(api_gateway_client):
    """
    Verifica colisões de balas com jogadores periodicamente
    """
    try:
        current_time = int(time.time())
        active_players = get_active_players()
        bullets_to_remove = []

        # Busca todas as balas do DynamoDB
        bullets = get_all_bullets_dynamo()
        print(f"🔍 Verificação periódica de colisões - {len(bullets)} balas do DynamoDB, {len(active_players)} jogadores")

        if not bullets:
            print("   📭 Nenhuma bala para verificar")
            return

        if not active_players:
            print("   👥 Nenhum jogador ativo para verificar")
            return

        for bullet in bullets:
            # Remove projéteis antigos (mais de 30 segundos) ou que expiraram o TTL
            bullet_ttl = bullet.get("ttl", 0)
            if current_time - bullet["created_at"] > 30 or current_time > bullet_ttl:
                bullets_to_remove.append(bullet)
                reason = "TTL expirado" if current_time > bullet_ttl else "antiga"
                print(f"   🗑️ Bala {bullet['id']} removida ({reason})")
                continue

            # Converte valores Decimal para float para comparação
            bullet_x = bullet.get("x", 0)
            bullet_y = bullet.get("y", 0)
            
            if isinstance(bullet_x, Decimal):
                bullet_x = float(bullet_x)
            if isinstance(bullet_y, Decimal):
                bullet_y = float(bullet_y)

            print(f"   🎯 Verificando bala {bullet['id']} ({bullet_x:.1f}, {bullet_y:.1f}) - Time: {bullet['shooter_team']}")

            # Verifica colisão com jogadores
            for player_id, player_data in active_players.items():
                if player_data.get("team") == bullet["shooter_team"]:
                    print(f"      ⏸️ Pulando jogador {player_id} (mesmo time)")
                    continue  # Não atira no próprio time

                player_x = player_data.get("x", 0)
                player_y = player_data.get("y", 0)
                player_hp = player_data.get("hp", PLAYER_MAX_HP)
                print(f"      🎯 Verificando jogador {player_id} - HP atual: {player_hp} (tipo: {type(player_hp)})")
                
                # Distância entre projétil e jogador
                if (bullet_x is not None and bullet_y is not None and 
                    player_x is not None and player_y is not None):
                    dx = bullet_x - player_x
                    dy = bullet_y - player_y
                    distance = math.sqrt(dx*dx + dy*dy)

                    print(f"      vs jogador {player_id} ({player_x:.1f}, {player_y:.1f}) - distância: {distance:.2f}")

                    # Aumenta o raio de colisão para 30 pixels
                    if distance < 30:  # Raio de colisão aumentado
                        print(f"🎯 COLISÃO DETECTADA! Bala {bullet['id']} atingiu jogador {player_id}")
                        print(f"   HP atual: {player_data.get('hp', PLAYER_MAX_HP)}")
                        print(f"   Dano: {BULLET_DAMAGE}")
                        
                        # Atingiu jogador
                        current_hp = player_data.get("hp", PLAYER_MAX_HP)
                        # Converte Decimal para float se necessário
                        if isinstance(current_hp, Decimal):
                            current_hp = float(current_hp)
                        
                        new_hp = max(0, current_hp - BULLET_DAMAGE)
                        print(f"   HP atual: {current_hp}")
                        print(f"   Novo HP: {new_hp}")
                        
                        # Atualiza HP no DynamoDB
                        player_connection_id = get_connection_by_player_id(player_id)
                        print(f"   Connection ID encontrado: {player_connection_id}")
                        
                        if player_connection_id:
                            try:
                                connections_table.update_item(
                                    Key={"connection_id": player_connection_id},
                                    UpdateExpression="SET hp = :hp, last_activity = :time",
                                    ExpressionAttributeValues={
                                        ":hp": Decimal(str(new_hp)),  # Converte para Decimal
                                        ":time": current_time
                                    }
                                )
                                print(f"   ✅ HP atualizado no DynamoDB para {new_hp}")
                                
                                # Verifica se foi salvo corretamente
                                try:
                                    verify_response = connections_table.get_item(Key={"connection_id": player_connection_id})
                                    saved_hp = verify_response.get("Item", {}).get("hp")
                                    if isinstance(saved_hp, Decimal):
                                        saved_hp = float(saved_hp)
                                    print(f"   🔍 HP verificado no DynamoDB: {saved_hp}")
                                except Exception as verify_e:
                                    print(f"   ⚠️ Erro ao verificar HP salvo: {verify_e}")
                                    
                            except Exception as e:
                                print(f"   ❌ Erro ao atualizar HP no DynamoDB: {e}")
                        else:
                            print(f"   ❌ Connection ID não encontrado para player {player_id}")

                        # Remove a bala
                        bullets_to_remove.append(bullet)

                        # Broadcast do dano e remoção da bala
                        broadcast_message(api_gateway_client, {
                            "type": "player_hit",
                            "player_id": player_id,
                            "damage": BULLET_DAMAGE,
                            "new_hp": new_hp,
                            "shooter_id": bullet["shooter_id"],
                            "timestamp": current_time
                        })

                        # Broadcast específico de HP para sincronização
                        broadcast_message(api_gateway_client, {
                            "type": "player_hp_update",
                            "player_id": player_id,
                            "hp": new_hp,
                            "timestamp": current_time
                        })

                        broadcast_message(api_gateway_client, {
                            "type": "bullet_removed",
                            "bullet_id": bullet["id"],
                            "timestamp": current_time
                        })

                        break  # Bala já atingiu alguém, não precisa verificar outros jogadores
                    else:
                        print(f"      ❌ Distância muito grande ({distance:.2f} >= 30)")

        # Remove balas processadas do DynamoDB
        for bullet in bullets_to_remove:
            delete_bullet_dynamo(bullet["id"])

        if bullets_to_remove:
            print(f"✅ Verificação periódica concluída - {len(bullets_to_remove)} balas removidas")
        else:
            print(f"✅ Verificação periódica concluída - nenhuma colisão detectada")

    except Exception as e:
        print(f"❌ Erro na verificação periódica de colisões: {str(e)}")
        import traceback
        traceback.print_exc()


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

                # Salva o estado do jogo no DynamoDB
                save_game_state()

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
        
        # Busca balas do DynamoDB
        bullets = get_all_bullets_dynamo()
        
        # Monta o game_state_message
        print("🔍 VERIFICANDO SCORES ANTES DE ENVIAR")
        print(f"🔍 game_state['scores'] original: {game_state['scores']}")
        print(f"🔍 Tipo do game_state['scores']: {type(game_state['scores'])}")
        
        current_scores = game_state["scores"]
        print(f"🎯 Scores que serão enviados no game_state: {current_scores}")
        print(f"🔍 Tipo dos scores: {type(current_scores)}")
        print(f"🔍 Conteúdo dos scores: {current_scores}")
        
        game_state_message = {
            "type": "game_state",
            "players": active_players,
            "flags": game_state["flags"],
            "bullets": bullets,
            "scores": current_scores,
            "teams": TEAMS,
            "timestamp": int(time.time())
        }
        
        print(f"🔍 Scores na mensagem final: {game_state_message['scores']}")
        print(f"🔍 Tipo dos scores na mensagem: {type(game_state_message['scores'])}")
        
        # Converte recursivamente todos os valores Decimal
        print(f"🔧 Convertendo valores Decimal...")
        
        # Log detalhado antes da conversão
        print(f"   game_state antes da conversão:")
        print(f"     - players: {type(active_players)} com {len(active_players)} itens")
        print(f"     - flags: {type(game_state['flags'])}")
        print(f"     - bullets: {type(bullets)} com {len(bullets)} itens do DynamoDB")
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


def get_connection_by_player_id(player_id: str) -> str | None:
    """
    Obtém connection_id pelo player_id
    """
    try:
        print(f"🔍 Buscando connection_id para player {player_id}")
        response = connections_table.scan(
            FilterExpression="player_id = :pid",
            ExpressionAttributeValues={":pid": player_id}
        )
        
        items = response.get("Items", [])
        print(f"   Items encontrados: {len(items)}")
        
        if items:
            connection_id = items[0]["connection_id"]
            print(f"   ✅ Connection ID encontrado: {connection_id}")
            return connection_id
        else:
            print(f"   ❌ Nenhum item encontrado para player {player_id}")
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
            FilterExpression="attribute_exists(player_id) AND player_id <> :null",
            ExpressionAttributeValues={":null": None}
        )
        
        players = {}
        print(f"🔍 Buscando jogadores ativos...")
        
        for item in response.get("Items", []):
            player_id = item.get("player_id")
            if player_id:
                team = item.get("team")
                print(f"   Jogador {player_id} com team: {team}")
                
                # Verifica se o team existe em TEAMS
                if team not in TEAMS:
                    print(f"⚠️ Team '{team}' não encontrado em TEAMS: {list(TEAMS.keys())}")
                    team = "red"  # fallback
                
                # Converte valores Decimal para float
                x = item.get("x", 0)
                y = item.get("y", 0)
                hp = item.get("hp", PLAYER_MAX_HP)
                
                if isinstance(x, Decimal):
                    x = float(x)
                if isinstance(y, Decimal):
                    y = float(y)
                if isinstance(hp, Decimal):
                    hp = float(hp)
                
                players[player_id] = {
                    "team": team,
                    "x": x,
                    "y": y,
                    "hp": hp,
                    "color": TEAMS[team]["color"]
                }
        
        print(f"✅ Encontrados {len(players)} jogadores ativos")
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


def bullet_to_dynamo(bullet):
    """Convert all numeric fields in a bullet to Decimal for DynamoDB."""
    bullet = bullet.copy()
    for key in ['x', 'y', 'dx', 'dy']:
        if key in bullet:
            bullet[key] = Decimal(str(bullet[key]))
    # created_at and ttl should be int, but DynamoDB accepts int or Decimal
    for key in ['created_at', 'ttl']:
        if key in bullet:
            bullet[key] = int(bullet[key])
    return bullet


def save_bullet_dynamo(bullet):
    """Salva uma bala no DynamoDB."""
    try:
        bullet = bullet_to_dynamo(bullet)
        print(f"💾 Tentando salvar bala {bullet['id']} no DynamoDB...")
        print(f"   Dados da bala: {bullet}")
        bullets_table.put_item(Item=bullet)
        print(f"✅ Bala {bullet['id']} salva no DynamoDB com sucesso")
    except Exception as e:
        print(f"❌ Erro ao salvar bala no DynamoDB: {e}")
        import traceback
        traceback.print_exc()


def update_bullet_dynamo(bullet_id, x, y):
    """Atualiza posição da bala no DynamoDB."""
    try:
        print(f"🔧 Tentando atualizar bala {bullet_id} para ({x}, {y})")
        
        # Primeiro verifica se a bala existe
        try:
            response = bullets_table.get_item(Key={"id": bullet_id})
            bullet = response.get("Item")
            
            if not bullet:
                print(f"❌ Bala {bullet_id} não encontrada no DynamoDB para atualização")
                return False
            
            print(f"✅ Bala {bullet_id} encontrada no DynamoDB, atualizando posição...")
        except Exception as e:
            print(f"❌ Erro ao verificar se bala {bullet_id} existe: {e}")
            return False
        
        # Converte para Decimal
        x_decimal = Decimal(str(x))
        y_decimal = Decimal(str(y))
        
        # Atualiza a posição
        bullets_table.update_item(
            Key={"id": bullet_id},
            UpdateExpression="SET x = :x, y = :y",
            ExpressionAttributeValues={":x": x_decimal, ":y": y_decimal}
        )
        print(f"✅ Bala {bullet_id} atualizada no DynamoDB para ({x_decimal}, {y_decimal})")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar bala {bullet_id} no DynamoDB: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_bullet_dynamo(bullet_id):
    """Remove uma bala do DynamoDB."""
    try:
        bullets_table.delete_item(Key={"id": bullet_id})
        print(f"🗑️ Bala {bullet_id} removida do DynamoDB")
    except Exception as e:
        print(f"❌ Erro ao remover bala do DynamoDB: {e}")


def get_all_bullets_dynamo():
    """Busca todas as balas do DynamoDB."""
    try:
        response = bullets_table.scan()
        bullets = response.get("Items", [])
        current_time = time.time()  # Use float aqui
        
        # Filtra balas antigas (mais de 15 segundos)
        filtered_bullets = []
        for bullet in bullets:
            bullet_created = bullet.get("created_at", 0)
            bullet_age = current_time - bullet_created
            if bullet_age < 15:  # Só retorna balas com menos de 15 segundos
                filtered_bullets.append(bullet)
        
        print(f"🔎 {len(bullets)} balas no DynamoDB, {len(filtered_bullets)} balas recentes enviadas - Servidor v{SERVER_VERSION}")
        return filtered_bullets
    except Exception as e:
        print(f"❌ Erro ao buscar balas do DynamoDB: {e}")
        return []
