# -*- coding: utf-8 -*-
"""
Testa a leitura das relações familiares no Qdrant.
Filtra perfis duplicados e mostra apenas o mais relevante.
"""

from qdrant_client import QdrantClient
import streamlit as st

# =====================================================
# 🔑 Ligação ao Qdrant Cloud via Streamlit secrets
# =====================================================
try:
    url = st.secrets["QDRANT_URL"]
    api_key = st.secrets["QDRANT_API_KEY"]
    client = QdrantClient(url=url, api_key=api_key)
    print(f"☁️ Ligado a Qdrant Cloud: {url}")
except Exception as e:
    raise RuntimeError("❌ Falha ao ligar ao Qdrant. Verifica o ficheiro .streamlit/secrets.toml.") from e

collection = "perfis_convidados"

# =====================================================
# 🔍 Função para ler um perfil e suas relações
# =====================================================
def mostrar_relacoes(nome):
    resultados, _ = client.scroll(
        collection_name=collection,
        scroll_filter={"must": [{"key": "nome", "match": {"value": nome}}]},
        limit=50
    )

    if not resultados:
        print(f"❌ Nenhum perfil encontrado com o nome '{nome}'.")
        return

    # Ordenar para preferir confirmados
    resultados_ordenados = sorted(resultados, key=lambda r: r.payload.get("confirmado", False), reverse=True)
    r = resultados_ordenados[0]

    payload = r.payload
    relacoes = payload.get("relacoes", {})
    confirmado = payload.get("confirmado", False)
    familia = payload.get("familia_id", "?")

    print(f"\n👤 Perfil principal encontrado:")
    print(f"   Nome: {nome}")
    print(f"   Confirmado: {'✅ Sim' if confirmado else '❌ Não'}")
    print(f"   Família: {familia}")
    print(f"   Relações: {relacoes}")

    if relacoes:
        if "conjuge" in relacoes:
            print(f"   ❤️ Cônjuge: {relacoes['conjuge']}")
        if "filhos" in relacoes:
            print(f"   👧 Filhos: {', '.join(relacoes['filhos'])}")
        if "pais" in relacoes:
            print(f"   👨‍👩‍👧 Pais: {', '.join(relacoes['pais'])}")
    else:
        print("⚠️ Este perfil não tem campo 'relacoes'.")

# =====================================================
# 🧪 Testes com nomes de exemplo
# =====================================================
if __name__ == "__main__":
    for nome in ["Isabel", "Jorge", "Catarina", "Diogo"]:
        mostrar_relacoes(nome)
