#!/usr/bin/env python3
"""
Jogo Multiplayer WebSocket - Cliente (Modo Captura de Bandeira)
Desenvolvido para AWS Lambda + DynamoDB + API Gateway WebSocket
"""

import os
import pygame
import websocket
import json
import time
import threading
import math
from typing import Dict, List
import uuid
import sys
from dotenv import load_dotenv

load_dotenv()

# Configurações do jogo
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SIZE = 20
PLAYER_SPEED = 5
FPS = 60
BULLET_SIZE = 5
FLAG_SIZE = 30
BASE_SIZE = 100

# 🔧 SUBSTITUA PELA SUA URL WEBSOCKET DA AWS
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")

# Times
TEAMS = {
    "red": {
        "name": "Time Vermelho",
        "color": [255, 100, 100],
        "base_x": 50,
        "base_y": SCREEN_HEIGHT // 2,
        "flag_x": 50,
        "flag_y": SCREEN_HEIGHT // 2,
        "spawn_x": 100,
        "spawn_y": SCREEN_HEIGHT // 2
    },
    "blue": {
        "name": "Time Azul", 
        "color": [100, 100, 255],
        "base_x": SCREEN_WIDTH - 50,
        "base_y": SCREEN_HEIGHT // 2,
        "flag_x": SCREEN_WIDTH - 50,
        "flag_y": SCREEN_HEIGHT // 2,
        "spawn_x": SCREEN_WIDTH - 100,
        "spawn_y": SCREEN_HEIGHT // 2
    }
}


class MultiplayerGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🎮 Jogo Multiplayer - Captura de Bandeira")
        self.clock = pygame.time.Clock()

        # Estado do jogador local
        self.player_id = str(uuid.uuid4())[:8]
        self.local_player = {
            "x": SCREEN_WIDTH // 2,
            "y": SCREEN_HEIGHT // 2,
            "team": None,
            "color": [255, 255, 255],
            "hp": 100,
            "max_hp": 100,
            "carrying_flag": None
        }

        # Estado de outros jogadores
        self.other_players = {}

        # Estado do jogo
        self.flags = {
            "red": {"x": TEAMS["red"]["flag_x"], "y": TEAMS["red"]["flag_y"], "captured": False, "carrier": None},
            "blue": {"x": TEAMS["blue"]["flag_x"], "y": TEAMS["blue"]["flag_y"], "captured": False, "carrier": None}
        }
        self.bullets = []
        self.scores = {"red": 0, "blue": 0}

        # WebSocket
        self.ws = None
        self.connected = False
        self.running = True

        # Thread para WebSocket
        self.ws_thread = None

        # Controle de envio de posição
        self.last_sent_position = {"x": -1, "y": -1}
        self.last_position_time = 0
        self.position_send_interval = 1 / 60  # 60 updates por segundo (mais frequente para colisões)

        # Controle de tiro
        self.last_shot_time = 0
        self.shot_cooldown = 0.5  # 0.5 segundos entre tiros

        # Controle de atualização de balas
        self.last_bullet_update_time = 0
        self.bullet_update_interval = 1 / 10  # 10 updates por segundo
        self.sent_bullet_updates = set()  # Rastreia balas que já foram enviadas

        # Interface
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 18)

        # Estado do jogo
        self.game_started = False
        self.respawn_timer = 0
        self.dead = False

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
            
            print(f"📨 Cliente recebeu: {msg_type}")
            if msg_type == "game_state":
                print(f"   game_state keys: {list(data.keys())}")
                players = data.get("players", {})
                print(f"   players count: {len(players)}")
                for pid, player_data in players.items():
                    print(f"   player {pid} keys: {list(player_data.keys())}")

            if msg_type == "player_joined":
                if "player_data" in data:
                    # Mensagem para o jogador que acabou de entrar
                    player_data = data["player_data"]
                    
                    # Debug: verifica se o player_id está sendo atualizado
                    old_player_id = self.player_id
                    if "player_id" in player_data:
                        self.player_id = player_data["player_id"]
                        print(f"🔄 Player ID atualizado: {old_player_id} -> {self.player_id}")
                    else:
                        print(f"⚠️ Player ID não encontrado em player_data: {player_data}")
                    
                    self.local_player["team"] = player_data["team"]
                    self.local_player["color"] = self.convert_color(player_data["color"])
                    self.local_player["x"] = player_data["x"]
                    self.local_player["y"] = player_data["y"]
                    self.local_player["hp"] = player_data["hp"]
                    self.game_started = True
                    print(f"✅ Você entrou no jogo! Time: {player_data['team']} - Player ID: {self.player_id}")
                else:
                    # Mensagem para outros jogadores
                    player_id = data["player_id"]
                    if player_id != self.player_id:
                        self.other_players[player_id] = {
                            "x": int(float(data["x"])),
                            "y": int(float(data["y"])),
                            "team": data["team"],
                            "color": self.convert_color(data["color"]),
                            "hp": 100  # HP padrão para novos jogadores
                        }
                        print(f"👋 Jogador {player_id} entrou no jogo (Time {data['team']})")

            elif msg_type == "player_left":
                player_id = data["player_id"]
                if player_id in self.other_players:
                    try:
                        del self.other_players[player_id]
                        print(f"👋 Jogador {player_id} saiu do jogo")
                    except KeyError:
                        pass

            elif msg_type == "player_update":
                player_id = data["player_id"]
                if player_id != self.player_id:
                    try:
                        # Atualiza apenas posição e dados básicos, mantém HP existente
                        if player_id in self.other_players:
                            # Preserva HP existente
                            current_hp = self.other_players[player_id].get("hp", 100)
                            self.other_players[player_id].update({
                                "x": int(float(data["x"])),
                                "y": int(float(data["y"])),
                                "team": data["team"],
                                "color": self.convert_color(data["color"]),
                                "hp": current_hp  # Mantém HP atual
                            })
                        else:
                            # Novo jogador, usa HP padrão
                            self.other_players[player_id] = {
                                "x": int(float(data["x"])),
                                "y": int(float(data["y"])),
                                "team": data["team"],
                                "color": self.convert_color(data["color"]),
                                "hp": 100
                            }
                    except (ValueError, TypeError) as e:
                        print(f"❌ Erro ao processar update do jogador {player_id}: {e}")

            elif msg_type == "player_hit":
                player_id = data["player_id"]
                damage = data["damage"]
                new_hp = data["new_hp"]
                shooter_id = data["shooter_id"]
                
                if player_id == self.player_id:
                    self.local_player["hp"] = new_hp
                    if new_hp <= 0:
                        self.dead = True
                        self.respawn_timer = 5
                        print(f"💀 Você foi morto por {shooter_id}!")
                    else:
                        print(f"💥 Você foi atingido! HP: {new_hp}")
                else:
                    if player_id in self.other_players:
                        self.other_players[player_id]["hp"] = new_hp
                        if new_hp <= 0:
                            print(f"💀 {player_id} foi morto por {shooter_id}")

            elif msg_type == "player_hp_update":
                player_id = data["player_id"]
                hp = data["hp"]
                
                if player_id == self.player_id:
                    self.local_player["hp"] = hp
                    # Não loga aqui para evitar duplicação com player_hit
                else:
                    if player_id in self.other_players:
                        self.other_players[player_id]["hp"] = hp
                        print(f"💚 HP de {player_id} sincronizado: {hp}")

            elif msg_type == "player_respawned":
                player_id = data["player_id"]
                if player_id == self.player_id:
                    self.local_player["hp"] = data["hp"]
                    self.local_player["x"] = data["x"]
                    self.local_player["y"] = data["y"]
                    self.dead = False
                    self.respawn_timer = 0
                    print("🔄 Você respawnou!")
                else:
                    if player_id in self.other_players:
                        self.other_players[player_id]["hp"] = data["hp"]
                        self.other_players[player_id]["x"] = data["x"]
                        self.other_players[player_id]["y"] = data["y"]
                        print(f"🔄 {player_id} respawnou!")

            elif msg_type == "bullet_shot":
                bullet = data["bullet"]
                self.bullets.append(bullet)
                print(f"🔫 {bullet['shooter_id']} atirou!")

            elif msg_type == "bullets_update":
                self.bullets = data["bullets"]

            elif msg_type == "bullet_position_update":
                bullet_id = data["bullet_id"]
                x = data["x"]
                y = data["y"]
                
                # Atualiza posição da bala
                for bullet in self.bullets:
                    if bullet["id"] == bullet_id:
                        bullet["x"] = x
                        bullet["y"] = y
                        break

            elif msg_type == "bullet_removed":
                bullet_id = data["bullet_id"]
                
                # Remove a bala
                for bullet in self.bullets:
                    if bullet["id"] == bullet_id:
                        self.bullets.remove(bullet)
                        self.sent_bullet_updates.discard(bullet_id)  # Remove do rastreamento
                        break

            elif msg_type == "flag_captured":
                flag_team = data["flag_team"]
                carrier_id = data["carrier_id"]
                self.flags[flag_team]["captured"] = True
                self.flags[flag_team]["carrier"] = carrier_id
                
                if carrier_id == self.player_id:
                    self.local_player["carrying_flag"] = flag_team
                    print(f"🏁 Você capturou a bandeira {flag_team}!")
                else:
                    print(f"🏁 {carrier_id} capturou a bandeira {flag_team}!")

            elif msg_type == "flag_dropped":
                flag_team = data["flag_team"]
                x = data["x"]
                y = data["y"]
                self.flags[flag_team]["captured"] = False
                self.flags[flag_team]["carrier"] = None
                self.flags[flag_team]["x"] = x
                self.flags[flag_team]["y"] = y
                
                if self.local_player["carrying_flag"] == flag_team:
                    self.local_player["carrying_flag"] = None
                    print(f"🏁 Você soltou a bandeira {flag_team}!")

            elif msg_type == "flag_scored":
                scoring_team = data["scoring_team"]
                flag_team = data["flag_team"]
                self.scores = data["scores"]
                
                # Reseta bandeiras
                self.flags[flag_team]["captured"] = False
                self.flags[flag_team]["carrier"] = None
                self.flags[flag_team]["x"] = TEAMS[flag_team]["flag_x"]
                self.flags[flag_team]["y"] = TEAMS[flag_team]["flag_y"]
                
                if self.local_player["carrying_flag"] == flag_team:
                    self.local_player["carrying_flag"] = None
                
                print(f"🏆 {scoring_team} marcou ponto! Placar: {self.scores}")

            elif msg_type == "game_state":
                # Estado completo do jogo
                players = data.get("players", {})
                for pid, player_data in players.items():
                    if pid != self.player_id:
                        try:
                            self.other_players[pid] = {
                                "x": int(float(player_data.get("x", 0))),
                                "y": int(float(player_data.get("y", 0))),
                                "team": player_data.get("team"),
                                "color": self.convert_color(player_data.get("color", [255, 255, 255])),
                                "hp": player_data.get("hp", 100)
                            }
                        except (ValueError, TypeError) as e:
                            print(f"❌ Erro ao processar dados do jogador {pid}: {e}")

                # Atualiza estado do jogo
                self.flags = data.get("flags", self.flags)
                self.bullets = data.get("bullets", [])
                self.scores = data.get("scores", {"red": 0, "blue": 0})

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

        # Envia mensagem de entrada no jogo (sem especificar time)
        # O servidor vai atribuir o time automaticamente baseado no balanceamento
        join_message = {
            "action": "join", 
            "player_id": self.player_id, 
            "x": self.local_player["x"], 
            "y": self.local_player["y"]
        }
        ws.send(json.dumps(join_message))
        print(f"🎮 Enviando join sem especificar time - servidor vai balancear")

    def connect_websocket(self):
        """Conecta ao WebSocket"""
        try:
            if not WEBSOCKET_URL:
                print("❌ WEBSOCKET_URL não configurada")
                return False
                
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

    def send_position_update(self):
        """Envia atualização de posição se necessário"""
        if not self.connected or not self.ws or self.dead:
            return

        current_time = time.time()
        current_pos = {"x": self.local_player["x"], "y": self.local_player["y"]}

        position_changed = (current_pos["x"] != self.last_sent_position["x"] or 
                          current_pos["y"] != self.last_sent_position["y"])
        time_elapsed = current_time - self.last_position_time >= self.position_send_interval

        if position_changed and time_elapsed:
            try:
                message = {
                    "action": "update", 
                    "player_id": self.player_id, 
                    "x": self.local_player["x"], 
                    "y": self.local_player["y"]
                }
                self.ws.send(json.dumps(message))

                self.last_sent_position = current_pos.copy()
                self.last_position_time = current_time

            except Exception as e:
                print(f"❌ Erro ao enviar posição: {e}")

    def send_shot(self, target_x, target_y):
        """Envia tiro"""
        print(f"🔫 send_shot() chamada - target=({target_x}, {target_y})")
        
        if not self.connected or not self.ws or self.dead:
            print(f"   ❌ Não conectado ou morto - connected={self.connected}, dead={self.dead}")
            return

        current_time = time.time()
        if current_time - self.last_shot_time < self.shot_cooldown:
            print(f"   ⏸️ Cooldown ativo - tempo restante: {self.shot_cooldown - (current_time - self.last_shot_time):.2f}s")
            return

        try:
            message = {
                "action": "shoot",
                "player_id": self.player_id,
                "target_x": target_x,
                "target_y": target_y,
                "player_x": self.local_player["x"],
                "player_y": self.local_player["y"]
            }
            print(f"   📤 Enviando tiro: {message}")
            self.ws.send(json.dumps(message))
            self.last_shot_time = current_time
            print(f"   ✅ Tiro enviado com sucesso")

        except Exception as e:
            print(f"❌ Erro ao enviar tiro: {e}")

    def send_capture_flag(self, flag_team):
        """Envia captura de bandeira"""
        if not self.connected or not self.ws or self.dead:
            return

        try:
            message = {
                "action": "capture_flag",
                "player_id": self.player_id,
                "flag_team": flag_team
            }
            self.ws.send(json.dumps(message))

        except Exception as e:
            print(f"❌ Erro ao capturar bandeira: {e}")

    def send_drop_flag(self):
        """Envia soltura de bandeira"""
        if not self.connected or not self.ws:
            return

        try:
            message = {
                "action": "drop_flag",
                "player_id": self.player_id,
                "x": self.local_player["x"],
                "y": self.local_player["y"]
            }
            self.ws.send(json.dumps(message))

        except Exception as e:
            print(f"❌ Erro ao soltar bandeira: {e}")

    def send_respawn(self):
        """Envia pedido de respawn"""
        if not self.connected or not self.ws:
            return

        try:
            message = {
                "action": "respawn",
                "player_id": self.player_id
            }
            self.ws.send(json.dumps(message))

        except Exception as e:
            print(f"❌ Erro ao respawnar: {e}")

    def send_ping(self):
        """Envia ping para manter conexão viva"""
        if not self.connected or not self.ws:
            return

        try:
            message = {"action": "ping", "timestamp": int(time.time())}
            self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"❌ Erro ao enviar ping: {e}")



    def update_bullets(self):
        """Atualiza posição das balas localmente e envia para o servidor"""
        if not self.connected or not self.ws:
            return

        # Debug: mostra que a função está sendo chamada
        if self.bullets:
            print(f"🔄 update_bullets() chamada - {len(self.bullets)} balas ativas - Player ID: {self.player_id}")

        current_time = time.time()
        bullets_to_remove = []

        # Debug: mostra quantas balas estão sendo processadas
        if self.bullets:
            print(f"🔍 Processando {len(self.bullets)} balas...")

        for bullet in self.bullets:
            # Remove balas antigas (mais de 5 segundos)
            if current_time - bullet.get("created_at", 0) > 5:
                bullets_to_remove.append(bullet)
                continue

            # Move a bala
            bullet["x"] += bullet["dx"]
            bullet["y"] += bullet["dy"]

            # Verifica se saiu da tela
            if (bullet["x"] < 0 or bullet["x"] > SCREEN_WIDTH or 
                bullet["y"] < 0 or bullet["y"] > SCREEN_HEIGHT):
                bullets_to_remove.append(bullet)
                continue

            # Se é uma bala do jogador local, envia atualização para o servidor
            if bullet.get("shooter_id") == self.player_id:
                bullet_id = bullet["id"]
                
                # Debug: mostra informações da bala
                print(f"   Bala {bullet_id} em ({bullet['x']:.1f}, {bullet['y']:.1f}) - shooter: {bullet.get('shooter_id')}")
                
                # Debug: mostra as condições
                time_condition = current_time - self.last_bullet_update_time >= self.bullet_update_interval
                sent_condition = bullet_id not in self.sent_bullet_updates
                print(f"   ⏱️ Condições: tempo={time_condition}, não_enviada={sent_condition}")
                
                # Só envia se não enviou recentemente e se a bala ainda não foi marcada como enviada
                if time_condition and sent_condition:
                    try:
                        message = {
                            "action": "bullet_update",
                            "bullet_id": bullet_id,
                            "x": bullet["x"],
                            "y": bullet["y"],
                            "shooter_id": self.player_id
                        }
                        print(f"   📤 Enviando atualização para bala {bullet_id}")
                        self.ws.send(json.dumps(message))
                        self.last_bullet_update_time = current_time
                        self.sent_bullet_updates.add(bullet_id)
                    except Exception as e:
                        print(f"❌ Erro ao enviar atualização de bala: {e}")
                else:
                    print(f"   ⏸️ Bala {bullet_id} já foi enviada ou muito recente")
            else:
                print(f"   👤 Bala {bullet.get('id')} não é do jogador local (shooter: {bullet.get('shooter_id')})")

        # Remove balas processadas
        for bullet in bullets_to_remove:
            if bullet in self.bullets:
                bullet_id = bullet.get("id")
                if bullet_id:
                    self.sent_bullet_updates.discard(bullet_id)  # Remove do rastreamento
                self.bullets.remove(bullet)

    def send_bullet_update(self, bullet_id, x, y):
        """Envia atualização de posição de bala para o servidor"""
        if not self.connected or not self.ws:
            return

        try:
            message = {
                "action": "bullet_update",
                "bullet_id": bullet_id,
                "x": x,
                "y": y,
                "shooter_id": self.player_id
            }
            self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"❌ Erro ao enviar atualização de bala: {e}")

    def handle_input(self):
        """Processa entrada do usuário"""
        keys = pygame.key.get_pressed()
        
        if self.dead:
            if keys[pygame.K_r]:
                self.send_respawn()
            return

        # Movimento
        dx = 0
        dy = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= PLAYER_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += PLAYER_SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= PLAYER_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += PLAYER_SPEED

        # Normaliza movimento diagonal
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        # Atualiza posição
        new_x = max(0, min(SCREEN_WIDTH - PLAYER_SIZE, self.local_player["x"] + dx))
        new_y = max(0, min(SCREEN_HEIGHT - PLAYER_SIZE, self.local_player["y"] + dy))
        
        self.local_player["x"] = new_x
        self.local_player["y"] = new_y

        # Tiro com clique do mouse
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:  # Botão esquerdo
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.send_shot(mouse_x, mouse_y)

        # Captura de bandeira com E
        if keys[pygame.K_e]:
            self.try_capture_flag()

        # Solta bandeira com Q
        if keys[pygame.K_q]:
            if self.local_player["carrying_flag"]:
                self.send_drop_flag()
                


    def try_capture_flag(self):
        """Tenta capturar bandeira próxima"""
        for flag_team, flag in self.flags.items():
            if flag["captured"]:
                continue

            dx = self.local_player["x"] - flag["x"]
            dy = self.local_player["y"] - flag["y"]
            distance = math.sqrt(dx*dx + dy*dy)

            if distance < FLAG_SIZE and self.local_player["team"] != flag_team:
                self.send_capture_flag(flag_team)
                break

    def draw(self):
        """Desenha o jogo"""
        # Fundo
        self.screen.fill((50, 50, 50))

        # Desenha bases
        for team_name, team_data in TEAMS.items():
            base_color = team_data["color"]
            pygame.draw.circle(self.screen, base_color, (team_data["base_x"], team_data["base_y"]), BASE_SIZE // 2)
            pygame.draw.circle(self.screen, (255, 255, 255), (team_data["base_x"], team_data["base_y"]), BASE_SIZE // 2, 3)

        # Desenha bandeiras
        for flag_team, flag in self.flags.items():
            if not flag["captured"]:
                flag_color = TEAMS[flag_team]["color"]
                pygame.draw.rect(self.screen, flag_color, (flag["x"] - FLAG_SIZE//2, flag["y"] - FLAG_SIZE//2, FLAG_SIZE, FLAG_SIZE))
                pygame.draw.rect(self.screen, (255, 255, 255), (flag["x"] - FLAG_SIZE//2, flag["y"] - FLAG_SIZE//2, FLAG_SIZE, FLAG_SIZE), 2)

        # Desenha projéteis
        for bullet in self.bullets:
            pygame.draw.circle(self.screen, (255, 255, 0), (int(bullet["x"]), int(bullet["y"])), BULLET_SIZE)

        # Desenha outros jogadores
        for player_id, player_data in self.other_players.items():
            color = player_data["color"]
            x, y = player_data["x"], player_data["y"]
            hp = player_data["hp"]
            
            # Jogador
            pygame.draw.circle(self.screen, color, (x, y), PLAYER_SIZE)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), PLAYER_SIZE, 2)
            
            # Barra de HP
            hp_width = 40
            hp_height = 5
            hp_x = x - hp_width // 2
            hp_y = y - PLAYER_SIZE - 10
            
            # Fundo da barra
            pygame.draw.rect(self.screen, (100, 100, 100), (hp_x, hp_y, hp_width, hp_height))
            
            # HP atual
            hp_percent = max(0, hp / 100)
            hp_current_width = int(hp_width * hp_percent)
            hp_color = (255, 0, 0) if hp_percent < 0.3 else (255, 255, 0) if hp_percent < 0.6 else (0, 255, 0)
            pygame.draw.rect(self.screen, hp_color, (hp_x, hp_y, hp_current_width, hp_height))

        # Desenha jogador local
        if not self.dead:
            color = self.local_player["color"]
            x, y = self.local_player["x"], self.local_player["y"]
            
            # Jogador
            pygame.draw.circle(self.screen, color, (int(x), int(y)), PLAYER_SIZE)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), PLAYER_SIZE, 3)
            
            # Indicador de bandeira carregada
            if self.local_player["carrying_flag"]:
                flag_color = TEAMS[self.local_player["carrying_flag"]]["color"]
                pygame.draw.circle(self.screen, flag_color, (int(x), int(y)), PLAYER_SIZE + 5, 3)
            
            # Barra de HP
            hp_width = 40
            hp_height = 5
            hp_x = x - hp_width // 2
            hp_y = y - PLAYER_SIZE - 10
            
            pygame.draw.rect(self.screen, (100, 100, 100), (hp_x, hp_y, hp_width, hp_height))
            
            hp_percent = max(0, self.local_player["hp"] / self.local_player["max_hp"])
            hp_current_width = int(hp_width * hp_percent)
            hp_color = (255, 0, 0) if hp_percent < 0.3 else (255, 255, 0) if hp_percent < 0.6 else (0, 255, 0)
            pygame.draw.rect(self.screen, hp_color, (hp_x, hp_y, hp_current_width, hp_height))

        # Interface
        self.draw_ui()

    def draw_ui(self):
        """Desenha interface do usuário"""
        # Status da conexão
        status_color = (0, 255, 0) if self.connected else (255, 0, 0)
        status_text = "Conectado" if self.connected else "Desconectado"
        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (10, 10))

        # Contador de jogadores
        player_count = len(self.other_players) + 1
        count_text = f"Jogadores: {player_count}"
        count_surface = self.font.render(count_text, True, (255, 255, 255))
        self.screen.blit(count_surface, (10, 35))

        # Placar
        score_text = f"Vermelho: {self.scores['red']} | Azul: {self.scores['blue']}"
        score_surface = self.big_font.render(score_text, True, (255, 255, 255))
        self.screen.blit(score_surface, (SCREEN_WIDTH // 2 - score_surface.get_width() // 2, 10))

        # Time do jogador
        if self.local_player["team"]:
            team_name = TEAMS[self.local_player["team"]]["name"]
            team_color = TEAMS[self.local_player["team"]]["color"]
            team_surface = self.font.render(f"Seu time: {team_name}", True, team_color)
            self.screen.blit(team_surface, (10, 60))

        # HP do jogador
        if not self.dead:
            hp_text = f"HP: {self.local_player['hp']}/{self.local_player['max_hp']}"
            hp_surface = self.font.render(hp_text, True, (255, 255, 255))
            self.screen.blit(hp_surface, (10, 85))

        # Bandeira carregada
        if self.local_player["carrying_flag"]:
            flag_text = f"Carregando bandeira: {self.local_player['carrying_flag']}"
            flag_surface = self.font.render(flag_text, True, (255, 255, 0))
            self.screen.blit(flag_surface, (10, 110))

        # Timer de respawn
        if self.dead:
            if self.respawn_timer > 0:
                respawn_text = f"Respawn em: {self.respawn_timer:.1f}s (Pressione R)"
                respawn_surface = self.big_font.render(respawn_text, True, (255, 0, 0))
                self.screen.blit(respawn_surface, (SCREEN_WIDTH // 2 - respawn_surface.get_width() // 2, SCREEN_HEIGHT // 2))
            else:
                respawn_text = "Pressione R para respawnar"
                respawn_surface = self.big_font.render(respawn_text, True, (255, 255, 0))
                self.screen.blit(respawn_surface, (SCREEN_WIDTH // 2 - respawn_surface.get_width() // 2, SCREEN_HEIGHT // 2))

        # Controles
        controls = [
            "Controles:",
            "WASD/Setas - Mover",
            "Clique esquerdo - Atirar",
            "E - Capturar bandeira",
            "Q - Soltar bandeira",
            "R - Respawnar (quando morto)",
            "ESC - Sair"
        ]
        
        for i, control in enumerate(controls):
            color = (255, 255, 0) if i == 0 else (200, 200, 200)
            control_surface = self.small_font.render(control, True, color)
            self.screen.blit(control_surface, (SCREEN_WIDTH - 200, 10 + i * 20))

        # FPS
        fps = int(self.clock.get_fps())
        fps_text = f"FPS: {fps}"
        fps_surface = self.small_font.render(fps_text, True, (255, 255, 255))
        self.screen.blit(fps_surface, (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 30))

    def disconnect(self):
        """Desconecta do WebSocket"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.connected = False

    def try_reconnect(self):
        """Tenta reconectar ao WebSocket"""
        print("🔄 Tentando reconectar...")
        self.disconnect()
        time.sleep(1)
        return self.connect_websocket()

    def run(self):
        """Loop principal do jogo"""
        if not self.connect_websocket():
            print("❌ Falha ao conectar ao servidor")
            return

        last_ping_time = 0
        ping_interval = 30  # 30 segundos

        while self.running:
            # Processa eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r and not self.connected:
                        self.try_reconnect()

            # Atualiza timer de respawn
            if self.dead and self.respawn_timer > 0:
                self.respawn_timer -= 1/60  # 60 FPS
                if self.respawn_timer <= 0:
                    self.respawn_timer = 0

            # Processa entrada
            self.handle_input()

            # Atualiza balas
            self.update_bullets()

            # Envia atualizações
            self.send_position_update()

            # Ping periódico
            current_time = time.time()
            if current_time - last_ping_time > ping_interval:
                self.send_ping()
                last_ping_time = current_time

            # Desenha
            self.draw()

            # Atualiza display
            pygame.display.flip()
            self.clock.tick(FPS)

        # Limpeza
        self.disconnect()
        pygame.quit()


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    try:
        import pygame
        import websocket
        print("✅ Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("📦 Execute: pip install pygame websocket-client python-dotenv")
        return False


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    if not WEBSOCKET_URL:
        print("❌ WEBSOCKET_URL não configurada!")
        print("🔧 Configure a variável de ambiente WEBSOCKET_URL ou crie um arquivo .env")
        sys.exit(1)

    print("🎮 Iniciando Jogo Multiplayer - Captura de Bandeira")
    print(f"🌐 Conectando em: {WEBSOCKET_URL}")
    
    game = MultiplayerGame()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n👋 Jogo interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro no jogo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        game.disconnect()
        pygame.quit()

