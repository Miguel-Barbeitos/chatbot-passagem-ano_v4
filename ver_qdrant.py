from qdrant_client import QdrantClient
import streamlit as st

# Lê chaves do secrets.toml
url = st.secrets["QDRANT_URL"]
api_key = st.secrets["QDRANT_API_KEY"]

client = QdrantClient(url=url, api_key=api_key)

print("🔍 A ler perfis do Qdrant...\n")

results, _ = client.scroll(collection_name="perfis_convidados", limit=3)

for r in results:
    print("🧠 POINT ID:", r.id)
    print("PAYLOAD:", r.payload)
    print("-" * 60)
