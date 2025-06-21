# 🚀 Guia Rápido - Jogo Multiplayer WebSocket

## 📋 Resumo dos Arquivos

### 🎮 **Cliente (Seu Computador)**
1. **`game_client.py`** - Código principal do jogo Pygame
2. **`requirements.txt`** - Dependências Python
3. **`setup.py`** - Script de instalação automática

### ☁️ **Servidor (AWS Lambda)**
1. **`lambda_function.py`** - Código do servidor WebSocket

---

## ⚡ Instalação Rápida

### 1️⃣ **Preparar Cliente**
```bash
# Baixar os arquivos
# game_client.py, requirements.txt, setup.py

# Executar setup automático
python setup.py

# OU instalar manualmente
pip install pygame==2.5.2 websocket-client==1.6.4
```

### 2️⃣ **Configurar AWS**
1. **DynamoDB**: Criar tabela `WebSocketConnections` 
   - Partition key: `connection_id` (String)

2. **Lambda**: Criar função `websocket-game-handler`
   - Cole o código `lambda_function.py`
   - Timeout: 30 segundos
   - Permissões: DynamoDB + API Gateway

3. **API Gateway**: Criar WebSocket API
   - Rotas: `$connect`, `$disconnect`, `$default`
   - Integração: Lambda Function
   - Deploy para stage `prod`

### 3️⃣ **Configurar URL**
```python
# No arquivo game_client.py, linha 18:
WEBSOCKET_URL = "wss://sua-api-real.execute-api.us-east-1.amazonaws.com/prod"
```

### 4️⃣ **Executar**
```bash
python game_client.py
```

---

## 🛠️ Arquivos de Código Completos

### 📄 **game_client.py** (Cliente Pygame)
- Interface gráfica com Pygame
- Conexão WebSocket em tempo real
- Movimentação com WASD/setas
- Sistema de cores automático
- Reconexão automática

### 📄 **lambda_function.py** (Servidor AWS)
- Gerenciamento de conexões WebSocket
- Broadcast para múltiplos jogadores
- Limpeza automática de conexões órfãs
- Sistema de cores únicas
- Logs detalhados para debug

### 📄 **requirements.txt** (Dependências)
```
pygame==2.5.2
websocket-client==1.6.4
```

---

## 🎯 Funcionalidades Implementadas

### ✅ **Cliente**
- 🎮 Interface gráfica moderna
- 🌐 WebSocket em tempo real
- 🎨 Cores únicas por jogador
- 🔄 Reconexão automática
- 📊 FPS counter e status
- 🎯 Movimentação suave
- 💬 Sistema de logs

### ✅ **Servidor**
- 🔌 Gerenciamento de conexões
- 📡 Broadcast instantâneo
- 🧹 Limpeza automática
- 🎨 Sistema de cores
- 📊 Logs detalhados
- ⏰ TTL automático (DynamoDB)
- 🏓 Ping/Pong para manter conexão

---

## 🔧 Configurações Importantes

### **DynamoDB TTL**
```python
# Configurado automaticamente no código Lambda
'expires_at': int(time.time()) + 3600  # 1 hora
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
{"action": "join", "player_id": "test1", "x": 400, "y": 300}
{"action": "update", "player_id": "test1", "x": 450, "y": 350}
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

---

## 🎮 Como Jogar

1. **Conectar**: Execute `python game_client.py`
2. **Mover**: Use WASD ou setas direcionais
3. **Sair**: Pressione ESC
4. **Reconectar**: Pressione R se desconectado

### **Interface**
- 🟢 **Verde**: Conectado
- 🔴 **Vermelho**: Desconectado
- 👥 **Contador**: Jogadores online
- ⚡ **FPS**: Performance do jogo

---

## 🚀 Melhorias Futuras

### **Funcionalidades Avançadas**
1. 🏠 **Salas de jogo** separadas
2. 🏆 **Sistema de pontuação**
3. 🔐 **Autenticação de usuários**
4. 🎨 **Sprites e animações**
5. 📱 **Versão mobile**
6. 🌍 **Chat em tempo real**

### **Otimizações**
1. 🚀 **ElastiCache** para cache
2. 🌐 **CloudFront** para CDN
3. 📊 **Métricas detalhadas**
4. 🔄 **Load balancing**

---

## ✅ Checklist Final

- [ ] ☁️ AWS configurada (DynamoDB + Lambda + API Gateway)
- [ ] 🔑 Permissões IAM corretas
- [ ] 🌐 URL WebSocket atualizada no cliente
- [ ] 📦 Dependências instaladas (`pygame`, `websocket-client`)
- [ ] 🧪 Teste de conexão realizado
- [ ] 🎮 Jogo funcionando com múltiplos jogadores

**Agora você tem um jogo multiplayer profissional rodando 100% na AWS! 🎉**