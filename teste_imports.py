#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_imports.py
================
Testa se os módulos podem ser importados
"""

import sys
import os

print("="*70)
print("🧪 TESTE DE IMPORTS")
print("="*70)

# Mostra path
print(f"\n📂 Diretório atual: {os.getcwd()}")
print(f"📂 Python path: {sys.path[:3]}")

# Testa import de quintas_qdrant
print("\n1️⃣ Testando modules.quintas_qdrant...")
try:
    from modules.quintas_qdrant import listar_quintas
    print("   ✅ quintas_qdrant OK!")
    
    quintas = listar_quintas()
    print(f"   ✅ listar_quintas() retornou {len(quintas)} quintas")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

# Testa import de quintas_updater
print("\n2️⃣ Testando modules.quintas_updater...")
try:
    from modules.quintas_updater import atualizar_quinta
    print("   ✅ quintas_updater OK!")
    print("   ✅ atualizar_quinta() disponível")
except Exception as e:
    print(f"   ❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n   💡 SOLUÇÃO:")
    print("   Verifica se modules/quintas_updater.py existe:")
    print("   $ ls -la modules/quintas_updater.py")

# Verifica se ficheiro existe
print("\n3️⃣ Verificando ficheiro...")
updater_path = "modules/quintas_updater.py"
if os.path.exists(updater_path):
    print(f"   ✅ {updater_path} existe!")
    size = os.path.getsize(updater_path)
    print(f"   📏 Tamanho: {size} bytes")
else:
    print(f"   ❌ {updater_path} NÃO EXISTE!")
    print("\n   💡 COPIA O FICHEIRO:")
    print("   $ cp COPIAR_PARA_MODULES_quintas_updater.py modules/quintas_updater.py")

print("\n" + "="*70)