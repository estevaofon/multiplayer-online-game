#!/usr/bin/env python3
"""
Script para debug dos scores
"""

import json
from decimal import Decimal

def test_score_conversion():
    """Testa a conversão de scores"""
    
    print("🧪 Testando conversão de scores...")
    print("=" * 40)
    
    # Simula scores do DynamoDB (com Decimal)
    dynamo_scores = {
        "red": Decimal("6"),
        "blue": Decimal("5")
    }
    
    print(f"1️⃣ Scores do DynamoDB: {dynamo_scores}")
    print(f"   Tipo: {type(dynamo_scores)}")
    print(f"   Tipo red: {type(dynamo_scores['red'])}")
    print(f"   Tipo blue: {type(dynamo_scores['blue'])}")
    
    # Simula a conversão que acontece no código
    converted_scores = {}
    for team, score in dynamo_scores.items():
        if isinstance(score, Decimal):
            converted_scores[team] = float(score)
        else:
            converted_scores[team] = score
    
    print(f"\n2️⃣ Scores convertidos: {converted_scores}")
    print(f"   Tipo: {type(converted_scores)}")
    print(f"   Tipo red: {type(converted_scores['red'])}")
    print(f"   Tipo blue: {type(converted_scores['blue'])}")
    
    # Testa serialização JSON
    try:
        json_str = json.dumps(converted_scores)
        print(f"\n3️⃣ JSON serializado: {json_str}")
        
        # Testa deserialização
        deserialized = json.loads(json_str)
        print(f"4️⃣ JSON deserializado: {deserialized}")
        print(f"   Tipo: {type(deserialized)}")
        
    except Exception as e:
        print(f"❌ Erro na serialização: {e}")
    
    # Testa scores padrão
    default_scores = {"red": 0, "blue": 0}
    print(f"\n5️⃣ Scores padrão: {default_scores}")
    print(f"   Tipo: {type(default_scores)}")
    
    # Simula o que acontece quando não há dados no DynamoDB
    empty_response = {}
    if "Item" not in empty_response:
        scores = default_scores
        print(f"6️⃣ Scores quando não há dados: {scores}")
    
    return True

def main():
    """Função principal"""
    print("🚀 Debug de Scores")
    print("=" * 40)
    
    if test_score_conversion():
        print("\n✅ Teste de conversão concluído!")
        print("📋 Verifique se os scores estão sendo convertidos corretamente")
    else:
        print("\n❌ Problema detectado na conversão")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 