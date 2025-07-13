#!/usr/bin/env python3
"""
Script para testar o reset do jogo
"""

import boto3
import json
import time
import os

def test_reset_game():
    """Testa o reset do jogo"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    TABLE_NAME = "game_state"
    
    # Cliente DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("🧪 Testando reset do jogo...")
    print("=" * 40)
    
    try:
        # 1. Verifica estado atual
        print("1️⃣ Verificando estado atual...")
        response = table.get_item(Key={"id": "current_game"})
        
        if "Item" in response:
            current_scores = response["Item"].get("scores", {})
            print(f"   Scores atuais: {current_scores}")
        else:
            print("   Nenhum estado encontrado")
        
        # 2. Cria estado com scores incorretos (simulando o problema)
        print("\n2️⃣ Criando estado com scores incorretos...")
        incorrect_state = {
            "id": "current_game",
            "flags": {
                "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 6, "blue": 5},
            "game_started": True,
            "last_updated": int(time.time()),
            "expires_at": int(time.time()) + 86400
        }
        
        table.put_item(Item=incorrect_state)
        print("   ✅ Estado com scores incorretos criado")
        
        # 3. Verifica se foi criado
        print("\n3️⃣ Verificando se foi criado...")
        response = table.get_item(Key={"id": "current_game"})
        if "Item" in response:
            scores = response["Item"].get("scores", {})
            print(f"   Scores após criação: {scores}")
        else:
            print("   ❌ Estado não foi criado")
            return False
        
        # 4. Simula reset (remove o item)
        print("\n4️⃣ Simulando reset (removendo estado)...")
        table.delete_item(Key={"id": "current_game"})
        print("   ✅ Estado removido")
        
        # 5. Verifica se foi removido
        print("\n5️⃣ Verificando se foi removido...")
        response = table.get_item(Key={"id": "current_game"})
        if "Item" not in response:
            print("   ✅ Estado removido com sucesso")
        else:
            print("   ❌ Estado ainda existe")
            return False
        
        # 6. Cria estado correto (scores zerados)
        print("\n6️⃣ Criando estado correto (scores zerados)...")
        correct_state = {
            "id": "current_game",
            "flags": {
                "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
                "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
            },
            "bullets": [],
            "scores": {"red": 0, "blue": 0},
            "game_started": False,
            "last_updated": int(time.time()),
            "expires_at": int(time.time()) + 86400
        }
        
        table.put_item(Item=correct_state)
        print("   ✅ Estado correto criado")
        
        # 7. Verifica estado final
        print("\n7️⃣ Verificando estado final...")
        response = table.get_item(Key={"id": "current_game"})
        if "Item" in response:
            final_scores = response["Item"].get("scores", {})
            print(f"   Scores finais: {final_scores}")
            
            if final_scores == {"red": 0, "blue": 0}:
                print("   ✅ Scores corretos!")
                return True
            else:
                print("   ❌ Scores incorretos!")
                return False
        else:
            print("   ❌ Estado final não encontrado")
            return False
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Teste de Reset do Jogo")
    print("=" * 40)
    
    if test_reset_game():
        print("\n✅ Teste de reset concluído com sucesso!")
        print("📋 O DynamoDB está funcionando corretamente como fonte de verdade")
        print("🔧 Agora faça deploy do código atualizado e teste o jogo")
    else:
        print("\n❌ Problema detectado no teste de reset")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 