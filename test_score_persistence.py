#!/usr/bin/env python3
"""
Script de teste para verificar persistência de scores
"""

import boto3
import json
import time
import os

def test_score_persistence():
    """Testa a persistência de scores no DynamoDB"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    TABLE_NAME = "game_state"
    
    # Cliente DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("🧪 Testando persistência de scores...")
    print("=" * 40)
    
    try:
        # Teste 1: Salvar scores
        print("1️⃣ Salvando scores de teste...")
        test_scores = {"red": 5, "blue": 3}
        
        table.put_item(
            Item={
                "id": "current_game",
                "flags": {
                    "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                    "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
                },
                "bullets": [],
                "scores": test_scores,
                "game_started": True,
                "last_updated": int(time.time()),
                "expires_at": int(time.time()) + 86400
            }
        )
        print(f"   ✅ Scores salvos: {test_scores}")
        
        # Teste 2: Carregar scores
        print("\n2️⃣ Carregando scores...")
        response = table.get_item(Key={"id": "current_game"})
        
        if "Item" in response:
            loaded_scores = response["Item"]["scores"]
            print(f"   ✅ Scores carregados: {loaded_scores}")
            
            # Verificar se são iguais
            if loaded_scores == test_scores:
                print("   ✅ Scores persistem corretamente!")
            else:
                print("   ❌ Scores não persistem corretamente!")
                return False
        else:
            print("   ❌ Não foi possível carregar os scores!")
            return False
        
        # Teste 3: Simular incremento de score
        print("\n3️⃣ Simulando incremento de score...")
        test_scores["red"] += 1
        test_scores["blue"] += 2
        
        table.put_item(
            Item={
                "id": "current_game",
                "flags": {
                    "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                    "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
                },
                "bullets": [],
                "scores": test_scores,
                "game_started": True,
                "last_updated": int(time.time()),
                "expires_at": int(time.time()) + 86400
            }
        )
        print(f"   ✅ Novos scores salvos: {test_scores}")
        
        # Verificar novamente
        response = table.get_item(Key={"id": "current_game"})
        if "Item" in response:
            final_scores = response["Item"]["scores"]
            print(f"   ✅ Scores finais carregados: {final_scores}")
            
            if final_scores == test_scores:
                print("   ✅ Incremento de scores funciona corretamente!")
            else:
                print("   ❌ Incremento de scores não funciona!")
                return False
        else:
            print("   ❌ Não foi possível carregar os scores finais!")
            return False
        
        print("\n🎉 Todos os testes passaram!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Teste de Persistência de Scores")
    print("=" * 40)
    
    if test_score_persistence():
        print("\n✅ Sistema de persistência funcionando corretamente!")
        print("📋 Os scores agora serão mantidos entre reinicializações do servidor")
    else:
        print("\n❌ Problemas detectados no sistema de persistência")
        print("🔧 Verifique se a tabela game_state foi criada corretamente")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 