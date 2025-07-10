#!/usr/bin/env python3
"""
Script de teste para verificar pontuação de bandeiras
"""

import json
import time
import websocket
import threading
from typing import Dict, Any

# Configurações
WEBSOCKET_URL = "wss://your-api-gateway-url.execute-api.region.amazonaws.com/dev"

class FlagScoringTest:
    def __init__(self):
        self.connected = False
        self.ws = None
        self.player_id = f"test_player_{int(time.time())}"
        self.test_results = []
        
    def on_websocket_message(self, ws, message):
        """Processa mensagens recebidas"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            print(f"📨 Recebido: {msg_type}")
            
            if msg_type == "flag_scored":
                scoring_team = data["scoring_team"]
                flag_team = data["flag_team"]
                scores = data["scores"]
                
                print(f"🏆 PONTO DETECTADO!")
                print(f"   Time que marcou: {scoring_team}")
                print(f"   Bandeira capturada: {flag_team}")
                print(f"   Placar atual: {scores}")
                
                self.test_results.append({
                    "type": "flag_scored",
                    "scoring_team": scoring_team,
                    "flag_team": flag_team,
                    "scores": scores,
                    "timestamp": time.time()
                })
                
            elif msg_type == "game_state":
                print(f"📊 Estado do jogo recebido")
                print(f"   Jogadores: {len(data.get('players', {}))}")
                print(f"   Bandeiras: {data.get('flags', {})}")
                print(f"   Placar: {data.get('scores', {})}")
                
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
        
        # Entra no jogo
        join_message = {
            "action": "join", 
            "player_id": self.player_id, 
            "team": "red",
            "x": 100, 
            "y": 100
        }
        ws.send(json.dumps(join_message))
        print(f"🎮 Entrou no jogo como {self.player_id}")

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

    def simulate_flag_capture_and_scoring(self):
        """Simula captura de bandeira e pontuação"""
        if not self.connected:
            print("❌ Não conectado")
            return
            
        print("\n🎯 Simulando captura de bandeira...")
        
        # 1. Captura bandeira azul
        capture_message = {
            "action": "capture_flag",
            "player_id": self.player_id,
            "flag_team": "blue"
        }
        self.ws.send(json.dumps(capture_message))
        print("   📥 Capturou bandeira azul")
        
        time.sleep(1)
        
        # 2. Move para base azul (simula estar na base)
        # Base azul está em (800, 300)
        position_message = {
            "action": "update",
            "player_id": self.player_id,
            "x": 800,
            "y": 300
        }
        self.ws.send(json.dumps(position_message))
        print("   🏃 Moveu para base azul (800, 300)")
        
        # 3. Aguarda verificação de pontuação
        print("   ⏳ Aguardando verificação de pontuação...")
        time.sleep(3)
        
        # 4. Verifica resultados
        if self.test_results:
            print(f"\n✅ Teste concluído! {len(self.test_results)} pontos detectados")
            for result in self.test_results:
                print(f"   - {result['scoring_team']} marcou ponto com bandeira {result['flag_team']}")
        else:
            print("\n❌ Nenhum ponto foi detectado")
            print("   Verifique se:")
            print("   1. A função check_flag_scoring está sendo chamada")
            print("   2. A distância até a base está correta")
            print("   3. Os dados do jogador estão sendo lidos corretamente")

    def run_test(self):
        """Executa o teste completo"""
        print("🧪 Iniciando teste de pontuação de bandeiras")
        print("=" * 50)
        
        if not self.connect_websocket():
            print("❌ Falha ao conectar")
            return
            
        time.sleep(2)  # Aguarda conexão estabilizar
        
        self.simulate_flag_capture_and_scoring()
        
        time.sleep(2)  # Aguarda processamento final
        
        self.ws.close()
        print("\n🏁 Teste finalizado")

if __name__ == "__main__":
    print("⚠️  ATENÇÃO: Configure WEBSOCKET_URL no script antes de executar!")
    print("   Exemplo: wss://abc123.execute-api.us-east-1.amazonaws.com/dev")
    print()
    
    # Descomente a linha abaixo e configure a URL correta
    # test = FlagScoringTest()
    # test.run_test() 