#!/usr/bin/env python3
"""
Script para Verificar Estado do Qdrant
Mostra quantos perfis e quintas estão carregados
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

print("=" * 60)
print("🔍 VERIFICAR ESTADO DO QDRANT")
print("=" * 60)
print()

try:
    from qdrant_client import QdrantClient
    
    # Tenta conectar ao Qdrant
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        print("☁️  Conectado ao Qdrant Cloud")
    else:
        qdrant_path = os.path.join(BASE_DIR, "qdrant_data")
        try:
            client = QdrantClient(path=qdrant_path)
            print(f"💾 Conectado ao Qdrant local: {qdrant_path}")
        except RuntimeError as e:
            if "already accessed" in str(e):
                print("⚠️  QDRANT JÁ ESTÁ EM USO!")
                print()
                print("Isto significa que:")
                print("  • O Streamlit está a correr, OU")
                print("  • Outro script Python está a usar o Qdrant")
                print()
                print("💡 Para ver o estado:")
                print("   1. Para o Streamlit (Ctrl+C)")
                print("   2. Executa este script novamente")
                print()
                print("OU adiciona isto no teu app.py para ver:")
                print()
                print("```python")
                print("from modules.perfis_manager import client, COLLECTION_PERFIS")
                print("info_perfis = client.get_collection(COLLECTION_PERFIS)")
                print("st.write(f'Perfis: {info_perfis.points_count}')")
                print("```")
                sys.exit(1)
            else:
                raise
    
    print()
    print("-" * 60)
    print("📦 COLLECTIONS DISPONÍVEIS:")
    print("-" * 60)
    
    # Lista todas as collections
    collections = client.get_collections()
    
    if not collections.collections:
        print("❌ Nenhuma collection encontrada!")
        print("💡 Executa: python popularqdrant.py")
        sys.exit(1)
    
    total_pontos = 0
    collections_info = []
    
    for col in collections.collections:
        try:
            info = client.get_collection(col.name)
            pontos = info.points_count
            total_pontos += pontos
            
            # Emoji baseado no tipo
            if "perfis" in col.name:
                emoji = "👥"
            elif "quintas" in col.name:
                emoji = "🏡"
            else:
                emoji = "💬"
            
            collections_info.append({
                "nome": col.name,
                "emoji": emoji,
                "pontos": pontos
            })
            
            print(f"{emoji} {col.name}: {pontos} pontos")
            
        except Exception as e:
            print(f"⚠️  {col.name}: Erro ao ler - {e}")
    
    print("-" * 60)
    print(f"📊 TOTAL: {total_pontos} pontos em {len(collections_info)} collections")
    print()
    
    # Análise do estado
    print("=" * 60)
    print("📋 ANÁLISE:")
    print("=" * 60)
    
    tem_perfis = any("perfis" in c["nome"] for c in collections_info)
    tem_quintas = any("quintas" in c["nome"] for c in collections_info)
    
    if tem_perfis:
        perfis_col = next(c for c in collections_info if "perfis" in c["nome"])
        if perfis_col["pontos"] > 0:
            print(f"✅ Perfis: {perfis_col['pontos']} convidados carregados")
        else:
            print(f"⚠️  Perfis: Collection existe mas está vazia!")
    else:
        print("❌ Perfis: Collection não existe")
        print("   💡 Executa: python popularqdrant.py")
    
    if tem_quintas:
        quintas_col = next(c for c in collections_info if "quintas" in c["nome"])
        if quintas_col["pontos"] > 0:
            print(f"✅ Quintas: {quintas_col['pontos']} quintas carregadas")
        else:
            print(f"⚠️  Quintas: Collection existe mas está vazia!")
    else:
        print("❌ Quintas: Collection não existe")
        print("   💡 Executa: python popularqdrant.py")
    
    # Mostra amostra de dados
    if tem_perfis and perfis_col["pontos"] > 0:
        print()
        print("-" * 60)
        print("👥 AMOSTRA DE PERFIS (primeiros 3):")
        print("-" * 60)
        
        perfis_col_name = perfis_col["nome"]
        resultados = client.scroll(
            collection_name=perfis_col_name,
            limit=3
        )
        
        for ponto in resultados[0]:
            print(f"  • {ponto.payload.get('nome', 'N/A')} ({ponto.payload.get('tipo', 'N/A')})")
    
    if tem_quintas and quintas_col["pontos"] > 0:
        print()
        print("-" * 60)
        print("🏡 AMOSTRA DE QUINTAS (primeiras 3):")
        print("-" * 60)
        
        quintas_col_name = quintas_col["nome"]
        resultados = client.scroll(
            collection_name=quintas_col_name,
            limit=3
        )
        
        for ponto in resultados[0]:
            nome = ponto.payload.get('nome', 'N/A')
            zona = ponto.payload.get('zona', 'N/A')
            print(f"  • {nome} ({zona})")
    
    print()
    print("=" * 60)
    
    # Conclusão
    if tem_perfis and tem_quintas and perfis_col["pontos"] > 0 and quintas_col["pontos"] > 0:
        print("✅ TUDO PRONTO!")
        print("   O Qdrant está corretamente populado.")
        print("   Podes iniciar o Streamlit: streamlit run app.py")
    elif tem_perfis and perfis_col["pontos"] > 0 and (not tem_quintas or quintas_col["pontos"] == 0):
        print("⚠️  PARCIALMENTE PRONTO")
        print("   • Perfis: OK ✅")
        print("   • Quintas: FALTAM ❌")
        print()
        print("💡 Para importar quintas:")
        print("   1. Para o Streamlit (se estiver a correr)")
        print("   2. python popularqdrant.py")
    else:
        print("❌ SETUP INCOMPLETO")
        print("   Executa: python popularqdrant.py")
    
    print("=" * 60)
    print()

except Exception as e:
    print(f"❌ Erro ao verificar Qdrant: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("💡 Possíveis causas:")
    print("   • Qdrant não inicializado (executa: python popularqdrant.py)")
    print("   • Problema de conexão")
    print("   • Qdrant em uso por outro processo")