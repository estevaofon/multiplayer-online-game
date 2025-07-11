#!/usr/bin/env python3
"""
Teste Simples de Multiplayer
"""

import os
import websocket
import json
import time
import threading
from dotenv import load_dotenv

load_dotenv()

def test_multiplayer():
    """Testa o multiplayer de forma simples"""
    
    websocket_url = os.getenv("WEBSOCKET_URL")
    
    if not websocket_url:
        print("❌ WEBSOCKET_URL não configurada")
        return
    
    print(f"🌐 Testando multiplayer em: {websocket_url}")
    
    # Lista para armazenar mensagens recebidas
    received_messages = []
    
    def on_message(ws, message):
        """Processa mensagens recebidas"""
        try:
            data = json.loads(message)
            received_messages.append(data)
            print(f"📨 Recebido: {data.get('type', 'unknown')}")
            
            # Se recebeu game_state, mostra jogadores
            if data.get('type') == 'game_state':
                players = data.get('players', {})
                print(f"👥 Jogadores ativos: {len(players)}")
                for pid, pdata in players.items():
                    print(f"   - {pid}: {pdata.get('team', 'unknown')} em ({pdata.get('x', 0)}, {pdata.get('y', 0)})")
                    
        except json.JSONDecodeError:
            print(f"📨 Mensagem não-JSON: {message}")
    
    def on_error(ws, error):
        print(f"❌ Erro: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Fechado: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        print("✅ Conectado!")
        
        # Envia join
        join_message = {
            "action": "join",
            "player_id": f"test_{int(time.time())}",
            "team": "red",
            "x": 100,
            "y": 300
        }
        
        print(f"📤 Enviando join: {join_message}")
        ws.send(json.dumps(join_message))
        
        # Envia alguns updates
        for i in range(3):
            time.sleep(2)
            update_message = {
                "action": "update",
                "player_id": f"test_{int(time.time())}",
                "x": 100 + i * 20,
                "y": 300 + i * 10
            }
            print(f"📤 Enviando update {i+1}: {update_message}")
            ws.send(json.dumps(update_message))
    
    try:
        # Cria conexão
        ws = websocket.WebSocketApp(
            websocket_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Executa em thread
        def run_websocket():
            ws.run_forever()
        
        thread = threading.Thread(target=run_websocket)
        thread.daemon = True
        thread.start()
        
        # Aguarda 20 segundos
        print("⏱️ Aguardando 20 segundos...")
        time.sleep(20)
        
        # Fecha conexão
        ws.close()
        thread.join(timeout=5)
        
        # Mostra resumo
        print(f"\n📊 Resumo:")
        print(f"   Total de mensagens recebidas: {len(received_messages)}")
        
        message_types = {}
        for msg in received_messages:
            msg_type = msg.get('type', 'unknown')
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        for msg_type, count in message_types.items():
            print(f"   {msg_type}: {count}")
        
        # Verifica se multiplayer está funcionando
        if len(received_messages) > 0:
            print("✅ Comunicação WebSocket funcionando!")
            
            # Verifica se recebeu game_state
            game_states = [msg for msg in received_messages if msg.get('type') == 'game_state']
            if game_states:
                latest_state = game_states[-1]
                players = latest_state.get('players', {})
                print(f"✅ Multiplayer funcionando! {len(players)} jogadores ativos")
            else:
                print("⚠️ Não recebeu game_state - verificar servidor")
        else:
            print("❌ Nenhuma mensagem recebida - problema de comunicação")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

def main():
    """Função principal"""
    print("🧪 Teste Simples de Multiplayer")
    print("=" * 40)
    
    test_multiplayer()

if __name__ == "__main__":
    main() 