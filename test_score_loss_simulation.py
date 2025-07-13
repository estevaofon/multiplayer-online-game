#!/usr/bin/env python3
"""
Script para simular o problema de perda de scores
"""

import boto3
import json
import time
import os
from decimal import Decimal

# Simula as configurações do servidor
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = "game_state"

# Cliente DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
game_state_table = dynamodb.Table(TABLE_NAME)

# Simula TEAMS
TEAMS = {
    "red": {
        "flag_x": 50,
        "flag_y": 300
    },
    "blue": {
        "flag_x": 750,
        "flag_y": 300
    }
}

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

def load_game_state():
    """Carrega o estado do jogo do DynamoDB"""
    try:
        print("🔄 Carregando estado do jogo do DynamoDB...")
        
        response = game_state_table.get_item(Key={"id": "current_game"})
        
        if "Item" in response:
            item = response["Item"]
            print(f"✅ Estado do jogo carregado do DynamoDB")
            
            loaded_scores = item.get("scores", {"red": 0, "blue": 0})
            print(f"🔍 Scores carregados do DynamoDB: {loaded_scores}")
            print(f"🔍 Tipo dos scores: {type(loaded_scores)}")
            
            # Converte scores de Decimal para int
            converted_scores = {}
            for team, score in loaded_scores.items():
                if isinstance(score, Decimal):
                    converted_scores[team] = int(score)
                    print(f"🔍 Convertendo {team}: {score} (Decimal) -> {int(score)} (int)")
                else:
                    converted_scores[team] = score
                    print(f"🔍 Mantendo {team}: {score} (tipo: {type(score)})")
            
            print(f"🔍 Scores convertidos: {converted_scores}")
            
            result = {
                "flags": item.get("flags", {
                    "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                    "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
                }),
                "bullets": item.get("bullets", []),
                "scores": converted_scores,
                "game_started": item.get("game_started", False)
            }
            
            return result
        else:
            print("📝 NENHUM ESTADO PERSISTIDO ENCONTRADO - USANDO ESTADO PADRÃO")
            default_scores = {"red": 0, "blue": 0}
            
            result = {
                "flags": {
                    "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                    "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
                },
                "bullets": [],
                "scores": default_scores,
                "game_started": False
            }
            
            return result
    except Exception as e:
        print(f"❌ Erro ao carregar estado do jogo: {str(e)}")
        return {
            "flags": {
                "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
                "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 0, "blue": 0},
            "game_started": False
        }

def simulate_send_game_state(game_state):
    """Simula a função send_game_state"""
    try:
        print("🔍 Simulando send_game_state...")
        
        # Simula jogadores ativos
        active_players = {
            "player1": {"team": "red", "x": 100, "y": 300, "hp": 100, "color": [255, 100, 100]},
            "player2": {"team": "blue", "x": 700, "y": 300, "hp": 100, "color": [100, 100, 255]}
        }
        
        # Simula balas
        bullets = []
        
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
        print(f"     - bullets: {type(bullets)} com {len(bullets)} itens")
        print(f"     - scores: {type(game_state['scores'])}")
        print(f"     - teams: {type(TEAMS)}")
        
        game_state_message = convert_decimals_recursive(game_state_message)
        print(f"✅ Conversão Decimal concluída")
        
        print(f"🔍 Mensagem final após conversão:")
        print(f"   Scores na mensagem: {game_state_message['scores']}")
        print(f"   Tipo dos scores: {type(game_state_message['scores'])}")
        
        return game_state_message
        
    except Exception as e:
        print(f"❌ Erro ao simular send_game_state: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Função principal"""
    print("🚀 Simulação do Problema de Perda de Scores")
    print("=" * 60)
    
    # 1. Carrega o estado atual
    print("1️⃣ Carregando estado atual...")
    game_state = load_game_state()
    print(f"   Estado carregado: scores={game_state['scores']}")
    
    # 2. Simula o que acontece quando um jogador entra
    print("\n2️⃣ Simulando entrada de jogador...")
    game_state_message = simulate_send_game_state(game_state)
    
    if game_state_message:
        print(f"\n3️⃣ Resultado final:")
        print(f"   Scores originais: {game_state['scores']}")
        print(f"   Scores na mensagem: {game_state_message['scores']}")
        
        # Verifica se houve perda
        original_red = game_state['scores'].get('red', 0)
        original_blue = game_state['scores'].get('blue', 0)
        message_red = game_state_message['scores'].get('red', 0)
        message_blue = game_state_message['scores'].get('blue', 0)
        
        if original_red != message_red or original_blue != message_blue:
            print("❌ PROBLEMA DETECTADO: Scores foram modificados!")
            print(f"   🔴 Vermelho: {original_red} -> {message_red}")
            print(f"   🔵 Azul: {original_blue} -> {message_blue}")
        else:
            print("✅ Scores mantidos corretamente!")
            print(f"   🔴 Vermelho: {original_red}")
            print(f"   🔵 Azul: {original_blue}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 