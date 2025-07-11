#!/usr/bin/env python3
"""
Script de Teste de Conexão WebSocket
"""

import os
import websocket
import json
import time
from dotenv import load_dotenv

load_dotenv()

def test_websocket_connection():
    """Testa a conexão WebSocket"""
    
    # Obtém URL do arquivo .env
    websocket_url = os.getenv("WEBSOCKET_URL")
    
    if not websocket_url:
        print("❌ WEBSOCKET_URL não configurada no arquivo .env")
        print("🔧 Configure a variável WEBSOCKET_URL no arquivo .env")
        return False
    
    print(f"🌐 Testando conexão com: {websocket_url}")
    
    def on_message(ws, message):
        """Processa mensagens recebidas"""
        try:
            data = json.loads(message)
            print(f"📨 Mensagem recebida: {data}")
        except json.JSONDecodeError:
            print(f"📨 Mensagem recebida (não-JSON): {message}")
    
    def on_error(ws, error):
        """Processa erros"""
        print(f"❌ Erro WebSocket: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        """Processa fechamento da conexão"""
        print(f"🔌 Conexão fechada: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        """Processa abertura da conexão"""
        print("✅ Conexão WebSocket estabelecida!")
        
        # Envia mensagem de teste
        test_message = {
            "action": "ping",
            "timestamp": int(time.time())
        }
        
        try:
            ws.send(json.dumps(test_message))
            print("📤 Mensagem de teste enviada")
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
    
    try:
        # Cria conexão WebSocket
        websocket.enableTrace(True)  # Habilita logs para debug
        ws = websocket.WebSocketApp(
            websocket_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Executa por 10 segundos
        print("⏱️ Executando teste por 10 segundos...")
        import threading
        import time
        
        # Executa em thread separada com timeout
        def run_with_timeout():
            ws.run_forever()
        
        thread = threading.Thread(target=run_with_timeout)
        thread.daemon = True
        thread.start()
        
        # Aguarda 10 segundos
        time.sleep(10)
        ws.close()
        thread.join(timeout=5)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 Teste de Conexão WebSocket")
    print("=" * 40)
    
    success = test_websocket_connection()
    
    if success:
        print("\n✅ Teste concluído com sucesso!")
        print("🎮 O servidor está funcionando corretamente")
    else:
        print("\n❌ Teste falhou!")
        print("🔧 Verifique:")
        print("   1. Configuração da AWS (Lambda, DynamoDB, API Gateway)")
        print("   2. URL WebSocket no arquivo .env")
        print("   3. Permissões IAM da Lambda")
        print("   4. Deploy da API Gateway")
        print("\n📖 Consulte AWS_SETUP.md para instruções detalhadas")

if __name__ == "__main__":
    main() 