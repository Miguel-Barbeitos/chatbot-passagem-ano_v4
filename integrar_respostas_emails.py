#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrar_respostas_emails.py
=============================
Processa emails de data/emails_quinta/processados
e atualiza Qdrant com informação de quais quintas responderam
"""

import os
import sys
import json
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime

# Adiciona path dos módulos
sys.path.insert(0, os.path.dirname(__file__))

print("="*70)
print("📧 INTEGRAÇÃO DE RESPOSTAS DE EMAILS")
print("="*70)

# =====================================================
# PASSO 1: PROCESSAR EMAILS
# =====================================================
print("\n📂 PASSO 1: Processar emails...")

emails_dir = "data/emails_quintas/processados"

if not os.path.exists(emails_dir):
    print(f"❌ Pasta não encontrada: {emails_dir}")
    print("⚠️ Certifica-te que estás na raiz do projeto!")
    sys.exit(1)

# Lista todos os .eml
eml_files = [f for f in os.listdir(emails_dir) if f.endswith('.eml')]
print(f"✅ Encontrados {len(eml_files)} emails")

# Mapeia domínios/palavras para nomes de quintas
# (ajusta conforme os nomes no Qdrant)
MAPA_QUINTAS = {
    'caminodelaermita': 'C.R. Camino de la Ermita & Spa',
    'casasdotoural': 'Casas do Toural',
    'montedosobreiro': 'Monte do Sobreiro',
    'solardealqueva': 'Solar de Alqueva',
    'apulia': 'Centro Escutista de Apúlia',
    'casalagoa': 'Casa da Lagoa',
    'casaforja': 'Casa da Forja',
    'casasromaria': 'Casas de Romaria',
    'casasmanolo': 'Casas Rurales Manolo',
    'brovales': 'El Paraíso de Brovales',
    'monsaraz': 'Estalagem de Monsaraz',
    'quintaquinhas': 'Quinta das Quinhas',
    'patiofigueira': 'Pátio da Figueira',
    'maverick': 'The Maverick',
}

quintas_responderam = {}

for eml_file in eml_files:
    try:
        filepath = os.path.join(emails_dir, eml_file)
        
        with open(filepath, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        assunto = str(msg.get('subject', ''))
        de = str(msg.get('from', ''))
        data_email = str(msg.get('date', ''))
        
        # Ignora não-entregas
        if 'undeliverable' in assunto.lower():
            continue
        
        # Verifica se é resposta
        if not any(prefix in assunto for prefix in ['Re:', 'RE:', 're:', 'Fwd:', 'FW:']):
            continue
        
        # Tenta identificar quinta
        nome_quinta = None
        email_lower = de.lower() + ' ' + eml_file.lower()
        
        for chave, nome in MAPA_QUINTAS.items():
            if chave in email_lower:
                nome_quinta = nome
                break
        
        if not nome_quinta:
            # Tenta extrair do filename
            nome_arquivo = eml_file.replace('.eml', '').replace('_', ' ')
            # Procura nome similar no mapa
            for chave, nome in MAPA_QUINTAS.items():
                if chave in nome_arquivo.lower():
                    nome_quinta = nome
                    break
        
        if nome_quinta:
            quintas_responderam[nome_quinta] = {
                'email': de,
                'data_resposta': data_email,
                'assunto': assunto,
                'arquivo': eml_file
            }
            print(f"  ✅ {nome_quinta}")
        else:
            print(f"  ⚠️ Quinta não identificada: {eml_file[:50]}")
    
    except Exception as e:
        print(f"  ❌ Erro em {eml_file}: {e}")

print(f"\n📊 Total de respostas identificadas: {len(quintas_responderam)}")

# =====================================================
# PASSO 2: ATUALIZAR QDRANT
# =====================================================
print("\n🔄 PASSO 2: Atualizar Qdrant...")
print("="*70)

atualizadas = 0
nao_encontradas = []

print("\n🔍 DEBUG - Tentando importar módulos...")
try:
    print("  → Importando listar_quintas de modules.quintas_qdrant...")
    from modules.quintas_qdrant import listar_quintas
    print("  ✅ listar_quintas importado!")
    
    print("  → Importando atualizar_quinta de modules.quintas_updater...")
    from modules.quintas_updater import atualizar_quinta
    print("  ✅ atualizar_quinta importado!")
    
    print("\n🔍 DEBUG - Listando quintas do Qdrant...")
    todas_quintas = listar_quintas()
    print(f"  ✅ {len(todas_quintas)} quintas encontradas!")
    
    print("\n🔍 DEBUG - Quintas a atualizar:")
    for nome in quintas_responderam.keys():
        print(f"  • {nome}")
    
    print("\n📦 Iniciando atualizações...")
    print("-"*70)
    
    # Atualiza cada quinta
    for nome_quinta, info in quintas_responderam.items():
        print(f"\n🔄 Processando: {nome_quinta}")
        
        # Procura a quinta no Qdrant
        quinta = next((q for q in todas_quintas if q['nome'] == nome_quinta), None)
        
        if quinta:
            print(f"  ✅ Quinta encontrada no Qdrant")
            # Atualiza com info de resposta
            try:
                campos_atualizar = {
                    'respondeu': True,
                    'email_resposta': info['email'],
                    'data_resposta': info['data_resposta'],
                    'status': 'respondeu'
                }
                print(f"  → Atualizando com campos: {list(campos_atualizar.keys())}")
                
                resultado = atualizar_quinta(nome_quinta, campos_atualizar)
                
                if resultado:
                    print(f"  ✅ SUCESSO!")
                    atualizadas += 1
                else:
                    print(f"  ⚠️ Função retornou False")
                    
            except Exception as e:
                print(f"  ❌ ERRO na atualização: {e}")
                import traceback
                traceback.print_exc()
        else:
            nao_encontradas.append(nome_quinta)
            print(f"  ⚠️ Não encontrada no Qdrant")
            print(f"     Procurei por: '{nome_quinta}'")
            print(f"     Primeiras 3 quintas do Qdrant:")
            for q in todas_quintas[:3]:
                print(f"       - '{q['nome']}'")
    
    print("\n" + "="*70)
    print(f"✅ RESULTADO: {atualizadas} de {len(quintas_responderam)} atualizadas")
    
    if nao_encontradas:
        print(f"\n⚠️ Não encontradas no Qdrant ({len(nao_encontradas)}):")
        for nome in nao_encontradas:
            print(f"  • {nome}")
        print("\n💡 Dica: Verifica se os nomes no MAPA_QUINTAS correspondem")
        print("   exatamente aos nomes no Qdrant (incluindo acentos, espaços, etc.)")

except ImportError as e:
    print(f"\n❌ ERRO DE IMPORT: {e}")
    print("\n💡 SOLUÇÃO:")
    print("  1. Verifica: ls -la modules/quintas_updater.py")
    print("  2. Se não existir, copia o ficheiro modules_quintas_updater.py")
    print("     para modules/quintas_updater.py")
    
    # Guarda JSON para importação manual
    output_file = "quintas_responderam.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(quintas_responderam, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON guardado: {output_file}")
    
    atualizadas = 'N/A (erro de import)'

except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {e}")
    print("\n🔍 TRACEBACK COMPLETO:")
    import traceback
    traceback.print_exc()
    
    atualizadas = 'N/A (erro)'


# =====================================================
# PASSO 3: VERIFICAÇÃO
# =====================================================
print("\n🔍 PASSO 3: Verificação...")

try:
    quintas_atualizadas = listar_quintas()
    com_resposta = [q for q in quintas_atualizadas if q.get('respondeu')]
    
    print(f"✅ Quintas marcadas como 'respondeu' no Qdrant: {len(com_resposta)}")
    
    if com_resposta:
        print("\n📋 Lista:")
        for q in com_resposta:
            print(f"  • {q['nome']}")
    
except Exception as e:
    print(f"⚠️ Não foi possível verificar: {e}")

# =====================================================
# RESUMO
# =====================================================
print("\n" + "="*70)
print("✨ INTEGRAÇÃO CONCLUÍDA!")
print("="*70)
print(f"""
📊 RESUMO:
  • Emails processados: {len(eml_files)}
  • Respostas identificadas: {len(quintas_responderam)}
  • Quintas atualizadas no Qdrant: {atualizadas if 'atualizadas' in locals() else 'N/A'}

🎯 PRÓXIMO PASSO:
  1. Testa no chatbot: "Quantas quintas responderam?"
  2. O chatbot deve mostrar as quintas atualizadas!
  
💡 Se houver quintas não encontradas, atualiza o MAPA_QUINTAS
   no início deste script com os nomes corretos do Qdrant.
""")
print("="*70)