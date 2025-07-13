#!/usr/bin/env python3
"""
Script para limpar e verificar a tabela game_state
"""

import boto3
import json
import time
import os

def clear_game_state():
    """Limpa a tabela game_state e verifica se há dados"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    TABLE_NAME = "game_state"
    
    # Cliente DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("🧹 Limpando tabela game_state...")
    print("=" * 40)
    
    try:
        # Verifica se há dados
        print("1️⃣ Verificando dados existentes...")
        response = table.get_item(Key={"id": "current_game"})
        
        if "Item" in response:
            item = response["Item"]
            print(f"   📊 Dados encontrados:")
            print(f"      - Scores: {item.get('scores')}")
            print(f"      - Game Started: {item.get('game_started')}")
            print(f"      - Last Updated: {item.get('last_updated')}")
            
            # Remove os dados
            print("\n2️⃣ Removendo dados...")
            table.delete_item(Key={"id": "current_game"})
            print("   ✅ Dados removidos com sucesso!")
        else:
            print("   📝 Nenhum dado encontrado na tabela")
        
        # Verifica novamente
        print("\n3️⃣ Verificando se a tabela está limpa...")
        response = table.get_item(Key={"id": "current_game"})
        
        if "Item" not in response:
            print("   ✅ Tabela está limpa!")
            
            # Cria estado inicial limpo
            print("\n4️⃣ Criando estado inicial limpo...")
            initial_state = {
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
            
            table.put_item(Item=initial_state)
            print("   ✅ Estado inicial criado: scores = {'red': 0, 'blue': 0}")
            
        else:
            print("   ❌ Erro: Dados ainda presentes na tabela")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Limpeza da Tabela game_state")
    print("=" * 40)
    
    if clear_game_state():
        print("\n🎉 Tabela game_state limpa e resetada com sucesso!")
        print("📋 Agora o jogo deve iniciar com scores zerados")
    else:
        print("\n❌ Falha ao limpar a tabela")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 