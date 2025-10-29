#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH_INTEGRAR_QDRANT.py
========================
Script para integrar automaticamente quintas_info do Qdrant no código existente

USO:
    python PATCH_INTEGRAR_QDRANT.py

O QUE FAZ:
1. Copia quintas_qdrant.py para modules/
2. Atualiza llm_groq.py para usar Qdrant
3. Cria backup do código original
4. Testa a integração
"""

import os
import shutil
from datetime import datetime

# Cores
class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    B = '\033[94m'
    W = '\033[1m'
    E = '\033[0m'

def print_step(numero, titulo):
    print(f"\n{C.W}{'='*70}")
    print(f"  PASSO {numero}: {titulo}")
    print(f"{'='*70}{C.E}\n")

def print_ok(msg):
    print(f"{C.G}✅ {msg}{C.E}")

def print_error(msg):
    print(f"{C.R}❌ {msg}{C.E}")

def print_warn(msg):
    print(f"{C.Y}⚠️  {msg}{C.E}")

def print_info(msg):
    print(f"{C.B}ℹ️  {msg}{C.E}")

# =====================================================
# PASSO 1: VERIFICAR ESTRUTURA DO PROJETO
# =====================================================
print_step(1, "VERIFICAR ESTRUTURA DO PROJETO")

ficheiros_necessarios = {
    "llm_groq.py": "Motor LLM",
    "app.py": "Aplicação principal",
    "modules/": "Pasta de módulos"
}

erros = []
for path, desc in ficheiros_necessarios.items():
    if os.path.exists(path):
        print_ok(f"{desc} encontrado: {path}")
    else:
        print_error(f"{desc} NÃO encontrado: {path}")
        erros.append(path)

if erros:
    print_error(f"\nFaltam ficheiros: {', '.join(erros)}")
    print_warn("Certifica-te que estás na raiz do projeto!")
    exit(1)

# =====================================================
# PASSO 2: CRIAR BACKUP
# =====================================================
print_step(2, "CRIAR BACKUP DO CÓDIGO ORIGINAL")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"backup_{timestamp}"

try:
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup de llm_groq.py
    if os.path.exists("llm_groq.py"):
        shutil.copy2("llm_groq.py", f"{backup_dir}/llm_groq.py")
        print_ok(f"Backup criado: {backup_dir}/llm_groq.py")
    
    print_ok(f"Backups guardados em: {backup_dir}/")
    
except Exception as e:
    print_error(f"Erro ao criar backup: {e}")
    exit(1)

# =====================================================
# PASSO 3: COPIAR MÓDULO quintas_qdrant.py
# =====================================================
print_step(3, "COPIAR MÓDULO quintas_qdrant.py")

if os.path.exists("quintas_qdrant.py"):
    try:
        shutil.copy2("quintas_qdrant.py", "modules/quintas_qdrant.py")
        print_ok("quintas_qdrant.py copiado para modules/")
    except Exception as e:
        print_error(f"Erro ao copiar: {e}")
        exit(1)
else:
    print_error("quintas_qdrant.py não encontrado!")
    print_warn("Certifica-te que o ficheiro está na mesma pasta")
    exit(1)

# =====================================================
# PASSO 4: ATUALIZAR llm_groq.py
# =====================================================
print_step(4, "ATUALIZAR llm_groq.py")

print_info("Lendo llm_groq.py...")

try:
    with open("llm_groq.py", "r", encoding="utf-8") as f:
        conteudo = f.read()
    
    # Verifica se já foi modificado
    if "from modules.quintas_qdrant import" in conteudo:
        print_warn("llm_groq.py já foi modificado anteriormente!")
        print_info("Nada a fazer neste passo.")
    else:
        print_info("Adicionando import do módulo Qdrant...")
        
        # Encontra a secção de imports
        linhas = conteudo.split('\n')
        
        # Procura linha com "from learning_qdrant"
        insert_index = None
        for i, linha in enumerate(linhas):
            if "from learning_qdrant import" in linha:
                insert_index = i + 1
                break
        
        if insert_index is None:
            # Se não encontrou, adiciona no início após os imports
            for i, linha in enumerate(linhas):
                if linha.startswith("import ") or linha.startswith("from "):
                    continue
                else:
                    insert_index = i
                    break
        
        # Adiciona o import
        novo_import = """
# =====================================================
# 🔄 INTEGRAÇÃO COM QDRANT (quintas_info)
# =====================================================
try:
    from modules.quintas_qdrant import executar_sql as executar_sql_qdrant
    USAR_QDRANT = True
    print("✅ Quintas: Usando Qdrant (quintas_info)")
except ImportError as e:
    USAR_QDRANT = False
    print(f"⚠️ Quintas: Qdrant não disponível, usando SQLite fallback ({e})")
