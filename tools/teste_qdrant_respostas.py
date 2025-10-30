#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teste_qdrant_respostas.py
==========================
Verifica quais quintas têm resposta no Qdrant
"""

import os
import sys

# Configuração para bypass SSL
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Adiciona path dos módulos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def testar_quintas_qdrant():
    """Testa quintas no Qdrant"""
    print("🧪 TESTE: QUINTAS NO QDRANT")
    print("=" * 70)
    
    try:
        from modules.quintas_qdrant import listar_quintas, get_estatisticas
        
        # Lista todas as quintas
        quintas = listar_quintas()
        
        print(f"\n📦 Total de quintas: {len(quintas)}")
        
        # Analisa campos de resposta
        print("\n🔍 ANÁLISE DE CAMPOS:")
        print("-" * 70)
        
        campos_encontrados = set()
        quintas_com_resposta = []
        quintas_sem_resposta = []
        
        for q in quintas:
            # Coleta todos os campos
            campos_encontrados.update(q.keys())
            
            # Verifica se tem resposta
            resposta = q.get('resposta')
            if resposta and resposta not in ['', None, 'Sem resposta', 'Erro email']:
                quintas_com_resposta.append(q)
            else:
                quintas_sem_resposta.append(q)
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   ✅ Com resposta: {len(quintas_com_resposta)}")
        print(f"   ❌ Sem resposta: {len(quintas_sem_resposta)}")
        
        print(f"\n📝 CAMPOS ENCONTRADOS:")
        for campo in sorted(campos_encontrados):
            print(f"   • {campo}")
        
        # Mostra exemplos de quintas com resposta
        print(f"\n✅ QUINTAS COM RESPOSTA ({len(quintas_com_resposta)}):")
        print("-" * 70)
        for i, q in enumerate(quintas_com_resposta[:5], 1):
            nome = q.get('nome', 'N/A')
            resposta = q.get('resposta', 'N/A')
            resumo = q.get('resumo_resposta', 'N/A')[:80]
            print(f"\n{i}. {nome}")
            print(f"   Resposta: {resposta}")
            print(f"   Resumo: {resumo}...")
        
        if len(quintas_com_resposta) > 5:
            print(f"\n   ...e mais {len(quintas_com_resposta) - 5}!")
        
        # Mostra exemplos de quintas SEM resposta
        print(f"\n❌ QUINTAS SEM RESPOSTA ({len(quintas_sem_resposta)}):")
        print("-" * 70)
        for i, q in enumerate(quintas_sem_resposta[:3], 1):
            nome = q.get('nome', 'N/A')
            resposta = q.get('resposta', 'N/A')
            print(f"{i}. {nome} - Resposta: '{resposta}'")
        
        # Estatísticas gerais
        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        print("-" * 70)
        stats = get_estatisticas()
        for chave, valor in stats.items():
            if isinstance(valor, dict):
                print(f"   {chave}:")
                for k, v in valor.items():
                    print(f"      • {k}: {v}")
            else:
                print(f"   {chave}: {valor}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_evento_json():
    """Testa leitura do event.json"""
    print("\n" + "=" * 70)
    print("🧪 TESTE: EVENT.JSON")
    print("=" * 70)
    
    try:
        from modules.organizacao import get_evento, get_tema_cor, get_datas_evento, get_orcamento
        
        evento = get_evento()
        print(f"\n✅ Evento carregado:")
        print(f"   Nome: {evento.get('nome')}")
        print(f"   Datas: {evento.get('data_inicio')} a {evento.get('data_fim')}")
        print(f"   Cor: {evento.get('cor')}")
        print(f"   Orçamento/pessoa: €{evento.get('orcamento_pessoa')}")
        
        tema = get_tema_cor()
        print(f"\n🎨 Tema:")
        print(f"   {tema}")
        
        datas = get_datas_evento()
        print(f"\n📅 Datas formatadas:")
        for k, v in datas.items():
            print(f"   {k}: {v}")
        
        orcamento = get_orcamento()
        print(f"\n💰 Orçamento:")
        print(f"   Por pessoa: €{orcamento['por_pessoa']}")
        print(f"   Total estimado: €{orcamento['total_estimado']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao ler event.json: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_responder_pergunta():
    """Testa função responder_pergunta_organizacao"""
    print("\n" + "=" * 70)
    print("🧪 TESTE: RESPONDER PERGUNTAS")
    print("=" * 70)
    
    try:
        from modules.organizacao import responder_pergunta_organizacao
        
        perguntas = [
            "Qual a cor da festa?",
            "Já temos quinta?",
            "Quantas quintas responderam?",
            "Quais são os dias?",
            "Quanto custa por pessoa?"
        ]
        
        for pergunta in perguntas:
            print(f"\n❓ {pergunta}")
            print("-" * 70)
            resposta = responder_pergunta_organizacao(pergunta)
            if resposta:
                print(resposta)
            else:
                print("⚠️ Não soube responder")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 INICIANDO TESTES...")
    print("=" * 70)
    
    # Teste 1: Quintas no Qdrant
    teste1 = testar_quintas_qdrant()
    
    # Teste 2: Event.json
    teste2 = testar_evento_json()
    
    # Teste 3: Responder perguntas
    teste3 = testar_responder_pergunta()
    
    # Resumo
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    print(f"   Quintas Qdrant: {'✅' if teste1 else '❌'}")
    print(f"   Event.json: {'✅' if teste2 else '❌'}")
    print(f"   Responder perguntas: {'✅' if teste3 else '❌'}")
    print()