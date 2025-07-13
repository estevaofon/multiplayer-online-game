#!/usr/bin/env python3
"""
Script para verificar se há múltiplas instâncias do Lambda causando problemas
"""

import boto3
import json
import time
import os
from datetime import datetime, timedelta

def check_lambda_instances():
    """Verifica se há múltiplas instâncias do Lambda rodando"""
    
    # Configurações
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    FUNCTION_NAME = "websocket-game-handler"  # Ajuste para o nome correto da sua função
    
    # Cliente CloudWatch Logs
    logs_client = boto3.client('logs', region_name=AWS_REGION)
    
    print("🔍 Verificando instâncias do Lambda...")
    print("=" * 50)
    
    try:
        # Busca logs das últimas 24 horas
        end_time = int(time.time() * 1000)
        start_time = end_time - (24 * 60 * 60 * 1000)  # 24 horas atrás
        
        print(f"🔍 Buscando logs de {datetime.fromtimestamp(start_time/1000)} até {datetime.fromtimestamp(end_time/1000)}")
        
        # Busca logs que contenham "load_game_state" ou "save_game_state"
        response = logs_client.filter_log_events(
            logGroupName=f"/aws/lambda/{FUNCTION_NAME}",
            startTime=start_time,
            endTime=end_time,
            filterPattern='load_game_state OR save_game_state OR "Scores ANTES" OR "Scores APÓS"',
            limit=100
        )
        
        print(f"📊 Encontrados {len(response.get('events', []))} eventos relevantes")
        
        # Agrupa por timestamp para identificar instâncias simultâneas
        events_by_time = {}
        
        for event in response.get('events', []):
            timestamp = event['timestamp']
            message = event['message']
            
            # Normaliza timestamp para agrupar por segundo
            time_key = timestamp // 1000
            
            if time_key not in events_by_time:
                events_by_time[time_key] = []
            
            events_by_time[time_key].append({
                'timestamp': timestamp,
                'message': message,
                'logStreamName': event['logStreamName']
            })
        
        print(f"📊 Eventos agrupados por segundo: {len(events_by_time)} grupos")
        
        # Verifica se há múltiplos log streams simultâneos (indicando múltiplas instâncias)
        concurrent_instances = 0
        
        for time_key, events in events_by_time.items():
            if len(events) > 1:
                log_streams = set(event['logStreamName'] for event in events)
                if len(log_streams) > 1:
                    concurrent_instances += 1
                    print(f"⚠️ Múltiplas instâncias detectadas em {datetime.fromtimestamp(time_key)}:")
                    print(f"   Log streams: {list(log_streams)}")
                    print(f"   Eventos: {len(events)}")
                    for event in events:
                        print(f"     - {event['logStreamName']}: {event['message'][:100]}...")
                    print()
        
        if concurrent_instances > 0:
            print(f"❌ PROBLEMA DETECTADO: {concurrent_instances} momentos com múltiplas instâncias!")
            print("   Isso pode causar conflitos no estado do jogo.")
        else:
            print("✅ Nenhuma instância simultânea detectada")
        
        # Busca logs específicos de scores
        print(f"\n🔍 Buscando logs específicos de scores...")
        score_response = logs_client.filter_log_events(
            logGroupName=f"/aws/lambda/{FUNCTION_NAME}",
            startTime=start_time,
            endTime=end_time,
            filterPattern='"Scores ANTES" OR "Scores APÓS" OR "Scores carregados" OR "Scores convertidos"',
            limit=50
        )
        
        print(f"📊 Encontrados {len(score_response.get('events', []))} eventos de scores")
        
        for event in score_response.get('events', []):
            timestamp = datetime.fromtimestamp(event['timestamp']/1000)
            message = event['message']
            print(f"   {timestamp}: {message.strip()}")
        
        return concurrent_instances > 0
        
    except Exception as e:
        print(f"❌ Erro ao verificar instâncias: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dynamodb_consistency():
    """Verifica a consistência dos dados no DynamoDB"""
    
    print(f"\n🔍 Verificando consistência do DynamoDB...")
    print("=" * 50)
    
    try:
        # Cliente DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name=os.environ.get("AWS_REGION", "us-east-1"))
        table = dynamodb.Table("game_state")
        
        # Faz múltiplas leituras para verificar consistência
        readings = []
        
        for i in range(5):
            response = table.get_item(Key={"id": "current_game"})
            if "Item" in response:
                scores = response["Item"].get("scores", {})
                readings.append(scores)
                print(f"   Leitura {i+1}: {scores}")
            else:
                readings.append(None)
                print(f"   Leitura {i+1}: Nenhum item encontrado")
        
        # Verifica se todas as leituras são iguais
        if all(r == readings[0] for r in readings):
            print("✅ Consistência do DynamoDB: OK")
            return True
        else:
            print("❌ PROBLEMA: Inconsistência detectada no DynamoDB!")
            print("   Leituras diferentes encontradas:")
            for i, reading in enumerate(readings):
                print(f"     Leitura {i+1}: {reading}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar consistência: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Verificação de Instâncias Lambda e Consistência")
    print("=" * 60)
    
    # Verifica instâncias
    has_concurrent_instances = check_lambda_instances()
    
    # Verifica consistência
    is_consistent = check_dynamodb_consistency()
    
    print(f"\n📋 Resumo:")
    print(f"   Múltiplas instâncias: {'❌ SIM' if has_concurrent_instances else '✅ NÃO'}")
    print(f"   Consistência DynamoDB: {'✅ OK' if is_consistent else '❌ PROBLEMA'}")
    
    if has_concurrent_instances or not is_consistent:
        print(f"\n🔧 Recomendações:")
        if has_concurrent_instances:
            print("   - Configure provisioned concurrency para evitar múltiplas instâncias")
            print("   - Use DynamoDB transactions para operações críticas")
        if not is_consistent:
            print("   - Verifique se há operações concorrentes no DynamoDB")
            print("   - Considere usar DynamoDB transactions")
        
        return 1
    else:
        print(f"\n✅ Sistema funcionando corretamente!")
        return 0

if __name__ == "__main__":
    exit(main()) 