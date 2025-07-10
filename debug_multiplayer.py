#!/usr/bin/env python3
"""
Script de Debug - Problema Multiplayer
"""

import os
import websocket
import json
import time
from dotenv import load_dotenv

load_dotenv()

def debug_multiplayer():
    """Debug do problema multiplayer"""
    
    websocket_url = os.getenv("WEBSOCKET_URL")
    
    if not websocket_url:
        print("❌ WEBSOCKET_URL não configurada")
        return
    
    print(f"🌐 Conectando em: {websocket_url}")
    
    # Contadores para debug
    message_count = 0
    player_joined_count = 0
    player_update_count = 0
    game_state_count = 0
    
    def on_message(ws, message):
        nonlocal message_count, player_joined_count, player_update_count, game_state_count
        
        message_count += 1
        print(f"\n📨 Mensagem #{message_count}:")
        
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            print(f"   Tipo: {msg_type}")
            print(f"   Dados: {json.dumps(data, indent=2)}")
            
            if msg_type == "player_joined":
                player_joined_count += 1
                print(f"   ✅ player_joined #{player_joined_count}")
                
            elif msg_type == "player_update":
                player_update_count += 1
                print(f"   ✅ player_update #{player_update_count}")
                
            elif msg_type == "game_state":
                game_state_count += 1
                players = data.get("players", {})
                print(f"   ✅ game_state #{game_state_count} - {len(players)} jogadores")
                for pid, pdata in players.items():
                    print(f"      Jogador {pid}: {pdata}")
                    
        except json.JSONDecodeError:
            print(f"   ❌ Mensagem não-JSON: {message}")
    
    def on_error(ws, error):
        print(f"❌ Erro: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Fechado: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        print("✅ Conectado!")
        
        # Simula entrada de jogador
        join_message = {
            "action": "join",
            "player_id": f"debug_{int(time.time())}",
            "team": "red",
            "x": 100,
            "y": 300
        }
        
        print(f"📤 Enviando join: {join_message}")
        ws.send(json.dumps(join_message))
        
        # Simula movimento
        time.sleep(2)
        update_message = {
            "action": "update",
            "player_id": f"debug_{int(time.time())}",
            "x": 150,
            "y": 350
        }
        
        print(f"📤 Enviando update: {update_message}")
        ws.send(json.dumps(update_message))
    
    try:
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(
            websocket_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        print("⏱️ Executando debug por 30 segundos...")
        import threading
        import time
        
        # Executa em thread separada com timeout
        def run_with_timeout():
            ws.run_forever()
        
        thread = threading.Thread(target=run_with_timeout)
        thread.daemon = True
        thread.start()
        
        # Aguarda 30 segundos
        time.sleep(30)
        ws.close()
        thread.join(timeout=5)
        
        print(f"\n📊 Resumo:")
        print(f"   Total de mensagens: {message_count}")
        print(f"   player_joined: {player_joined_count}")
        print(f"   player_update: {player_update_count}")
        print(f"   game_state: {game_state_count}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_multiple_connections():
    """Testa múltiplas conexões simultâneas"""
    
    websocket_url = os.getenv("WEBSOCKET_URL")
    
    if not websocket_url:
        print("❌ WEBSOCKET_URL não configurada")
        return
    
    print("🧪 Testando múltiplas conexões...")
    
    connections = []
    
    for i in range(3):
        print(f"🔌 Criando conexão {i+1}...")
        
        def create_connection(conn_id):
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    print(f"📨 Conexão {conn_id}: {data.get('type', 'unknown')}")
                except:
                    pass
            
            def on_error(ws, error):
                print(f"❌ Conexão {conn_id} erro: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                print(f"🔌 Conexão {conn_id} fechada")
            
            def on_open(ws):
                print(f"✅ Conexão {conn_id} aberta")
                
                # Envia join
                join_msg = {
                    "action": "join",
                    "player_id": f"test_{conn_id}_{int(time.time())}",
                    "team": "red" if conn_id % 2 == 0 else "blue",
                    "x": 100 + conn_id * 50,
                    "y": 300
                }
                ws.send(json.dumps(join_msg))
            
            ws = websocket.WebSocketApp(
                websocket_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            return ws
        
        ws = create_connection(i+1)
        connections.append(ws)
    
    # Executa todas as conexões
    import threading
    
    threads = []
    for ws in connections:
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Aguarda 15 segundos e depois fecha todas as conexões
    time.sleep(15)
    for ws in connections:
        ws.close()
    
    # Aguarda threads terminarem
    for thread in threads:
        thread.join(timeout=5)
    
    print("✅ Teste de múltiplas conexões concluído")

def main():
    """Função principal"""
    print("🔍 Debug do Problema Multiplayer")
    print("=" * 40)
    
    choice = input("Escolha o teste:\n1. Debug de mensagens\n2. Múltiplas conexões\n3. Ambos\nEscolha (1-3): ")
    
    if choice == "1":
        debug_multiplayer()
    elif choice == "2":
        test_multiple_connections()
    elif choice == "3":
        debug_multiplayer()
        print("\n" + "="*40 + "\n")
        test_multiple_connections()
    else:
        print("❌ Opção inválida")

if __name__ == "__main__":
    main() 