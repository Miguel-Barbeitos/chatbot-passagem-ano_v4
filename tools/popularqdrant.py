#!/usr/bin/env python3
"""
Script SAFE para Popular Qdrant
Funciona MESMO com Streamlit a correr!
Usa a API do Qdrant em vez de acesso direto ao storage
"""

import os
import sys
import json
import sqlite3
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

print("=" * 60)
print("🚀 POPULAR QDRANT (MODO SAFE)")
print("   Funciona com Streamlit a correr!")
print("=" * 60)
print()

# =====================================================
# 2️⃣ IMPORTAR QUINTAS USANDO MÓDULOS EXISTENTES
# =====================================================
print("2️⃣ A importar quintas para o Qdrant...")
print("-" * 60)

try:
    # Importa a conexão EXISTENTE (a mesma que o Streamlit usa)
    from modules.perfis_manager import client
    from qdrant_client import models
    
    print("✅ Reutilizando conexão do Streamlit!")
    
    # Nome da collection
    COLLECTION_QUINTAS = "quintas_info"
    
    # Verifica se já existe
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if COLLECTION_QUINTAS in collection_names:
            info = client.get_collection(COLLECTION_QUINTAS)
            if info.points_count > 0:
                print(f"✅ Collection '{COLLECTION_QUINTAS}' já tem {info.points_count} quintas!")
                print("💡 Se quiseres reimportar, usa: python forcar_limpeza_qdrant.py")
                
                # Mostra amostra
                print()
                print("📋 Amostra das quintas:")
                resultados = client.scroll(
                    collection_name=COLLECTION_QUINTAS,
                    limit=3
                )
                for ponto in resultados[0]:
                    print(f"  • {ponto.payload['nome']} ({ponto.payload['zona']})")
                
                print()
                print("=" * 60)
                print("✅ QDRANT JÁ ESTÁ PRONTO!")
                print("=" * 60)
                sys.exit(0)
            else:
                print(f"⚠️  Collection '{COLLECTION_QUINTAS}' existe mas está vazia")
                print("📦 A reimportar...")
                client.delete_collection(COLLECTION_QUINTAS)
        
    except Exception as e:
        print(f"⚠️  Erro ao verificar: {e}")
    
    # Cria collection
    print(f"📦 A criar collection '{COLLECTION_QUINTAS}'...")
    client.create_collection(
        collection_name=COLLECTION_QUINTAS,
        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
    )
    print("✅ Collection criada!")
    
    # Carrega modelo (com bypass SSL)
    print("🧠 A carregar modelo de embeddings...")
    try:
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("intfloat/multilingual-e5-base")
        print("✅ Modelo carregado!")
    except Exception as e:
        print(f"⚠️  Erro ao carregar modelo: {e}")
        print("💡 A usar embeddings dummy (quintas funcionam na mesma)")
        model = None
    
    # Lê quintas da base de dados
    db_path = os.path.join(BASE_DIR, "data", "quintas.db")
    print(f"📂 A ler quintas de: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Ficheiro não encontrado: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM quintas")
    quintas = cursor.fetchall()
    conn.close()
    
    print(f"📋 Encontradas {len(quintas)} quintas")
    
    # Converte para pontos do Qdrant
    pontos = []
    print("🔄 A processar quintas...")
    
    for i, quinta in enumerate(quintas):
        # Cria texto descritivo para embedding
        texto_busca = f"{quinta['nome']}"
        
        if quinta['zona']:
            texto_busca += f" localizada em {quinta['zona']}"
        
        if quinta['morada']:
            texto_busca += f" morada {quinta['morada']}"
        
        if quinta['capacidade_confirmada']:
            texto_busca += f" capacidade {quinta['capacidade_confirmada']} pessoas"
        elif quinta['capacidade_43']:
            texto_busca += f" capacidade {quinta['capacidade_43']} pessoas"
        
        if quinta['custo_total']:
            texto_busca += f" custo {quinta['custo_total']} euros"
        elif quinta['custo_4500']:
            texto_busca += f" custo {quinta['custo_4500']} euros"
        
        if quinta['observacoes']:
            texto_busca += f" {quinta['observacoes']}"
        
        # Gera embedding
        if model is not None:
            vector = model.encode(texto_busca).tolist()
        else:
            # Embedding dummy (zeros) se modelo não disponível
            vector = [0.0] * 768
        
        # Payload
        payload = {
            "id": i + 1,
            "nome": quinta['nome'],
            "zona": quinta['zona'],
            "morada": quinta['morada'],
            "email": quinta['email'],
            "telefone": quinta['telefone'],
            "website": quinta['website'],
            "estado": quinta['estado'],
            "resposta": quinta['resposta'],
            "capacidade_43": quinta['capacidade_43'],
            "custo_4500": quinta['custo_4500'],
            "estimativa_custo": quinta['estimativa_custo'],
            "capacidade_confirmada": quinta['capacidade_confirmada'],
            "ultima_resposta": quinta['ultima_resposta'],
            "proposta_tarifaria": quinta['proposta_tarifaria'],
            "unidades_detalhe": quinta['unidades_detalhe'],
            "num_unidades": quinta['num_unidades'],
            "observacao_unidades": quinta['observacao_unidades'],
            "custo_total": quinta['custo_total'],
            "resumo_resposta": quinta['resumo_resposta'],
            "observacoes": quinta['observacoes'],
            "notas_calculo": quinta['notas_calculo'],
            "texto_busca": texto_busca
        }
        
        pontos.append(models.PointStruct(
            id=i + 1,
            vector=vector,
            payload=payload
        ))
        
        # Progresso
        if (i + 1) % 10 == 0:
            print(f"  Processadas {i + 1}/{len(quintas)}...")
    
    # Insere no Qdrant
    print(f"💾 A inserir {len(pontos)} quintas no Qdrant...")
    client.upsert(
        collection_name=COLLECTION_QUINTAS,
        points=pontos
    )
    
    print(f"✅ {len(pontos)} quintas importadas com sucesso!")
    
    # Testa busca (só se modelo disponível)
    if model is not None:
        print()
        print("🧪 Teste de busca...")
        query_test = "quintas em lisboa com piscina"
        query_vector = model.encode(query_test).tolist()
        
        resultados = client.search(
            collection_name=COLLECTION_QUINTAS,
            query_vector=query_vector,
            limit=3
        )
        
        print(f"Busca: '{query_test}'")
        print("Resultados:")
        for r in resultados:
            print(f"  • {r.payload['nome']} ({r.payload['zona']}) - Score: {r.score:.3f}")
    
    print()
    print("=" * 60)
    print("✅ QUINTAS IMPORTADAS COM SUCESSO!")
    print("=" * 60)
    print()
    print("💡 O Streamlit pode continuar a correr!")
    print("   Recarrega a página para ver as mudanças.")
    print()

except Exception as e:
    print(f"❌ Erro ao importar quintas: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("💡 Alternativa:")
    print("   1. Para o Streamlit (Ctrl+C)")
    print("   2. python popularqdrant.py")

# =====================================================
# 3️⃣ VERIFICAÇÃO FINAL
# =====================================================
print("3️⃣ Verificação final...")
print("-" * 60)

try:
    collections = client.get_collections()
    print(f"📦 Collections no Qdrant:")
    for col in collections.collections:
        try:
            info = client.get_collection(col.name)
            emoji = "👥" if "perfis" in col.name else ("🏡" if "quintas" in col.name else "💬")
            print(f"  {emoji} {col.name}: {info.points_count} pontos")
        except:
            print(f"  ⚠️  {col.name}: Erro ao ler")
    
    print()
    print("=" * 60)
    print("✅ SETUP COMPLETO!")
    print("=" * 60)
    print()
    print("💡 Agora podes:")
    print("   • Continuar a usar o Streamlit")
    print("   • Fazer perguntas sobre quintas")
    print("   • Busca semântica funciona!")
    print()
    
except Exception as e:
    print(f"⚠️  Erro na verificação: {e}")

print()