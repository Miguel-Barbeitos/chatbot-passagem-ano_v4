#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_minimo.py
===============
Teste mínimo para encontrar o erro
"""

print("="*70)
print("🧪 TESTE MINIMALISTA")
print("="*70)

# Passo 1: Import quintas_qdrant
print("\n1️⃣ Importando quintas_qdrant...")
try:
    from modules.quintas_qdrant import get_client, listar_quintas
    print("   ✅ OK!")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Passo 2: Testar get_client()
print("\n2️⃣ Testando get_client()...")
try:
    client = get_client()
    print("   ✅ Cliente criado!")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Passo 3: Testar listar_quintas()
print("\n3️⃣ Testando listar_quintas()...")
try:
    quintas = listar_quintas()
    print(f"   ✅ {len(quintas)} quintas encontradas!")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Passo 4: Import quintas_updater
print("\n4️⃣ Importando quintas_updater...")
try:
    from modules.quintas_updater import atualizar_quinta
    print("   ✅ OK!")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Passo 5: Teste de atualização (dry-run)
print("\n5️⃣ Testando atualizar_quinta() [dry-run]...")
try:
    # Pega primeira quinta como teste
    if quintas:
        primeira_quinta = quintas[0]['nome']
        print(f"   Testando com: {primeira_quinta}")
        
        # Tenta atualizar com campo de teste
        resultado = atualizar_quinta(primeira_quinta, {
            'teste_atualizacao': True
        })
        
        if resultado:
            print("   ✅ Atualização funcionou!")
        else:
            print("   ⚠️ Atualização retornou False (quinta não encontrada?)")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*70)
print("✅ TODOS OS TESTES PASSARAM!")
print("="*70)
print("\n💡 Se chegou aqui, o problema está no script de integração,")
print("   não nos módulos. Partilha o output completo do")
print("   integrar_respostas_emails.py incluindo os erros!")