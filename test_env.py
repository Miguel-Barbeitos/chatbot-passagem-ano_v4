import os

print("🔍 VERIFICANDO VARIÁVEIS DE AMBIENTE")
print("=" * 60)

qdrant_url = os.getenv("QDRANT_URL")
qdrant_key = os.getenv("QDRANT_API_KEY")

if qdrant_url:
    print(f"✅ QDRANT_URL: {qdrant_url[:30]}...")
else:
    print("❌ QDRANT_URL: NÃO DEFINIDA")

if qdrant_key:
    print(f"✅ QDRANT_API_KEY: {qdrant_key[:10]}...")
else:
    print("❌ QDRANT_API_KEY: NÃO DEFINIDA")

print()

# Tenta conectar
if qdrant_url and qdrant_key:
    from qdrant_client import QdrantClient
    
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        collections = client.get_collections()
        
        print("✅ CONEXÃO FUNCIONA!")
        print(f"📦 Coleções: {len(collections.collections)}")
        
        for col in collections.collections:
            info = client.get_collection(col.name)
            print(f"  • {col.name}: {info.points_count} pontos")
    
    except Exception as e:
        print(f"❌ ERRO AO CONECTAR: {e}")
else:
    print("❌ NÃO PODE CONECTAR (faltam variáveis)")