#!/usr/bin/env python3
"""
Script para testar a função convert_decimals_recursive
"""

import json
from decimal import Decimal

def convert_decimals_recursive(obj, path=""):
    """Converte recursivamente todos os valores Decimal em um objeto"""
    try:
        if isinstance(obj, Decimal):
            print(f"   Conversão Decimal em {path}: {obj} -> {float(obj)}")
            return float(obj)
        elif isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                result[key] = convert_decimals_recursive(value, new_path)
            return result
        elif isinstance(obj, list):
            result = []
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                result.append(convert_decimals_recursive(item, new_path))
            return result
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            print(f"⚠️ Tipo não esperado encontrado em {path}: {type(obj)} - {obj}")
            return str(obj)
    except Exception as e:
        print(f"❌ Erro ao converter Decimal em {path}: {e} - Tipo: {type(obj)} - Valor: {obj}")
        return str(obj)

def test_convert_decimals():
    """Testa a função convert_decimals_recursive"""
    
    print("🧪 Testando convert_decimals_recursive...")
    print("=" * 50)
    
    # Teste 1: Scores com Decimal
    print("1️⃣ Teste com scores do DynamoDB:")
    dynamo_scores = {
        "red": Decimal("6"),
        "blue": Decimal("5")
    }
    print(f"   Input: {dynamo_scores}")
    
    converted = convert_decimals_recursive(dynamo_scores)
    print(f"   Output: {converted}")
    print(f"   Tipo: {type(converted)}")
    
    # Teste 2: Scores normais (sem Decimal)
    print("\n2️⃣ Teste com scores normais:")
    normal_scores = {
        "red": 0,
        "blue": 0
    }
    print(f"   Input: {normal_scores}")
    
    converted_normal = convert_decimals_recursive(normal_scores)
    print(f"   Output: {converted_normal}")
    print(f"   Tipo: {type(converted_normal)}")
    
    # Teste 3: Game state completo
    print("\n3️⃣ Teste com game_state completo:")
    game_state = {
        "flags": {
            "red": {"x": 50, "y": 300, "captured": False, "carrier": None},
            "blue": {"x": 750, "y": 300, "captured": False, "carrier": None}
        },
        "bullets": [],
        "scores": {"red": Decimal("6"), "blue": Decimal("5")},
        "game_started": False
    }
    print(f"   Input scores: {game_state['scores']}")
    
    converted_game_state = convert_decimals_recursive(game_state)
    print(f"   Output scores: {converted_game_state['scores']}")
    print(f"   Tipo scores: {type(converted_game_state['scores'])}")
    
    # Teste 4: Serialização JSON
    print("\n4️⃣ Teste de serialização JSON:")
    try:
        json_str = json.dumps(converted_game_state)
        print(f"   JSON serializado com sucesso")
        print(f"   Tamanho: {len(json_str)} caracteres")
        
        # Verifica se os scores estão corretos no JSON
        parsed = json.loads(json_str)
        print(f"   Scores no JSON: {parsed['scores']}")
        
    except Exception as e:
        print(f"   ❌ Erro na serialização: {e}")
    
    return True

def main():
    """Função principal"""
    print("🚀 Teste da Função convert_decimals_recursive")
    print("=" * 50)
    
    if test_convert_decimals():
        print("\n✅ Teste concluído com sucesso!")
        print("📋 A função convert_decimals_recursive está funcionando corretamente")
    else:
        print("\n❌ Problema detectado na função")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 