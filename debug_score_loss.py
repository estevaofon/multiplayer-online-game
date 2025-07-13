#!/usr/bin/env python3
"""
Script para investigar a perda de scores
"""

import boto3
import json
import time
import os

def investigate_score_loss():
    """Investiga a perda de scores"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    TABLE_NAME = "game_state"
    
    # Cliente DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("🔍 Investigando perda de scores...")
    print("=" * 50)
    
    try:
        # 1. Verifica estado atual
        print("1️⃣ Estado atual da tabela game_state:")
        response = table.get_item(Key={"id": "current_game"})
        
        if "Item" in response:
            item = response["Item"]
            scores = item.get("scores", {})
            print(f"   ✅ Item encontrado")
            print(f"   📊 Scores atuais: {scores}")
            print(f"   🔍 Tipo dos scores: {type(scores)}")
            print(f"   📅 Última atualização: {item.get('last_updated')}")
            print(f"   🎮 Jogo iniciado: {item.get('game_started')}")
            
            # Verifica se há problemas com os scores
            red_score = scores.get("red", 0)
            blue_score = scores.get("blue", 0)
            
            print(f"   🔴 Score vermelho: {red_score} (tipo: {type(red_score)})")
            print(f"   🔵 Score azul: {blue_score} (tipo: {type(blue_score)})")
            
            # Se os scores estão como Decimal, converte para int
            if isinstance(red_score, float):
                red_score = int(red_score)
            if isinstance(blue_score, float):
                blue_score = int(blue_score)
                
            print(f"   🔴 Score vermelho (convertido): {red_score}")
            print(f"   🔵 Score azul (convertido): {blue_score}")
            
        else:
            print("   ❌ Nenhum item encontrado na tabela")
            return False
        
        # 2. Simula o problema (2x1 -> 0x1)
        print("\n2️⃣ Simulando o problema (2x1 -> 0x1):")
        
        # Cria estado com 2x1
        state_2x1 = {
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
        
        print(f"   📊 Salvando estado 2x1: {state_2x1['scores']}")
        table.put_item(Item=state_2x1)
        
        # Verifica se foi salvo
        response = table.get_item(Key={"id": "current_game"})
        if "Item" in response:
            saved_scores = response["Item"].get("scores", {})
            print(f"   ✅ Estado salvo: {saved_scores}")
        else:
            print("   ❌ Falha ao salvar estado")
            return False
        
        # 3. Simula incremento de ponto (deveria ser 3x1)
        print("\n3️⃣ Simulando incremento de ponto (deveria ser 3x1):")
        
        # Simula o que acontece no código
        game_state_simulation = {
            "scores": {"red": 2, "blue": 1}
        }
        
        print(f"   📊 Estado simulado antes: {game_state_simulation['scores']}")
        
        # Incrementa ponto do time vermelho
        game_state_simulation["scores"]["red"] += 1
        
        print(f"   📊 Estado simulado depois: {game_state_simulation['scores']}")
        
        # Salva o estado atualizado
        state_3x1 = {
            "id": "current_game",
            "flags": {
                "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": game_state_simulation["scores"],
            "game_started": True,
            "last_updated": int(time.time()),
            "expires_at": int(time.time()) + 86400
        }
        
        print(f"   📊 Salvando estado 3x1: {state_3x1['scores']}")
        table.put_item(Item=state_3x1)
        
        # Verifica se foi salvo corretamente
        response = table.get_item(Key={"id": "current_game"})
        if "Item" in response:
            final_scores = response["Item"].get("scores", {})
            print(f"   ✅ Estado final salvo: {final_scores}")
            
            if final_scores == {"red": 3, "blue": 1}:
                print("   ✅ Incremento funcionou corretamente!")
            else:
                print("   ❌ Problema no incremento!")
                print(f"      Esperado: {{'red': 3, 'blue': 1}}")
                print(f"      Obtido: {final_scores}")
        else:
            print("   ❌ Falha ao verificar estado final")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante investigação: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    print("🚀 Investigação de Perda de Scores")
    print("=" * 50)
    
    if investigate_score_loss():
        print("\n✅ Investigação concluída!")
        print("📋 Verifique os logs acima para identificar o problema")
    else:
        print("\n❌ Falha na investigação")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 