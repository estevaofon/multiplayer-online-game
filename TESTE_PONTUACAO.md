# 🏆 Guia de Teste - Pontuação de Bandeiras

## Objetivo
Verificar se a pontuação está funcionando quando um jogador leva a bandeira do adversário para sua base.

## Como Funciona
1. Jogador captura a bandeira do time adversário
2. Jogador se move para a base do time adversário
3. Sistema verifica se está dentro da área da base (raio de 50 pixels)
4. Se estiver, marca ponto e reseta a bandeira

## Passos para Testar

### 1. Preparação
```bash
# Certifique-se de que o servidor está rodando
# Execute o cliente do jogo
python game-client.py
```

### 2. Teste Manual
1. **Conecte dois jogadores** (ou use o script de teste)
2. **Jogador 1 (Time Vermelho)**:
   - Vá até a bandeira azul (posição aproximada: 800, 100)
   - Pressione `F` para capturar a bandeira
   - Você deve ver "🏁 Você capturou a bandeira blue!"
3. **Leve a bandeira para a base azul**:
   - Mova-se para a base azul (posição: 800, 300)
   - Você deve ver no console do servidor:
     ```
     🏁 Verificando pontuação de bandeiras...
        Bandeira blue capturada por player_123
        Portador player_123 (red) em (800, 300)
        Distância até base blue (800, 300): 0.0
        🏆 PONTO! red marcou ponto com bandeira blue!
     ```
4. **Verifique o resultado**:
   - No cliente, você deve ver: "🏆 red marcou ponto! Placar: {'red': 1, 'blue': 0}"
   - A bandeira deve voltar para sua posição original
   - O placar deve ser atualizado

### 3. Teste com Script Automatizado
```bash
# Edite o arquivo test_flag_scoring.py
# Configure a WEBSOCKET_URL correta
# Execute o teste
python test_flag_scoring.py
```

## Posições das Bases
- **Base Vermelha**: (200, 300)
- **Base Azul**: (800, 300)

## Posições das Bandeiras
- **Bandeira Vermelha**: (200, 100)
- **Bandeira Azul**: (800, 100)

## Logs Esperados no Servidor

### Quando captura bandeira:
```
📥 Jogador player_123 capturou bandeira blue
🏁 Bandeira blue capturada por player_123
```

### Quando move para base:
```
🏁 Verificando pontuação de bandeiras...
   Bandeira blue capturada por player_123
   Portador player_123 (red) em (800, 300)
   Distância até base blue (800, 300): 0.0
   🏆 PONTO! red marcou ponto com bandeira blue!
```

### Quando não está na base:
```
🏁 Verificando pontuação de bandeiras...
   Bandeira blue capturada por player_123
   Portador player_123 (red) em (400, 300)
   Distância até base blue (800, 300): 400.0
   Ainda não chegou na base (precisa < 50)
```

## Problemas Comuns

### 1. Nenhum ponto é detectado
**Possíveis causas:**
- A função `check_flag_scoring` não está sendo chamada
- Dados do jogador não estão sendo lidos corretamente
- Distância calculada incorretamente

**Soluções:**
- Verifique os logs do servidor
- Confirme que a posição está dentro do raio de 50 pixels
- Verifique se o `player_id` está correto

### 2. Erro de conexão
**Possíveis causas:**
- WebSocket URL incorreta
- Servidor não está rodando
- Problemas de rede

**Soluções:**
- Verifique a URL do WebSocket
- Confirme que o servidor está ativo
- Teste a conectividade

### 3. Bandeira não reseta
**Possíveis causas:**
- Erro na atualização do estado da bandeira
- Problema no broadcast da mensagem

**Soluções:**
- Verifique os logs de erro
- Confirme que a mensagem `flag_scored` está sendo enviada

## Comandos Úteis para Debug

### Verificar estado atual:
```python
# No console do servidor
print(f"Estado das bandeiras: {game_state['flags']}")
print(f"Placar atual: {game_state['scores']}")
```

### Verificar jogadores ativos:
```python
# No console do servidor
active_players = get_active_players()
print(f"Jogadores ativos: {active_players}")
```

## Resultado Esperado
✅ Pontuação detectada automaticamente quando jogador chega na base com bandeira
✅ Placar atualizado em tempo real
✅ Bandeira retorna para posição original
✅ Mensagem de confirmação no cliente
✅ Logs detalhados no servidor 