# 🎯 Guia de Teste - Atribuição Automática de Times

## Objetivo
Verificar se a atribuição automática de times está funcionando corretamente, balanceando os jogadores entre vermelho e azul.

## Como Funciona
1. Cliente se conecta sem especificar time
2. Servidor conta jogadores ativos em cada time
3. Servidor atribui o time com menos jogadores
4. Cliente recebe confirmação com time atribuído

## Passos para Testar

### 1. Preparação
```bash
# Certifique-se de que o servidor está rodando
# Execute o cliente do jogo
python game-client.py
```

### 2. Teste Manual - Um Jogador
1. **Execute o cliente**: `python game-client.py`
2. **Verifique os logs do servidor**:
   ```
   🎯 Atribuindo time automaticamente para player_123
      Jogadores ativos: 0
      Time vermelho: 0 jogadores
      Time azul: 0 jogadores
      ➡️ Atribuindo time VERMELHO (menos jogadores)
   🎮 Jogador player_123 entrando no jogo no time red na posição (200, 300)
   ```
3. **Verifique o cliente**: Deve mostrar "✅ Você entrou no jogo! Time: red"

### 3. Teste Manual - Dois Jogadores
1. **Execute dois clientes** em terminais separados
2. **Primeiro jogador** deve receber time vermelho
3. **Segundo jogador** deve receber time azul
4. **Verifique os logs do servidor**:
   ```
   # Primeiro jogador
   🎯 Atribuindo time automaticamente para player_1
      Jogadores ativos: 0
      Time vermelho: 0 jogadores
      Time azul: 0 jogadores
      ➡️ Atribuindo time VERMELHO (menos jogadores)
   
   # Segundo jogador
   🎯 Atribuindo time automaticamente para player_2
      Jogadores ativos: 1
      Time vermelho: 1 jogadores
      Time azul: 0 jogadores
      ➡️ Atribuindo time AZUL (menos jogadores)
   ```

### 4. Teste com Script Automatizado
```bash
# Edite o arquivo test_team_assignment.py
# Configure a WEBSOCKET_URL correta
# Execute o teste
python test_team_assignment.py
```

## Logs Esperados

### Quando um jogador entra:
```
🎯 Atribuindo time automaticamente para player_123
   Jogadores ativos: 2
   Time vermelho: 1 jogadores
   Time azul: 1 jogadores
   ➡️ Atribuindo time VERMELHO (menos jogadores)
🎮 Jogador player_123 entrando no jogo no time red na posição (200, 300)
```

### Quando o cliente recebe confirmação:
```
📨 Cliente recebeu: player_joined
✅ Você entrou no jogo! Time: red
```

## Problemas Comuns

### 1. Todos os jogadores ficam no time vermelho
**Possíveis causas:**
- A função `get_active_players()` não está retornando dados corretos
- Problema na contagem de jogadores por time
- Cache do DynamoDB não está atualizado

**Soluções:**
- Verifique se `ConsistentRead=True` está sendo usado
- Confirme que os dados estão sendo salvos corretamente no DynamoDB
- Verifique os logs de contagem de jogadores

### 2. Jogador não recebe confirmação de time
**Possíveis causas:**
- Mensagem `player_joined` não está sendo enviada
- Problema na conexão WebSocket
- Erro no processamento da mensagem

**Soluções:**
- Verifique se a mensagem `player_joined` com `player_data` está sendo enviada
- Confirme que o cliente está processando a mensagem corretamente
- Verifique logs de erro no servidor

### 3. Balanceamento incorreto
**Possíveis causas:**
- Lógica de contagem incorreta
- Jogadores desconectados não estão sendo removidos
- Race condition na atribuição

**Soluções:**
- Verifique a lógica de contagem no servidor
- Confirme que jogadores desconectados são removidos
- Adicione logs detalhados para debug

## Comandos Úteis para Debug

### Verificar jogadores ativos:
```python
# No console do servidor
active_players = get_active_players()
print(f"Jogadores ativos: {active_players}")

red_count = sum(1 for p in active_players.values() if p.get("team") == "red")
blue_count = sum(1 for p in active_players.values() if p.get("team") == "blue")
print(f"Vermelho: {red_count}, Azul: {blue_count}")
```

### Verificar conexões no DynamoDB:
```python
# No console do servidor
response = connections_table.scan(ConsistentRead=True)
for item in response.get("Items", []):
    print(f"{item['connection_id']}: {item.get('player_id')} - {item.get('team')}")
```

## Resultado Esperado
✅ Primeiro jogador recebe time vermelho
✅ Segundo jogador recebe time azul
✅ Terceiro jogador recebe time vermelho
✅ Quarto jogador recebe time azul
✅ Balanceamento mantido com mais jogadores
✅ Logs detalhados mostrando a lógica de atribuição

## Teste de Stress
Para testar com muitos jogadores:
1. Execute o script `test_team_assignment.py` com a função `test_multiple_players()`
2. Verifique se o balanceamento é mantido
3. Confirme que não há vazamentos de memória ou conexões órfãs 