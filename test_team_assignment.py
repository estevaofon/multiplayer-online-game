#!/usr/bin/env python3
"""
Script de teste para verificar atribuição automática de times
"""

import json
import time
import websocket
import threading
from typing import Dict, Any

# Configurações
WEBSOCKET_URL = "wss://your-api-gateway-url.execute-api.region.amazonaws.com/dev"

class TeamAssignmentTest:
    def __init__(self):
        self.connected = False
        self.ws = None
        self.player_id = f"test_player_{int(time.time())}"
        self.assigned_team = None
        
    def on_websocket_message(self, ws, message):
        """Processa mensagens recebidas"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            print(f"📨 Recebido: {msg_type}")
            
            if msg_type == "player_joined" and "player_data" in data:
                player_data = data["player_data"]
                self.assigned_team = player_data["team"]
                print(f"✅ Time atribuído: {self.assigned_team}")
                print(f"   Posição: ({player_data['x']}, {player_data['y']})")
                print(f"   HP: {player_data['hp']}")
                
            elif msg_type == "game_state":
                players = data.get("players", {})
                print(f"📊 Estado do jogo:")
                print(f"   Total de jogadores: {len(players)}")
                
                red_count = 0
                blue_count = 0
                for pid, player_data in players.items():
                    team = player_data.get("team")
                    if team == "red":
                        red_count += 1
                    elif team == "blue":
                        blue_count += 1
                    print(f"   {pid}: {team}")
                
                print(f"   Time vermelho: {red_count} jogadores")
                print(f"   Time azul: {blue_count} jogadores")
                
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")

    def on_websocket_error(self, ws, error):
        print(f"❌ Erro WebSocket: {error}")
        self.connected = False

    def on_websocket_close(self, ws, close_status_code, close_msg):
        print("🔌 Conexão WebSocket fechada")
        self.connected = False

    def on_websocket_open(self, ws):
        print("🌐 Conexão WebSocket estabelecida")
        self.connected = True
        
        # Entra no jogo sem especificar time
        join_message = {
            "action": "join", 
            "player_id": self.player_id, 
            "x": 100, 
            "y": 100
        }
        ws.send(json.dumps(join_message))
        print(f"🎮 Entrou no jogo como {self.player_id} (sem especificar time)")

    def connect_websocket(self):
        """Conecta ao WebSocket"""
        try:
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                WEBSOCKET_URL, 
                on_open=self.on_websocket_open, 
                on_message=self.on_websocket_message, 
                on_error=self.on_websocket_error, 
                on_close=self.on_websocket_close
            )

            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()

            max_wait = 5
            wait_time = 0
            while not self.connected and wait_time < max_wait:
                time.sleep(0.1)
                wait_time += 0.1

            return self.connected

        except Exception as e:
            print(f"❌ Erro ao conectar WebSocket: {e}")
            return False

    def run_test(self):
        """Executa o teste completo"""
        print("🧪 Testando atribuição automática de times")
        print("=" * 50)
        
        if not self.connect_websocket():
            print("❌ Falha ao conectar")
            return
            
        time.sleep(3)  # Aguarda atribuição de time
        
        if self.assigned_team:
            print(f"\n✅ Teste concluído!")
            print(f"   Time atribuído: {self.assigned_team}")
        else:
            print("\n❌ Nenhum time foi atribuído")
            
        time.sleep(2)  # Aguarda processamento final
        
        self.ws.close()
        print("\n🏁 Teste finalizado")

def test_multiple_players():
    """Testa múltiplos jogadores para verificar balanceamento"""
    print("\n🧪 Testando múltiplos jogadores")
    print("=" * 50)
    
    players = []
    
    # Cria 4 jogadores de teste
    for i in range(4):
        player = TeamAssignmentTest()
        player.player_id = f"test_player_{i}_{int(time.time())}"
        players.append(player)
        
        if player.connect_websocket():
            print(f"✅ Jogador {i+1} conectado")
        else:
            print(f"❌ Jogador {i+1} falhou ao conectar")
            
        time.sleep(1)  # Pequena pausa entre conexões
    
    # Aguarda atribuição de times
    time.sleep(5)
    
    # Verifica times atribuídos
    red_count = 0
    blue_count = 0
    
    for i, player in enumerate(players):
        if player.assigned_team:
            print(f"Jogador {i+1}: {player.assigned_team}")
            if player.assigned_team == "red":
                red_count += 1
            else:
                blue_count += 1
        else:
            print(f"Jogador {i+1}: Nenhum time atribuído")
    
    print(f"\n📊 Resultado do balanceamento:")
    print(f"   Time vermelho: {red_count} jogadores")
    print(f"   Time azul: {blue_count} jogadores")
    
    if abs(red_count - blue_count) <= 1:
        print("✅ Balanceamento funcionando corretamente!")
    else:
        print("❌ Balanceamento não está funcionando")
    
    # Fecha conexões
    for player in players:
        if player.ws:
            player.ws.close()
    
    time.sleep(1)
    print("🏁 Teste de múltiplos jogadores finalizado")

if __name__ == "__main__":
    print("⚠️  ATENÇÃO: Configure WEBSOCKET_URL no script antes de executar!")
    print("   Exemplo: wss://abc123.execute-api.us-east-1.amazonaws.com/dev")
    print()
    
    # Descomente uma das opções abaixo:
    
    # Teste simples - um jogador
    # test = TeamAssignmentTest()
    # test.run_test()
    
    # Teste múltiplos jogadores
    # test_multiple_players() 