#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REMOVER_TODOS_PATCHES.py
========================
Remove TODOS os blocos de código adicionados pelos patches
Procura por marcadores específicos e remove os blocos completos
"""

import shutil
from datetime import datetime
import re

print("🧹 REMOVENDO TODOS OS PATCHES...")
print("="*70)

# Backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"app.py.backup_{timestamp}"
shutil.copy2("app.py", backup)
print(f"✅ Backup: {backup}")

# Lê o ficheiro
with open("app.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

print(f"\n📊 Tamanho original: {len(conteudo)} caracteres")

# =====================================================
# IDENTIFICAR E REMOVER BLOCOS DE PATCHES
# =====================================================

# Padrão 1: Blocos com comentários de fixes
padroes_remover = [
    # Fixes com marcadores
    r'# ={50,}\n# 🔧 FIX:.*?\n# ={50,}.*?(?=\n    # ={50,}|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    r'# -{50,}\n# FIX \d+:.*?(?=\n    # -{50,}|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    r'# FIX:.*?\n.*?(?=\n    # FIX|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    
    # Blocos com emojis de fix
    r'    # 🎯.*?\n.*?(?=\n    # 🎯|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    r'    # ✅.*?\n.*?(?=\n    # ✅|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    
    # Context-aware
    r'    # ={50,}\n    # 🎯 CONTEXT-AWARE:.*?(?=\n    # ={50,}|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
    
    # Verificações prioritárias
    r'    # ={50,}\n    # 🎯 VERIFICAÇÕES PRIORITÁRIAS.*?(?=\n    # ={50,}|\n    [a-z_]+ =|\ndef |\nclass |\Z)',
]

conteudo_limpo = conteudo

for padrao in padroes_remover:
    matches = re.findall(padrao, conteudo_limpo, re.DOTALL)
    if matches:
        print(f"   🗑️  Encontrado {len(matches)} blocos para remover")
        conteudo_limpo = re.sub(padrao, '', conteudo_limpo, flags=re.DOTALL)

# =====================================================
# REMOVE LINHAS ÓRFÃS PROBLEMÁTICAS
# =====================================================

linhas = conteudo_limpo.split('\n')
linhas_limpas = []

for i, linha in enumerate(linhas):
    linha_stripped = linha.strip()
    
    # Remove linhas órfãs de break/continue/pass/return
    if linha_stripped in ['break', 'continue', 'pass', 'return']:
        # Verifica se próxima linha tem menos indentação (sinal que está órfão)
        if i+1 < len(linhas):
            proxima = linhas[i+1]
            espacos_atual = len(linha) - len(linha.lstrip())
            espacos_proximo = len(proxima) - len(proxima.lstrip())
            
            if espacos_proximo < espacos_atual or proxima.strip() == '':
                print(f"   🗑️  Removendo '{linha_stripped}' órfão na linha {i+1}")
                continue
    
    # Remove linhas com print de debugging órfãos
    if linha_stripped.startswith('print(f"🔄 Reformulado:'):
        print(f"   🗑️  Removendo print órfão na linha {i+1}")
        continue
    
    if linha_stripped.startswith('print(f"🎯 '):
        print(f"   🗑️  Removendo print órfão na linha {i+1}")
        continue
    
    linhas_limpas.append(linha)

conteudo_final = '\n'.join(linhas_limpas)

# =====================================================
# REMOVE IMPORTS DESNECESSÁRIOS
# =====================================================

# Remove imports duplicados ou órfãos
imports_remover = [
    'from modules.quintas_qdrant import executar_sql as executar_sql_qdrant',
    'USAR_QDRANT = True',
    'USAR_QDRANT = False',
]

for imp in imports_remover:
    if imp in conteudo_final:
        print(f"   🗑️  Removendo import: {imp}")
        conteudo_final = conteudo_final.replace(imp, '')

# =====================================================
# LIMPA LINHAS VAZIAS EXCESSIVAS
# =====================================================

# Remove mais de 3 linhas vazias consecutivas
conteudo_final = re.sub(r'\n{4,}', '\n\n\n', conteudo_final)

# =====================================================
# GUARDA
# =====================================================

with open("app.py", "w", encoding="utf-8") as f:
    f.write(conteudo_final)

reducao = len(conteudo) - len(conteudo_final)
print(f"\n📊 Tamanho final: {len(conteudo_final)} caracteres")
print(f"   Redução: {reducao} caracteres ({reducao/len(conteudo)*100:.1f}%)")

print("\n" + "="*70)
print("✅ PATCHES REMOVIDOS!")
print("="*70)
print()
print("🧪 TESTA AGORA:")
print("   streamlit run app.py")
print()
print("Se ainda houver erros, partilha a linha exata e vejo.")
print()
print(f"💾 Backup guardado: {backup}")
print("="*70)