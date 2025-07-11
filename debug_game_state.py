#!/usr/bin/env python3
"""
Debug específico para o problema do game_state
"""

import json
import time
import websocket
import threading
from datetime import datetime

# Configurações
WEBSOCKET_URL = "wss://2oyhltudp1.execute-api.us-east-1.amazonaws.com/production/"
TEST_DURATION = 45  # Aumentado para 45 segundos

class GameStateDebugger:
    def __init__(self):
        self.ws = None
        self.messages_received = []
        self.connected = False
        self.player_id = f"debug_gs_{int(time.time())}"
        
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            print(f"📨 Recebido: {msg_type}")
            print(f"   Dados: {json.dumps(data, indent=2)}")
            
            self.messages_received.append({
                "type": msg_type,
                "data": data,
                "timestamp": time.time()
            })
            
            # Verifica se recebeu game_state
            if msg_type == "game_state":
                print("🎉 GAME_STATE RECEBIDO!")
                players = data.get("players", {})
                print(f"   Jogadores no game_state: {len(players)}")
                for pid, pdata in players.items():
                    print(f"     - {pid}: {pdata.get('team')} em ({pdata.get('x')}, {pdata.get('y')})")
                    
        except json.JSONDecodeError:
            print(f"❌ Erro ao decodificar JSON: {message}")
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")
    
    def on_error(self, ws, error):
        print(f"❌ Erro WebSocket: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"🔌 Fechado: {close_status_code} - {close_msg}")
        self.connected = False
    
    def on_open(self, ws):
        print("✅ Conectado!")
        self.connected = True
        
        # Envia join após 2 segundos
        def send_join():
            time.sleep(2)
            if self.connected:
                join_msg = {
                    "action": "join",
                    "player_id": self.player_id,
                    "team": "red",
                    "x": 100,
                    "y": 300
                }
                print(f"📤 Enviando join: {join_msg}")
                ws.send(json.dumps(join_msg))
                
                # Envia ping após 5 segundos para manter conexão ativa
                time.sleep(5)
                if self.connected:
                    ping_msg = {"action": "ping"}
                    print(f"📤 Enviando ping: {ping_msg}")
                    ws.send(json.dumps(ping_msg))
        
        threading.Thread(target=send_join, daemon=True).start()
    
    def run_test(self):
        print("🔍 Debug do Game State")
        print("=" * 50)
        print(f"🌐 Conectando em: {WEBSOCKET_URL}")
        print(f"⏱️ Executando teste por {TEST_DURATION} segundos...")
        
        # Configura WebSocket
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Executa em thread separada
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()
        
        # Aguarda o tempo do teste
        time.sleep(TEST_DURATION)
        
        # Fecha conexão
        if self.connected:
            self.ws.close()
        
        # Aguarda thread terminar
        ws_thread.join(timeout=5)
        
        # Análise dos resultados
        print("\n📊 Análise dos Resultados:")
        print("=" * 50)
        
        game_state_count = len([m for m in self.messages_received if m["type"] == "game_state"])
        player_joined_count = len([m for m in self.messages_received if m["type"] == "player_joined"])
        
        print(f"   Total de mensagens: {len(self.messages_received)}")
        print(f"   game_state recebidos: {game_state_count}")
        print(f"   player_joined recebidos: {player_joined_count}")
        
        if game_state_count == 0:
            print("❌ PROBLEMA: Nenhum game_state foi recebido!")
            print("   Isso significa que novos jogadores não veem jogadores existentes")
            print("   Verifique os logs do Lambda para erros de serialização")
        else:
            print("✅ game_state está funcionando!")
            
        # Mostra todas as mensagens recebidas
        print("\n📋 Todas as mensagens recebidas:")
        for i, msg in enumerate(self.messages_received, 1):
            print(f"   {i}. {msg['type']} - {datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')}")

if __name__ == "__main__":
    debugger = GameStateDebugger()
    debugger.run_test() 