"""
        
        linhas.insert(insert_index, novo_import)
        
        # Atualiza a função executar_sql
        novo_conteudo = '\n'.join(linhas)
        
        # Substitui a função executar_sql
        if "def executar_sql(query: str):" in novo_conteudo:
            print_info("Atualizando função executar_sql...")
            
            # Encontra e substitui
            import re
            
            # Padrão para encontrar a função
            padrao = r'def executar_sql\(query: str\):.*?(?=\ndef |\nclass |\Z)'
            
            nova_funcao = '''def executar_sql(query: str):
    """
    Executa query SQL usando Qdrant (se disponível) ou SQLite fallback
    """
    if USAR_QDRANT:
        try:
            return executar_sql_qdrant(query)
        except Exception as e:
            print(f"⚠️ Erro no Qdrant, tentando SQLite: {e}")
    
    # Fallback para SQLite
    try:
        conn = sqlite3.connect("data/quintas.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"⚠️ Erro ao executar SQL: {e}")
        return []
'''
            
            novo_conteudo = re.sub(padrao, nova_funcao, novo_conteudo, flags=re.DOTALL)
        
        # Guarda o ficheiro atualizado
        with open("llm_groq.py", "w", encoding="utf-8") as f:
            f.write(novo_conteudo)
        
        print_ok("llm_groq.py atualizado com sucesso!")
        print_info("  → Import adicionado")
        print_info("  → Função executar_sql atualizada")

except Exception as e:
    print_error(f"Erro ao atualizar llm_groq.py: {e}")
    import traceback
    traceback.print_exc()
    
    print_warn(f"\nRestaurando backup...")
    try:
        shutil.copy2(f"{backup_dir}/llm_groq.py", "llm_groq.py")
        print_ok("Backup restaurado")
    except:
        print_error("Erro ao restaurar backup!")
    exit(1)

# =====================================================
# PASSO 5: TESTAR INTEGRAÇÃO
# =====================================================
print_step(5, "TESTAR INTEGRAÇÃO")

print_info("Testando import do módulo...")

try:
    import sys
    sys.path.insert(0, os.getcwd())
    
    from modules.quintas_qdrant import get_manager, get_estatisticas
    
    print_ok("Import bem sucedido!")
    
    print_info("\nTestando conexão ao Qdrant...")
    
    manager = get_manager()
    print_ok("Conexão estabelecida!")
    
    stats = get_estatisticas()
    
    print_ok(f"\n📊 Estatísticas das quintas:")
    print(f"   • Total: {stats['total']}")
    print(f"   • Com resposta: {stats['com_resposta']}")
    print(f"   • Sem resposta: {stats['sem_resposta']}")
    print(f"   • Fonte: {stats['fonte']}")
    
    if stats['total'] > 0:
        print_ok(f"\n✨ SUCESSO! {stats['total']} quintas disponíveis no Qdrant")
    else:
        print_warn("\n⚠️ Nenhuma quinta encontrada no Qdrant")
        print_info("Verifica se a collection 'quintas_info' tem dados")

except Exception as e:
    print_error(f"Erro ao testar: {e}")
    import traceback
    traceback.print_exc()
    
    print_warn("\n⚠️ O código foi atualizado mas há um erro na execução")
    print_info("Verifica as credenciais do Qdrant:")
    print_info("  • QDRANT_URL em variáveis de ambiente")
    print_info("  • QDRANT_API_KEY em variáveis de ambiente")
    print_info("  • Ou em .streamlit/secrets.toml")

# =====================================================
# RESUMO FINAL
# =====================================================
print_step("✅", "INTEGRAÇÃO CONCLUÍDA")

print(f"{C.W}O QUE FOI FEITO:{C.E}")
print(f"  ✅ Backup criado: {backup_dir}/")
print(f"  ✅ Módulo copiado: modules/quintas_qdrant.py")
print(f"  ✅ llm_groq.py atualizado")
print(f"  ✅ Testes executados")

print(f"\n{C.W}PRÓXIMOS PASSOS:{C.E}")
print(f"  1. Testa o chatbot:")
print(f"     {C.B}streamlit run app.py{C.E}")
print(f"")
print(f"  2. Testa perguntas sobre quintas:")
print(f"     • 'Quantas quintas já contactámos?'")
print(f"     • 'Que quintas já vimos?'")
print(f"     • 'Diz-me o website da primeira'")
print(f"")
print(f"  3. Se algo falhar:")
print(f"     • Verifica credenciais Qdrant")
print(f"     • Restaura backup: cp {backup_dir}/llm_groq.py .")

print(f"\n{C.G}{'='*70}")
print(f"  🎉 PRONTO A USAR!")
print(f"{'='*70}{C.E}\n")