# 🚀 Guia Rápido - Jogo Multiplayer Captura de Bandeira

## 📋 Resumo dos Arquivos

### 🎮 **Cliente (Seu Computador)**
1. **`game_client.py`** - Código principal do jogo Pygame (Modo Captura de Bandeira)
2. **`pyproject.toml`** - Dependências Python
3. **`.env`** - Configurações (criar manualmente)

### ☁️ **Servidor (AWS Lambda)**
1. **`websocket_game_handler.py`** - Código do servidor WebSocket

---

## ⚡ Instalação Rápida

### 1️⃣ **Preparar Cliente**
```bash
# Instalar dependências
pip install -e .

# OU instalar manualmente
pip install pygame>=2.6.1 websocket-client>=1.8.0 python-dotenv>=1.1.1
```

### 2️⃣ **Configurar AWS**
1. **DynamoDB**: Criar tabela `WebSocketConnections` 
   - Partition key: `connection_id` (String)

2. **Lambda**: Criar função `websocket-game-handler`
   - Cole o código `websocket_game_handler.py`
   - Timeout: 30 segundos
   - Permissões: DynamoDB + API Gateway

3. **API Gateway**: Criar WebSocket API
   - Rotas: `$connect`, `$disconnect`, `$default`
   - Integração: Lambda Function
   - Deploy para stage `prod`

### 3️⃣ **Configurar URL**
```bash
# Criar arquivo .env
echo "WEBSOCKET_URL=wss://sua-api-real.execute-api.us-east-1.amazonaws.com/prod" > .env
```

### 4️⃣ **Executar**
```bash
python game_client.py
```

---

## 🎯 Funcionalidades do Modo Captura de Bandeira

### ⚔️ **Sistema de Times**
- **Time Vermelho** vs **Time Azul**
- Atribuição automática de times
- Cores distintas para identificação
- Bases separadas para cada time

### 🏁 **Sistema de Bandeiras**
- Cada time tem sua bandeira na base
- Objetivo: Capturar bandeira do time oposto
- Levar bandeira para sua própria base para marcar ponto
- Bandeiras podem ser soltas e recapturadas

### 💖 **Sistema de HP (Vida)**
- Cada jogador tem 100 HP
- Dano de tiro: 25 HP
- Jogadores morrem quando HP chega a 0
- Sistema de respawn após 5 segundos

### 🔫 **Sistema de Combate**
- Tiro com clique do mouse
- Projéteis em tempo real
- Cooldown de 0.5 segundos entre tiros
- Colisão automática com jogadores inimigos

### 🎮 **Controles**
- **WASD/Setas**: Movimento
- **Clique esquerdo**: Atirar
- **E**: Capturar bandeira próxima
- **Q**: Soltar bandeira carregada
- **R**: Respawnar (quando morto)
- **ESC**: Sair do jogo

---

## 🛠️ Arquivos de Código Completos

### 📄 **game_client.py** (Cliente Pygame)
- Interface gráfica moderna com Pygame
- Conexão WebSocket em tempo real
- Sistema de times e bandeiras
- Sistema de HP e combate
- Interface de usuário completa

### 📄 **websocket_game_handler.py** (Servidor AWS)
- Gerenciamento de conexões WebSocket
- Sistema de times e bandeiras
- Processamento de tiros e colisões
- Sistema de pontuação
- Broadcast em tempo real

### 📄 **pyproject.toml** (Dependências)
```toml
[project]
name = "multiplayer-online-game"
version = "0.1.0"
description = "Jogo Multiplayer Captura de Bandeira"
requires-python = ">=3.13"
dependencies = [
    "pygame>=2.6.1",
    "python-dotenv>=1.1.1", 
    "websocket-client>=1.8.0",
]
```

---

## 🎯 Funcionalidades Implementadas

### ✅ **Cliente**
- 🎮 Interface gráfica moderna
- 🌐 WebSocket em tempo real
- ⚔️ Sistema de times (Vermelho vs Azul)
- 🏁 Sistema de bandeiras e captura
- 💖 Sistema de HP e respawn
- 🔫 Sistema de tiro com mouse
- 📊 Interface de pontuação
- 🎯 Movimentação suave
- 💬 Sistema de logs

### ✅ **Servidor**
- 🔌 Gerenciamento de conexões
- 📡 Broadcast instantâneo
- ⚔️ Sistema de times
- 🏁 Lógica de bandeiras
- 🔫 Processamento de tiros
- 💖 Sistema de HP e dano
- 🏆 Sistema de pontuação
- 🧹 Limpeza automática
- 📊 Logs detalhados

---

## 🔧 Configurações Importantes

### **DynamoDB Schema**
```json
{
    "connection_id": "String (Partition Key)",
    "player_id": "String",
    "team": "String (red/blue)",
    "hp": "Number",
    "x": "Number",
    "y": "Number",
    "connected_at": "Number",
    "last_activity": "Number",
    "expires_at": "Number (TTL)"
}
```

