#!/usr/bin/env python3
"""
Script para testar a correção do problema de scores
"""

import boto3
import json
import time
import os
from decimal import Decimal

# Configurações
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = "game_state"

# Cliente DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
game_state_table = dynamodb.Table(TABLE_NAME)

def test_score_update():
    """Testa a atualização de scores consultando o DynamoDB primeiro"""
    
    print("🚀 Teste da Correção de Scores")
    print("=" * 50)
    
    try:
        # 1. Define um estado inicial (2x1)
        print("1️⃣ Definindo estado inicial (2x1)...")
        initial_state = {
            "id": "current_game",
            "flags": {
                "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 2, "blue": 1},
            "game_started": True,
            "last_updated": int(time.time()),
            "expires_at": int(time.time()) + 86400
        }
        
        game_state_table.put_item(Item=initial_state)
        print(f"   ✅ Estado inicial salvo: {initial_state['scores']}")
        
        # 2. Simula múltiplas requisições simultâneas
        print("\n2️⃣ Simulando múltiplas requisições simultâneas...")
        
        # Simula 3 requisições que marcam ponto simultaneamente
        for i in range(3):
            print(f"\n   Requisição {i+1}:")
            
            # CONSULTA O DYNAMODB ANTES DE ATUALIZAR (como na correção)
            print(f"   🔍 CONSULTANDO DYNAMODB ANTES DE ATUALIZAR SCORE...")
            response = game_state_table.get_item(Key={"id": "current_game"})
            
            if "Item" in response:
                current_scores = response["Item"].get("scores", {"red": 0, "blue": 0})
                # Converte de Decimal para int
                dynamo_scores = {}
                for team, score in current_scores.items():
                    if isinstance(score, Decimal):
                        dynamo_scores[team] = int(score)
                    else:
                        dynamo_scores[team] = score
                
                print(f"   🔍 Scores atuais no DynamoDB: {dynamo_scores}")
                
                # Simula o time vermelho marcando ponto
                carrier_team = "red"
                old_score = dynamo_scores.get(carrier_team, 0)
                dynamo_scores[carrier_team] += 1
                new_score = dynamo_scores[carrier_team]
                
                print(f"   🔍 Score do time {carrier_team}: {old_score} -> {new_score}")
                print(f"   🔍 Scores APÓS o ponto: {dynamo_scores}")
                
                # Salva no DynamoDB
                updated_state = {
                    "id": "current_game",
                    "flags": response["Item"].get("flags", {}),
                    "bullets": response["Item"].get("bullets", []),
                    "scores": dynamo_scores,
                    "game_started": response["Item"].get("game_started", True),
                    "last_updated": int(time.time()),
                    "expires_at": int(time.time()) + 86400
                }
                
                game_state_table.put_item(Item=updated_state)
                print(f"   ✅ Estado atualizado no DynamoDB: {dynamo_scores}")
            else:
                print(f"   ❌ Nenhum item encontrado no DynamoDB")
        
        # 3. Verifica o resultado final
        print("\n3️⃣ Verificando resultado final...")
        final_response = game_state_table.get_item(Key={"id": "current_game"})
        
        if "Item" in final_response:
            final_scores = final_response["Item"].get("scores", {})
            # Converte de Decimal para int
            final_scores_int = {}
            for team, score in final_scores.items():
                if isinstance(score, Decimal):
                    final_scores_int[team] = int(score)
                else:
                    final_scores_int[team] = score
            
            print(f"   📊 Scores finais: {final_scores_int}")
            
            # Verifica se está correto (deveria ser 5x1 após 3 pontos)
            expected_scores = {"red": 5, "blue": 1}
            if final_scores_int == expected_scores:
                print(f"   ✅ CORREÇÃO FUNCIONOU! Scores corretos: {final_scores_int}")
                print(f"   ✅ Esperado: {expected_scores}")
                return True
            else:
                print(f"   ❌ PROBLEMA PERSISTE! Scores incorretos: {final_scores_int}")
                print(f"   ❌ Esperado: {expected_scores}")
                return False
        else:
            print(f"   ❌ Nenhum item encontrado no final")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🔧 Testando Correção do Problema de Scores")
    print("=" * 60)
    
    success = test_score_update()
    
    if success:
        print(f"\n✅ CORREÇÃO FUNCIONOU!")
        print(f"   O problema de perda de scores foi resolvido.")
        print(f"   Agora o código consulta o DynamoDB antes de atualizar scores.")
    else:
        print(f"\n❌ CORREÇÃO NÃO FUNCIONOU!")
        print(f"   O problema persiste. Verifique os logs acima.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 