# ☁️ Configuração AWS - Jogo Multiplayer Captura de Bandeira

## 📋 Pré-requisitos

- Conta AWS ativa
- AWS CLI configurado (opcional)
- Permissões para criar recursos AWS

---

## 🚀 Setup Passo a Passo

### 1️⃣ **DynamoDB - Tabela de Conexões**

1. **Acesse o Console AWS DynamoDB**
2. **Criar tabela**:
   - **Nome da tabela**: `WebSocketConnections`
   - **Partition key**: `connection_id` (String)
   - **Configurações**: Padrão
   - **TTL**: Ativar com atributo `expires_at`

```json
{
  "TableName": "WebSocketConnections",
  "KeySchema": [
    {
      "AttributeName": "connection_id",
      "KeyType": "HASH"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "connection_id",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PAY_PER_REQUEST"
}
```

### 2️⃣ **Lambda - Função do Servidor**

1. **Acesse o Console AWS Lambda**
2. **Criar função**:
   - **Nome**: `websocket-game-handler`
   - **Runtime**: Python 3.9 ou superior
   - **Arquitetura**: x86_64
   - **Permissões**: Criar nova role com permissões básicas

3. **Configurar timeout**:
   - **Timeout**: 30 segundos

4. **Adicionar variáveis de ambiente**:
   ```
   TABLE_NAME=WebSocketConnections
   AWS_REGION=us-east-1
   API_GATEWAY_ENDPOINT=https://2oyhltudp1.execute-api.us-east-1.amazonaws.com/production
   ```

5. **Colar código**: Copiar todo o conteúdo de `websocket_game_handler.py`

### 3️⃣ **IAM - Permissões da Role Lambda**

1. **Acesse o Console IAM**
2. **Encontrar a role** criada para o Lambda
3. **Adicionar política** (JSON):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:*:table/WebSocketConnections"
        },
        {
            "Effect": "Allow",
            "Action": [
                "execute-api:ManageConnections"
            ],
            "Resource": "arn:aws:execute-api:us-east-1:*:2oyhltudp1/production/POST/@connections/*"
        }
    ]
}
```

### 4️⃣ **API Gateway - WebSocket API**

1. **Acesse o Console API Gateway**
2. **Criar API**:
   - **Tipo**: WebSocket API
   - **Nome**: `game-websocket-api`

3. **Configurar rotas**:
   - **$connect**: Integração Lambda - `websocket-game-handler`
   - **$disconnect**: Integração Lambda - `websocket-game-handler`
   - **$default**: Integração Lambda - `websocket-game-handler`

4. **Deploy**:
   - **Stage**: `production`
   - **Deploy**

5. **Obter URL**:
   - **WebSocket URL**: `wss://2oyhltudp1.execute-api.us-east-1.amazonaws.com/production`

### 5️⃣ **Configurar Cliente**

1. **Criar arquivo `.env`**:
```bash
WEBSOCKET_URL=wss://2oyhltudp1.execute-api.us-east-1.amazonaws.com/production
```

2. **Testar conexão**:
```bash
python game_client.py
```

---

## 🔧 Troubleshooting

### **Erro: "Handshake status 500"**
- ✅ Lambda function existe e está configurada
- ✅ Variáveis de ambiente estão corretas
- ✅ Permissões IAM estão configuradas
- ✅ API Gateway está deployado

### **Erro: "get_api_gateway_client is not defined"**
- ✅ Código Lambda foi atualizado com a função
- ✅ Deploy da Lambda foi feito após atualização

### **Erro: "403 Forbidden"**
- ✅ Permissões IAM incluem DynamoDB e API Gateway
- ✅ ARN da API Gateway está correto na política IAM

### **Erro: "DynamoDB table not found"**
- ✅ Tabela `WebSocketConnections` existe
- ✅ Nome da tabela está correto nas variáveis de ambiente

---

## 📊 Monitoramento

### **CloudWatch Logs**
- **Grupo de logs**: `/aws/lambda/websocket-game-handler`
- **Monitorar**: Erros e performance

### **DynamoDB Metrics**
- **Tabela**: `WebSocketConnections`
- **Monitorar**: Consumo de RCU/WCU

### **API Gateway Metrics**
- **API**: `game-websocket-api`
- **Monitorar**: Latência e erros

---

## 💰 Custos Estimados

### **Free Tier (12 meses)**
- **Lambda**: 1M requests grátis
- **DynamoDB**: 25GB + 25 RCU/WCU grátis
- **API Gateway**: 1M WebSocket messages grátis

### **Produção (100 jogadores)**
- **Lambda**: ~$2-5/mês
- **DynamoDB**: ~$1-3/mês
- **API Gateway**: ~$2-4/mês
- **Total**: ~$5-12/mês

---

## ✅ Checklist de Verificação

- [ ] DynamoDB tabela criada
- [ ] Lambda function configurada
- [ ] Variáveis de ambiente definidas
- [ ] Permissões IAM configuradas
- [ ] API Gateway criado e deployado
- [ ] URL WebSocket obtida
- [ ] Cliente configurado
- [ ] Teste de conexão realizado

**Agora seu servidor AWS está pronto para o jogo! 🎉** 