### **Permissões IAM**
```json
{
    "dynamodb:PutItem",
    "dynamodb:GetItem", 
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:Scan",
    "execute-api:ManageConnections"
}
```

### **API Gateway Routes**
- **$connect**: Nova conexão
- **$disconnect**: Desconexão
- **$default**: Mensagens do jogo

---

## 🧪 Testando o Sistema

### **1. Teste Local**
```bash
python game_client.py
```

### **2. Teste WebSocket Manual**
```bash
# Instalar wscat
npm install -g wscat

# Conectar
wscat -c wss://sua-api-url/prod

# Enviar mensagens
{"action": "join", "player_id": "test1", "team": "red", "x": 100, "y": 300}
{"action": "shoot", "player_id": "test1", "target_x": 400, "target_y": 300, "player_x": 100, "player_y": 300}
{"action": "capture_flag", "player_id": "test1", "flag_team": "blue"}
```

### **3. Debug AWS**
- CloudWatch Logs: `/aws/lambda/websocket-game-handler`
- DynamoDB: Verificar items na tabela
- API Gateway: Monitorar métricas

---

## 💰 Custos AWS (Estimativa)

### **Free Tier (12 meses)**
- Lambda: 1M requests grátis
- DynamoDB: 25GB + 25 RCU/WCU grátis
- API Gateway: 1M WebSocket messages grátis

### **Produção (100 jogadores simultâneos)**
- **Lambda**: ~$2-5/mês
- **DynamoDB**: ~$1-3/mês  
- **API Gateway**: ~$2-4/mês
- **Total**: ~$5-12/mês

---

## 🚨 Troubleshooting

### **Erro: "WebSocket connection failed"**
- ✅ URL WebSocket correta?
- ✅ API Gateway deployada?
- ✅ Stage = `prod`?

### **Erro: "403 Forbidden"**
- ✅ Permissões IAM configuradas?
- ✅ Lambda tem acesso ao DynamoDB?

### **Erro: "Lambda timeout"**
- ✅ Timeout configurado para 30s?
- ✅ DynamoDB está respondendo?

### **Jogadores não aparecem**
- ✅ Verificar logs CloudWatch
- ✅ DynamoDB tem os dados?
- ✅ Broadcast funcionando?

### **Bandeiras não funcionam**
- ✅ Verificar estado das bandeiras no servidor
- ✅ Verificar lógica de captura
- ✅ Verificar posições das bases

---

## 🎮 Como Jogar

### **Objetivo**
Capturar a bandeira do time oposto e levá-la para sua base para marcar pontos.

### **Mecânicas**
1. **Movimento**: Use WASD ou setas para se mover
2. **Combate**: Clique do mouse para atirar nos inimigos
3. **Captura**: Aproxime-se da bandeira inimiga e pressione E
4. **Pontuação**: Leve a bandeira para sua base
5. **Respawn**: Pressione R quando morto

### **Interface**
- 🟢 **Verde**: Conectado
- 🔴 **Vermelho**: Desconectado
- 👥 **Contador**: Jogadores online
- ⚡ **FPS**: Performance do jogo
- 🏆 **Placar**: Pontos de cada time
- 💖 **HP**: Barra de vida do jogador
- 🏁 **Bandeira**: Indicador de bandeira carregada

---

## 🚀 Melhorias Futuras

### **Funcionalidades Avançadas**
1. 🏠 **Salas de jogo** separadas
2. 🏆 **Sistema de ranking**
3. 🔐 **Autenticação de usuários**
4. 🎨 **Sprites e animações**
5. 📱 **Versão mobile**
6. 🌍 **Chat em tempo real**
7. 🛡️ **Power-ups e habilidades**
8. 🗺️ **Mapas diferentes**

### **Otimizações**
1. 🚀 **ElastiCache** para cache
2. 🌐 **CloudFront** para CDN
3. 📊 **Métricas detalhadas**
4. 🔄 **Load balancing**

---

## ✅ Checklist Final

- [ ] ☁️ AWS configurada (DynamoDB + Lambda + API Gateway)
- [ ] 🔑 Permissões IAM corretas
- [ ] 🌐 URL WebSocket atualizada no .env
- [ ] 📦 Dependências instaladas (`pygame`, `websocket-client`, `python-dotenv`)
- [ ] 🧪 Teste de conexão realizado
- [ ] 🎮 Jogo funcionando com múltiplos jogadores
- [ ] ⚔️ Sistema de times funcionando
- [ ] 🏁 Sistema de bandeiras funcionando
- [ ] 🔫 Sistema de tiro funcionando
- [ ] 💖 Sistema de HP funcionando

**Agora você tem um jogo multiplayer de captura de bandeira profissional rodando 100% na AWS! 🎉**