from qdrant_client import QdrantClient
import streamlit as st

def get_client():
    url = st.secrets["QDRANT_URL"]
    api_key = st.secrets["QDRANT_API_KEY"]
    return QdrantClient(url=url, api_key=api_key)

client = get_client()
collection = "perfis_convidados"

print("🔍 A procurar confirmados...")

results, _ = client.scroll(
    collection_name=collection,
    scroll_filter={"must": [{"key": "confirmado", "match": {"value": True}}]},
    limit=100
)

if not results:
    print("⚠️ Nenhum confirmado encontrado.")
else:
    print(f"✅ Encontrados {len(results)} confirmados:\n")
    for r in results:
        print(f"• {r.payload.get('nome')} ({r.payload.get('familia_id')})")
