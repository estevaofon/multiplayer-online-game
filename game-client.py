#!/usr/bin/env python3
"""
Jogo Multiplayer WebSocket - Cliente
Desenvolvido para AWS Lambda + DynamoDB + API Gateway WebSocket
"""

import pygame
import websocket
import json
import time
import threading
from typing import Dict, List
import uuid
import sys

# Configurações do jogo
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SIZE = 20
PLAYER_SPEED = 5
FPS = 60

# 🔧 SUBSTITUA PELA SUA URL WEBSOCKET DA AWS
WEBSOCKET_URL = "wss://***/production/"


class MultiplayerGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🎮 Jogo Multiplayer WebSocket")
        self.clock = pygame.time.Clock()

        # Estado do jogador local
        self.player_id = str(uuid.uuid4())[:8]
        self.local_player = {
            "x": SCREEN_WIDTH // 2,
            "y": SCREEN_HEIGHT // 2,
            "color": [255, 0, 0],  # Será definida pelo servidor
        }

        # Estado de outros jogadores
        self.other_players = {}

        # WebSocket
        self.ws = None
        self.connected = False
        self.running = True

        # Thread para WebSocket
        self.ws_thread = None

        # Controle de envio de posição
        self.last_sent_position = {"x": -1, "y": -1}
        self.last_position_time = 0
        self.position_send_interval = 1 / 30  # 30 updates por segundo

        # Interface
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 36)

    def convert_color(self, color):
        """Converte cor para formato válido do Pygame (lista de integers)"""
        try:
            if isinstance(color, list):
                return [int(float(c)) for c in color]
            elif isinstance(color, tuple):
                return [int(float(c)) for c in color]
            else:
                return [255, 255, 255]  # Branco padrão
        except (ValueError, TypeError):
            return [255, 255, 255]  # Branco padrão em caso de erro

    def on_websocket_message(self, ws, message):
        """Processa mensagens recebidas via WebSocket"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "player_joined":
                player_id = data["player_id"]
                if player_id == self.player_id:
                    self.local_player["color"] = data["color"]
                    print(f"✅ Você entrou no jogo! ID: {self.player_id}")
                else:
                    print(f"👋 Jogador {player_id} entrou no jogo")

            elif msg_type == "player_left":
                player_id = data["player_id"]
                if player_id in self.other_players:
                    try:
                        del self.other_players[player_id]
                        print(f"👋 Jogador {player_id} saiu do jogo")
                    except KeyError:
                        # Jogador já foi removido, ignora
                        pass

            elif msg_type == "player_update":
                player_id = data["player_id"]
                if player_id != self.player_id:
                    try:
                        self.other_players[player_id] = {"x": int(float(data["x"])), "y": int(float(data["y"])), "color": self.convert_color(data["color"])}
                    except (ValueError, TypeError) as e:
                        print(f"❌ Erro ao processar update do jogador {player_id}: {e}")
                        print(f"📊 Dados recebidos: {data}")

            elif msg_type == "game_state":
                # Estado completo do jogo (usado na conexão inicial)
                players = data.get("players", {})
                for pid, player_data in players.items():
                    if pid != self.player_id:
                        try:
                            self.other_players[pid] = {
                                "x": int(float(player_data.get("x", 0))),
                                "y": int(float(player_data.get("y", 0))),
                                "color": self.convert_color(player_data.get("color", [255, 255, 255])),
                            }
                        except (ValueError, TypeError) as e:
                            print(f"❌ Erro ao processar dados do jogador {pid}: {e}")
                            print(f"📊 Dados recebidos: {player_data}")

            elif msg_type == "error":
                print(f"❌ Erro do servidor: {data.get('message', 'Erro desconhecido')}")

            elif msg_type == "pong":
                # Resposta ao ping - mantém conexão viva
                pass

        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")

    def on_websocket_error(self, ws, error):
        """Trata erros do WebSocket"""
        print(f"❌ Erro WebSocket: {error}")
        self.connected = False

    def on_websocket_close(self, ws, close_status_code, close_msg):
        """Trata fechamento da conexão WebSocket"""
        print("🔌 Conexão WebSocket fechada")
        self.connected = False

    def on_websocket_open(self, ws):
        """Trata abertura da conexão WebSocket"""
        print("🌐 Conexão WebSocket estabelecida")
        self.connected = True

        # Envia mensagem de entrada no jogo
        join_message = {"action": "join", "player_id": self.player_id, "x": self.local_player["x"], "y": self.local_player["y"]}
        ws.send(json.dumps(join_message))

    def connect_websocket(self):
        """Conecta ao WebSocket"""
        try:
            websocket.enableTrace(False)  # Desabilita logs verbosos
            self.ws = websocket.WebSocketApp(WEBSOCKET_URL, on_open=self.on_websocket_open, on_message=self.on_websocket_message, on_error=self.on_websocket_error, on_close=self.on_websocket_close)

            # Executa WebSocket em thread separada
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()

            # Aguarda conexão
            max_wait = 5  # 5 segundos
            wait_time = 0
            while not self.connected and wait_time < max_wait:
                time.sleep(0.1)
                wait_time += 0.1

            return self.connected

        except Exception as e:
            print(f"❌ Erro ao conectar WebSocket: {e}")
            return False

    def send_position_update(self):
        """Envia atualização de posição se necessário"""
        if not self.connected or not self.ws:
            return

        current_time = time.time()
        current_pos = {"x": self.local_player["x"], "y": self.local_player["y"]}

        # Verifica se a posição mudou ou se passou tempo suficiente
        position_changed = current_pos["x"] != self.last_sent_position["x"] or current_pos["y"] != self.last_sent_position["y"]

        time_elapsed = current_time - self.last_position_time >= self.position_send_interval

        if position_changed and time_elapsed:
            try:
                message = {"action": "update", "player_id": self.player_id, "x": self.local_player["x"], "y": self.local_player["y"]}
                self.ws.send(json.dumps(message))

                self.last_sent_position = current_pos.copy()
                self.last_position_time = current_time

            except Exception as e:
                print(f"❌ Erro ao enviar posição: {e}")
                self.connected = False

    def send_ping(self):
        """Envia ping para manter conexão viva"""
        if self.connected and self.ws:
            try:
                ping_message = {"action": "ping"}
                self.ws.send(json.dumps(ping_message))
            except Exception as e:
                print(f"❌ Erro ao enviar ping: {e}")
                self.connected = False

    def handle_input(self):
        """Processa entrada do jogador"""
        keys = pygame.key.get_pressed()

        old_x, old_y = self.local_player["x"], self.local_player["y"]

        # Movimento com WASD ou setas
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.local_player["x"] = max(0, self.local_player["x"] - PLAYER_SPEED)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.local_player["x"] = min(SCREEN_WIDTH - PLAYER_SIZE, self.local_player["x"] + PLAYER_SPEED)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.local_player["y"] = max(0, self.local_player["y"] - PLAYER_SPEED)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.local_player["y"] = min(SCREEN_HEIGHT - PLAYER_SIZE, self.local_player["y"] + PLAYER_SPEED)

        # Envia atualização se a posição mudou
        if old_x != self.local_player["x"] or old_y != self.local_player["y"]:
            self.send_position_update()

    def draw(self):
        """Desenha o jogo na tela"""
        # Fundo gradiente
        for y in range(SCREEN_HEIGHT):
            color_factor = y / SCREEN_HEIGHT
            color = (int(20 + color_factor * 10), int(25 + color_factor * 15), int(40 + color_factor * 20))
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))

        # Desenha grid sutil
        grid_color = (40, 45, 60)
        for x in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(self.screen, grid_color, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(self.screen, grid_color, (0, y), (SCREEN_WIDTH, y))

        # Desenha outros jogadores primeiro
        # Cria uma cópia da lista para evitar "dictionary changed during iteration"
        players_to_remove = []

        for player_id, player in list(self.other_players.items()):
            try:
                color = self.convert_color(player.get("color", [0, 255, 0]))
                x = int(float(player.get("x", 0)))
                y = int(float(player.get("y", 0)))

                player_rect = pygame.Rect(x, y, PLAYER_SIZE, PLAYER_SIZE)

                # Sombra
                shadow_rect = pygame.Rect(x + 2, y + 2, PLAYER_SIZE, PLAYER_SIZE)
                pygame.draw.rect(self.screen, (0, 0, 0, 50), shadow_rect)

                # Jogador
                pygame.draw.rect(self.screen, color, player_rect)
                pygame.draw.rect(self.screen, (200, 200, 200), player_rect, 1)

                # ID do jogador
                id_text = self.font.render(player_id[:4], True, (255, 255, 255))
                self.screen.blit(id_text, (x, y - 20))

            except (ValueError, TypeError) as e:
                print(f"❌ Erro ao desenhar jogador {player_id}: {e}")
                print(f"📊 Dados do jogador: {player}")
                # Marca jogador para remoção (não remove durante iteração)
                players_to_remove.append(player_id)

        # Remove jogadores com dados inválidos após a iteração
        for player_id in players_to_remove:
            if player_id in self.other_players:
                del self.other_players[player_id]
                print(f"🗑️ Jogador {player_id} removido por dados inválidos")

        # Desenha o jogador local por último (em destaque)
        player_rect = pygame.Rect(self.local_player["x"], self.local_player["y"], PLAYER_SIZE, PLAYER_SIZE)
        # Sombra
        shadow_rect = pygame.Rect(self.local_player["x"] + 2, self.local_player["y"] + 2, PLAYER_SIZE, PLAYER_SIZE)
        pygame.draw.rect(self.screen, (0, 0, 0, 80), shadow_rect)
        # Jogador local
        pygame.draw.rect(self.screen, self.local_player["color"], player_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), player_rect, 3)  # Borda branca mais grossa

        # "VOCÊ" acima do jogador local
        you_text = self.font.render("VOCÊ", True, (255, 255, 0))
        self.screen.blit(you_text, (self.local_player["x"] - 5, self.local_player["y"] - 20))

        # Interface de informações
        y_offset = 10

        # Status da conexão
        if self.connected:
            status_text = f"🟢 Conectado - ID: {self.player_id}"
            status_color = (0, 255, 0)
        else:
            status_text = "🔴 Desconectado - Tentando reconectar..."
            status_color = (255, 100, 100)

        text = self.font.render(status_text, True, status_color)
        self.screen.blit(text, (10, y_offset))
        y_offset += 25

        # Número de jogadores
        total_players = len(self.other_players) + (1 if self.connected else 0)
        players_text = self.font.render(f"👥 Jogadores online: {total_players}", True, (255, 255, 255))
        self.screen.blit(players_text, (10, y_offset))
        y_offset += 25

        # FPS
        fps_text = self.font.render(f"⚡ FPS: {int(self.clock.get_fps())}", True, (150, 255, 150))
        self.screen.blit(fps_text, (10, y_offset))

        # Instruções (canto inferior)
        instructions = ["🎮 WASD ou ↑↓←→ para mover", "🚪 ESC para sair", "📡 WebSocket em tempo real"]

        for i, instruction in enumerate(instructions):
            text = self.font.render(instruction, True, (180, 180, 180))
            self.screen.blit(text, (10, SCREEN_HEIGHT - 80 + i * 22))

        # Título do jogo (canto superior direito)
        title_text = self.big_font.render("🎮 Multiplayer Game", True, (255, 255, 255))
        title_rect = title_text.get_rect()
        self.screen.blit(title_text, (SCREEN_WIDTH - title_rect.width - 10, 10))

        pygame.display.flip()

    def disconnect(self):
        """Desconecta do servidor"""
        if self.connected and self.ws:
            try:
                leave_message = {"action": "leave", "player_id": self.player_id}
                self.ws.send(json.dumps(leave_message))
                time.sleep(0.1)  # Aguarda envio
            except Exception as e:
                print(f"❌ Erro ao enviar leave: {e}")

            try:
                self.ws.close()
            except Exception as e:
                print(f"❌ Erro ao fechar WebSocket: {e}")

        self.connected = False
        self.running = False

    def try_reconnect(self):
        """Tenta reconectar ao WebSocket"""
        if not self.connected and self.running:
            print("🔄 Tentando reconectar...")
            if self.connect_websocket():
                print("✅ Reconectado com sucesso!")
            else:
                print("❌ Falha na reconexão")

    def run(self):
        """Loop principal do jogo"""
        print("🎮 Iniciando jogo multiplayer WebSocket...")
        print("🔗 Conectando ao servidor...")

        # Verifica se a URL foi configurada
        if "sua-websocket-api-id" in WEBSOCKET_URL:
            print("❌ ERRO: URL do WebSocket não foi configurada!")
            print("🔧 Edite a variável WEBSOCKET_URL no código com sua URL real da AWS")
            input("Pressione Enter para continuar mesmo assim...")

        # Tenta conectar
        if not self.connect_websocket():
            print("❌ Não foi possível conectar ao servidor WebSocket.")
            print("🔧 Verifique se:")
            print("   1. A URL está correta")
            print("   2. A AWS API Gateway está configurada")
            print("   3. A função Lambda está funcionando")
            print("   4. Você tem conexão com a internet")

            resposta = input("Tentar mesmo assim? (s/N): ")
            if resposta.lower() != "s":
                return

        print("🚀 Jogo iniciado! Use WASD ou setas para mover.")

        last_reconnect_attempt = 0
        last_ping_time = 0
        reconnect_interval = 3  # Tenta reconectar a cada 3 segundos
        ping_interval = 30  # Ping a cada 30 segundos

        while self.running:
            current_time = time.time()

            # Processa eventos do Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r and not self.connected:
                        # Tecla R para reconectar manualmente
                        self.try_reconnect()

            # Tenta reconectar se desconectado
            if not self.connected and current_time - last_reconnect_attempt > reconnect_interval:
                self.try_reconnect()
                last_reconnect_attempt = current_time

            # Envia ping para manter conexão viva
            if self.connected and current_time - last_ping_time > ping_interval:
                self.send_ping()
                last_ping_time = current_time

            # Processa entrada do jogador
            if self.connected:
                self.handle_input()

            # Desenha o jogo
            self.draw()

            # Controla FPS
            self.clock.tick(FPS)

        # Desconecta adequadamente
        print("👋 Desconectando...")
        self.disconnect()
        pygame.quit()
        print("✅ Jogo finalizado!")


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    try:
        import pygame
    except ImportError:
        print("❌ Pygame não encontrado!")
        print("📦 Instale com: pip install pygame")
        return False

    try:
        import websocket
    except ImportError:
        print("❌ websocket-client não encontrado!")
        print("📦 Instale com: pip install websocket-client")
        return False

    return True


if __name__ == "__main__":
    print("🎮 Jogo Multiplayer WebSocket")
    print("=" * 40)

    # Verifica dependências
    if not check_dependencies():
        sys.exit(1)

    # Inicia o jogo
    try:
        game = MultiplayerGame()
        game.run()
    except KeyboardInterrupt:
        print("\n👋 Jogo interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
