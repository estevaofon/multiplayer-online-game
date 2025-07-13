#!/usr/bin/env python3
"""
Script para testar a função load_game_state
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
        import traceback
        traceback.print_exc()
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

def main():
    """Função principal"""
    print("🚀 Teste da Função load_game_state")
    print("=" * 50)
    
    # Testa a função
    game_state = load_game_state()
    
    print(f"\n🎮 Estado final carregado:")
    print(f"   Scores: {game_state['scores']}")
    print(f"   Tipo dos scores: {type(game_state['scores'])}")
    print(f"   Game started: {game_state['game_started']}")
    
    # Verifica se os scores estão corretos
    red_score = game_state['scores'].get('red', 0)
    blue_score = game_state['scores'].get('blue', 0)
    
    print(f"\n🔍 Verificação final:")
    print(f"   🔴 Score vermelho: {red_score} (tipo: {type(red_score)})")
    print(f"   🔵 Score azul: {blue_score} (tipo: {type(blue_score)})")
    
    # Verifica se os scores são números inteiros
    if isinstance(red_score, int) and isinstance(blue_score, int):
        print("✅ Scores são números inteiros corretamente!")
    else:
        print("❌ Problema: Scores não são números inteiros!")
        print(f"   Red: {type(red_score)}")
        print(f"   Blue: {type(blue_score)}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 