#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH_CORRIGIR_CONFIRMACOES.py
Corrige o sistema de confirmações para funcionar com encoding UTF-8
"""

import os
import shutil
from datetime import datetime

print("🔧 CORRIGINDO SISTEMA DE CONFIRMAÇÕES...")
print("="*60)

# Backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"backup_{timestamp}"
os.makedirs(backup_dir, exist_ok=True)

# Backup de modules/confirmacoes.py
if os.path.exists("modules/confirmacoes.py"):
    shutil.copy2("modules/confirmacoes.py", f"{backup_dir}/confirmacoes.py")
    print(f"✅ Backup: {backup_dir}/confirmacoes.py")

# Lê o ficheiro
with open("modules/confirmacoes.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

# Substitui a função confirmar_pessoa para normalizar nomes
novo_codigo = '''
def normalizar_nome(nome):
    """Normaliza nome para comparação (remove acentos, minúsculas)"""
    import unicodedata
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.lower().strip()

def confirmar_pessoa(nome, confirmado_por=None):
    """Confirma uma pessoa"""
    try:
        # Normaliza o nome para busca
        nome_normalizado = normalizar_nome(nome)
        
        # Busca o perfil (tenta várias formas)
        perfil = pm.buscar_perfil(nome)
        
        # Se não encontrou, tenta buscar todos e comparar normalizado
        if not perfil:
            print(f"⚠️ Tentando busca alternativa para '{nome}'...")
            todos_perfis = pm.listar_todos_perfis()
            for p in todos_perfis:
                if normalizar_nome(p.get("nome", "")) == nome_normalizado:
                    perfil = p
                    print(f"✅ Encontrado: {p.get('nome')}")
                    break
        
        if not perfil:
            return {
                "sucesso": False,
                "mensagem": f"'{nome}' nao esta na lista de convidados",
                "familia_sugerida": []
            }
'''

# Substitui a função
import re
padrao = r'def confirmar_pessoa\(nome, confirmado_por=None\):.*?(?=\ndef |$)'
conteudo = re.sub(padrao, novo_codigo, conteudo, flags=re.DOTALL)

# Guarda
with open("modules/confirmacoes.py", "w", encoding="utf-8") as f:
    f.write(conteudo)

print("✅ modules/confirmacoes.py atualizado!")
print("\n" + "="*60)
print("✨ CORRIGIDO! Testa agora:")
print("   streamlit run app.py")
print("="*60)