#!/usr/bin/env python3
"""
Script de Instalação - Jogo Multiplayer Captura de Bandeira
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou superior é necessário!")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    return True

def install_dependencies():
    """Instala as dependências do projeto"""
    print("📦 Instalando dependências...")
    
    try:
        # Tenta instalar usando pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("✅ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Erro ao instalar dependências com pip")
        print("🔧 Tentando instalar manualmente...")
        
        try:
            dependencies = [
                "pygame>=2.6.1",
                "websocket-client>=1.8.0", 
                "python-dotenv>=1.1.1"
            ]
            
            for dep in dependencies:
                print(f"   Instalando {dep}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            
            print("✅ Dependências instaladas manualmente!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar {dep}: {e}")
            return False

def create_env_file():
    """Cria arquivo .env se não existir"""
    env_file = ".env"
    example_file = "env.example"
    
    if os.path.exists(env_file):
        print("✅ Arquivo .env já existe")
        return True
    
    if os.path.exists(example_file):
        print("📝 Criando arquivo .env a partir do exemplo...")
        try:
            shutil.copy(example_file, env_file)
            print("✅ Arquivo .env criado!")
            print("🔧 Edite o arquivo .env com sua URL WebSocket da AWS")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar .env: {e}")
            return False
    else:
        print("⚠️ Arquivo env.example não encontrado")
        print("🔧 Crie manualmente o arquivo .env com:")
        print("   WEBSOCKET_URL=wss://sua-api-real.execute-api.us-east-1.amazonaws.com/prod")
        return False

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    try:
        import pygame
        print("✅ Pygame instalado")
    except ImportError:
        print("❌ Pygame não encontrado")
        return False
    
    try:
        import websocket
        print("✅ WebSocket-client instalado")
    except ImportError:
        print("❌ WebSocket-client não encontrado")
        return False
    
    try:
        import dotenv
        print("✅ Python-dotenv instalado")
    except ImportError:
        print("❌ Python-dotenv não encontrado")
        return False
    
    return True

def main():
    """Função principal"""
    print("🚀 Setup do Jogo Multiplayer Captura de Bandeira")
    print("=" * 50)
    
    # Verifica versão do Python
    if not check_python_version():
        sys.exit(1)
    
    # Instala dependências
    if not install_dependencies():
        print("❌ Falha na instalação das dependências")
        sys.exit(1)
    
    # Verifica se as dependências foram instaladas
    if not check_dependencies():
        print("❌ Algumas dependências não foram instaladas corretamente")
        sys.exit(1)
    
    # Cria arquivo .env
    create_env_file()
    
    print("\n🎉 Setup concluído com sucesso!")
    print("\n📋 Próximos passos:")
    print("1. Configure sua AWS (DynamoDB + Lambda + API Gateway)")
    print("2. Edite o arquivo .env com sua URL WebSocket")
    print("3. Execute: python game_client.py")
    print("\n📖 Consulte o README.md para instruções detalhadas")

if __name__ == "__main__":
    main() 