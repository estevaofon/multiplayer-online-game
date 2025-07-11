# 🚀 Início Rápido - Jogo Multiplayer Captura de Bandeira

## ⚡ Setup em 5 minutos

### 1️⃣ **Instalar Dependências**
```bash
# Opção A: Setup automático
python setup.py

# Opção B: Instalação manual
pip install pygame>=2.6.1 websocket-client>=1.8.0 python-dotenv>=1.1.1
```

### 2️⃣ **Configurar AWS (Primeira vez)**
1. **DynamoDB**: Criar tabela `WebSocketConnections`
   - Partition key: `connection_id` (String)
   - TTL: `expires_at`

2. **Lambda**: Criar função `websocket-game-handler`
   - Runtime: Python 3.9+
   - Timeout: 30 segundos
   - Código: Copiar `websocket_game_handler.py`

3. **API Gateway**: Criar WebSocket API
   - Rotas: `$connect`, `$disconnect`, `$default`
   - Integração: Lambda Function
   - Deploy: Stage `prod`

### 3️⃣ **Configurar URL**
```bash
# Criar arquivo .env
echo "WEBSOCKET_URL=wss://sua-api-real.execute-api.us-east-1.amazonaws.com/prod" > .env
```

### 4️⃣ **Executar Jogo**
```bash
python game_client.py
```

---

## 🎮 Como Jogar

### **Controles**
- **WASD/Setas**: Mover
- **Clique esquerdo**: Atirar
- **E**: Capturar bandeira
- **Q**: Soltar bandeira
- **R**: Respawnar (quando morto)
- **ESC**: Sair

### **Objetivo**
Capturar a bandeira do time oposto e levá-la para sua base!

### **Mecânicas**
- Cada jogador tem 100 HP
- Tiros causam 25 de dano
- Respawn automático após 5 segundos
- Times: Vermelho vs Azul

---

## 🔧 Troubleshooting

### **Erro: "Module not found"**
```bash
pip install -r requirements.txt
```

### **Erro: "WebSocket connection failed"**
- Verificar URL no arquivo `.env`
- Verificar se API Gateway está deployado

### **Erro: "403 Forbidden"**
- Verificar permissões IAM do Lambda
- Verificar se DynamoDB está configurado

---

## 📞 Suporte

- 📖 **Documentação completa**: `README.md`
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussões**: GitHub Discussions

**Divirta-se! 🎉** 