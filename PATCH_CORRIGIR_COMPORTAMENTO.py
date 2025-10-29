#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REVERTER_TUDO.py
================
Reverte app.py para o backup ORIGINAL (antes de TODOS os patches)
"""

import os
import glob
import shutil
from datetime import datetime

print("🔄 REVERTENDO PARA VERSÃO ORIGINAL...")
print("="*70)

# =====================================================
# PROCURA O BACKUP MAIS ANTIGO (original)
# =====================================================
backups = sorted(glob.glob("backup_*"))

if not backups:
    backups = sorted(glob.glob("app.py.backup_*"))

if not backups:
    print("❌ Nenhum backup encontrado!")
    print()
    print("⚠️ SOLUÇÃO ALTERNATIVA:")
    print("  1. Vai ao GitHub do projeto")
    print("  2. Baixa app.py original")
    print("  3. Ou usa 'git checkout app.py' se tens git")
    exit(1)

# Usa o PRIMEIRO backup (mais antigo = original)
backup_original = backups[0]

print(f"📦 Backups encontrados: {len(backups)}")
print(f"✅ Usando o mais antigo (original): {backup_original}")

# Verifica se tem app.py dentro
if os.path.isdir(backup_original):
    backup_file = os.path.join(backup_original, "app.py")
else:
    backup_file = backup_original

if not os.path.exists(backup_file):
    print(f"❌ {backup_file} não existe!")
    exit(1)

# =====================================================
# GUARDA O ESTADO ATUAL (com erros)
# =====================================================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
erro_file = f"app.py.com_erros_{timestamp}"

shutil.copy2("app.py", erro_file)
print(f"💾 App.py atual (com erros) guardado: {erro_file}")

# =====================================================
# RESTAURA ORIGINAL
# =====================================================
shutil.copy2(backup_file, "app.py")
print(f"✅ app.py restaurado do backup original!")

# =====================================================
# LIMPA BACKUPS INTERMÉDIOS (opcional)
# =====================================================
print()
resposta = input("🗑️  Queres apagar backups intermédios com erros? (s/N): ")

if resposta.lower() == 's':
    for backup in backups[1:]:  # Mantém o primeiro (original)
        try:
            if os.path.isdir(backup):
                shutil.rmtree(backup)
            else:
                os.remove(backup)
            print(f"  🗑️  Apagado: {backup}")
        except:
            pass
    print("✅ Backups intermédios apagados")

print("\n" + "="*70)
print("✅ REVERTIDO PARA VERSÃO ORIGINAL!")
print("="*70)
print()
print("📊 ESTADO ATUAL:")
print(f"  ✅ app.py = versão original (funcional)")
print(f"  💾 Backup do estado com erros: {erro_file}")
print(f"  📦 Backup original mantido: {backup_original}")
print()
print("🚀 PRÓXIMOS PASSOS:")
print("  1. streamlit run app.py  (deve funcionar!)")
print("  2. Vou criar fixes SIMPLES e MANUAIS")
print("  3. Aplicas 1 de cada vez, testando entre cada")
print()
print("="*70)