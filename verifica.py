# -*- coding: utf-8 -*-
"""
Script de diagnóstico do Qdrant Cloud
Verifica ligação, coleções e confirmações.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os

# ======================================================
# CONFIGURAÇÃO (podes substituir pela tua API key)
# ======================================================

QDRANT_URL = os.getenv("QDRANT_URL") or "https://53262e06-1c9b-4530-a703-94f9e573b71a.europe-west3-0.gcp.cloud.qdrant.io:6333"
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8j0MluKJ7Hzk0B2Fey7FBsbQXvr21rvkNlsKCH1COpo" 

print("🔑 Teste de ligação ao Qdrant Cloud...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

try:
    collections = client.get_collections()
    print("\n✅ Ligação bem-sucedida!")
    print("Coleções disponíveis:")
    for c in collections.collections:
        print(f" • {c.name}")
except Exception as e:
    print(f"❌ Erro ao listar coleções: {e}")
    exit()

# ======================================================
# TESTE DE CONFIRMAÇÕES
# ======================================================

try:
    print("\n🔍 A procurar perfis confirmados...")
    results, _ = client.scroll(
        collection_name="perfis_convidados",
        scroll_filter=Filter(
            must=[FieldCondition(key="confirmado", match=MatchValue(value=True))]
        ),
        limit=50
    )

    if not results:
        print("⚠️ Nenhum perfil encontrado com confirmado=True.")
    else:
        print(f"✅ {len(results)} perfis confirmados encontrados:\n")
        for r in results:
            nome = r.payload.get("nome")
            familia = r.payload.get("familia_id", "")
            confirmado_por = r.payload.get("confirmado_por", "")
            print(f" • {nome} ({familia}) — confirmado por {confirmado_por}")

except Exception as e:
    print(f"❌ Erro ao procurar confirmados: {e}")
