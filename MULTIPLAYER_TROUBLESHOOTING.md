# 🔍 Troubleshooting - Problema Multiplayer

## 🚨 Problema: Só aparece um jogador

### 📋 Checklist de Verificação

#### 1️⃣ **Verificar Logs do Lambda**
1. Acesse CloudWatch Logs
2. Procure por `/aws/lambda/websocket-game-handler`
3. Verifique se aparecem mensagens como:
   - `📢 Notificando entrada do jogador X para outros jogadores`
   - `📡 Broadcast para X (connection_id)`
   - `📊 Enviando game_state com X jogadores ativos`

#### 2️⃣ **Verificar DynamoDB**
1. Acesse o console DynamoDB
2. Vá para a tabela `WebSocketConnections`
3. Verifique se há múltiplos registros com `player_id` preenchido
4. Confirme que `last_activity` está atualizado

#### 3️⃣ **Testar com Script de Debug**
```bash
python debug_multiplayer.py
```

#### 4️⃣ **Verificar Permissões IAM**
Certifique-se que a Lambda tem permissões para:
- `dynamodb:Scan`
- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `execute-api:ManageConnections`

---

## 🔧 Soluções Comuns

### **Problema 1: Broadcast não está funcionando**
**Sintomas**: Jogadores entram mas não veem uns aos outros

**Solução**:
1. Verificar se `broadcast_message` está sendo chamada
2. Verificar se `exclude_connection` está correto
3. Verificar se conexões têm `player_id` definido

### **Problema 2: Conexões órfãs no DynamoDB**
**Sintomas**: Jogadores antigos ainda aparecem

**Solução**:
1. Limpar tabela DynamoDB manualmente
2. Verificar se `handle_disconnect` está funcionando
3. Verificar TTL da tabela

### **Problema 3: API Gateway não está enviando mensagens**
**Sintomas**: Conexões estabelecidas mas sem comunicação

**Solução**:
1. Verificar se API Gateway está deployado
2. Verificar se rotas estão configuradas corretamente
3. Verificar se Lambda tem permissões para API Gateway

---

## 🧪 Testes de Diagnóstico

### **Teste 1: Conexão Simples**
```bash
python test_connection.py
```

### **Teste 2: Debug de Mensagens**
```bash
python debug_multiplayer.py
# Escolha opção 1
```

### **Teste 3: Múltiplas Conexões**
```bash
python debug_multiplayer.py
# Escolha opção 2
```

### **Teste 4: Verificar DynamoDB**
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('WebSocketConnections')

response = table.scan()
for item in response['Items']:
    print(f"Connection: {item.get('connection_id')}")
    print(f"Player: {item.get('player_id')}")
    print(f"Team: {item.get('team')}")
    print(f"Last Activity: {item.get('last_activity')}")
    print("---")
```

---

## 📊 Logs Importantes

### **Logs que devem aparecer quando um jogador entra:**
```
🆕 Nova conexão: connection_id
🎮 Jogador player_id entrando no jogo no time team
📢 Notificando entrada do jogador player_id para outros jogadores
📡 Broadcast para player_id (connection_id)
📊 Enviando game_state para connection_id com X jogadores ativos
```

### **Logs que devem aparecer quando um jogador se move:**
```
🎯 Ação recebida: update de connection_id
📡 Broadcast para player_id (connection_id)
```

---

## 🚀 Solução Rápida

Se o problema persistir, tente:

1. **Reiniciar tudo**:
   ```bash
   # 1. Limpar DynamoDB
   # 2. Redeploy Lambda
   # 3. Redeploy API Gateway
   # 4. Testar novamente
   ```

2. **Verificar variáveis de ambiente**:
   ```
   TABLE_NAME=WebSocketConnections
   AWS_REGION=us-east-1
   API_GATEWAY_ENDPOINT=https://sua-api.execute-api.us-east-1.amazonaws.com/production
   ```

3. **Verificar código atualizado**:
   - Certifique-se que o código do Lambda está atualizado
   - Verifique se a função `get_api_gateway_client` existe
   - Confirme que `broadcast_message` foi corrigida

---

## 📞 Próximos Passos

Se nenhuma solução funcionar:

1. **Executar debug completo**:
   ```bash
   python debug_multiplayer.py
   ```

2. **Verificar logs CloudWatch** para erros específicos

3. **Testar com wscat** para verificar comunicação WebSocket

4. **Verificar se há problemas de rede** ou firewall

---

## ✅ Checklist Final

- [ ] Lambda function atualizada com código corrigido
- [ ] DynamoDB tem múltiplos registros com player_id
- [ ] Broadcast está funcionando (logs mostram "📡 Broadcast")
- [ ] API Gateway está deployado e funcionando
- [ ] Permissões IAM estão corretas
- [ ] Teste de debug mostra comunicação entre jogadores

**Se todos os itens estiverem OK, o multiplayer deve funcionar! 🎉** 