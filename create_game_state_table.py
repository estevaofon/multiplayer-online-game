#!/usr/bin/env python3
"""
Script para criar a tabela game_state no DynamoDB
"""

import boto3
import os
from botocore.exceptions import ClientError

def create_game_state_table():
    """Cria a tabela game_state no DynamoDB"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    TABLE_NAME = "game_state"
    
    # Cliente DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    
    try:
        # Verifica se a tabela já existe
        try:
            table = dynamodb.Table(TABLE_NAME)
            table.load()
            print(f"✅ Tabela {TABLE_NAME} já existe")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"📝 Tabela {TABLE_NAME} não existe, criando...")
            else:
                raise
        
        # Cria a tabela
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Aguarda a tabela ficar ativa
        print("⏳ Aguardando tabela ficar ativa...")
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        
        # Configura TTL após a tabela estar ativa
        print("⏳ Configurando TTL...")
        dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)
        dynamodb_client.update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'expires_at'
            }
        )
        
        # Aguarda a tabela ficar ativa
        print("⏳ Aguardando tabela ficar ativa...")
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        
        print(f"✅ Tabela {TABLE_NAME} criada com sucesso!")
        print(f"   - Partition Key: id (String)")
        print(f"   - Billing Mode: PAY_PER_REQUEST")
        print(f"   - TTL: expires_at")
        
        return True
        
    except ClientError as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Criando tabela game_state no DynamoDB")
    print("=" * 40)
    
    if create_game_state_table():
        print("\n🎉 Tabela game_state criada/verificada com sucesso!")
        print("\n📋 A tabela será usada para persistir:")
        print("   - Scores dos times")
        print("   - Estado das bandeiras")
        print("   - Estado do jogo")
        print("   - Balas ativas")
    else:
        print("\n❌ Falha ao criar tabela game_state")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 
