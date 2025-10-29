"""
🌩️ POPULAR QDRANT CLOUD - Script Standalone
Importa perfis e quintas para o Qdrant Cloud
Pede credenciais manualmente (não depende de Streamlit)
"""

import json
import sqlite3
import sys
from pathlib import Path

try:
    from qdrant_client import QdrantClient, models
    import numpy as np
except ImportError:
    print("❌ Instala: pip install qdrant-client numpy")
    sys.exit(1)

# =====================================================
# 🔑 CREDENCIAIS
# =====================================================

print("=" * 60)
print("🔑 CREDENCIAIS DO QDRANT CLOUD")
print("=" * 60)
print()

QDRANT_URL = input("URL do Qdrant (ex: https://xxx.cloud.qdrant.io:6333): ").strip()
QDRANT_API_KEY = input("API Key: ").strip()

if not QDRANT_URL or not QDRANT_API_KEY:
    print("\n❌ Credenciais inválidas!")
    sys.exit(1)

print()
print(f"☁️  Conectando a: {QDRANT_URL}")

try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # Testa conexão
    collections = client.get_collections()
    print(f"✅ Conectado! ({len(collections.collections)} coleções existentes)")
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    sys.exit(1)

# =====================================================
# 👥 IMPORTAR PERFIS
# =====================================================

print("\n" + "=" * 60)
print("👥 IMPORTAR PERFIS")
print("=" * 60)

COLLECTION_PERFIS = "perfis_convidados"
PERFIS_JSON = Path("data/perfis_base.json")

# Verifica se ficheiro existe
if not PERFIS_JSON.exists():
    print(f"❌ Ficheiro não encontrado: {PERFIS_JSON}")
    print("   Executa este script na pasta do projeto!")
    sys.exit(1)

# Cria/verifica collection
try:
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if COLLECTION_PERFIS in collection_names:
        resposta = input(f"\n⚠️  Collection '{COLLECTION_PERFIS}' já existe. Apagar e recriar? (s/N): ").strip().lower()
        if resposta == 's':
            print(f"🗑️  Apagando collection antiga...")
            client.delete_collection(COLLECTION_PERFIS)
            print("✅ Apagada!")
        else:
            print("⏭️  Mantendo collection existente")
    
    # Cria collection
    if COLLECTION_PERFIS not in [c.name for c in client.get_collections().collections]:
        print(f"📦 Criando collection '{COLLECTION_PERFIS}'...")
        client.create_collection(
            collection_name=COLLECTION_PERFIS,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print("✅ Collection criada!")

except Exception as e:
    print(f"❌ Erro ao criar collection: {e}")
    sys.exit(1)

# Lê perfis do JSON
try:
    with open(PERFIS_JSON, "r", encoding="utf-8") as f:
        perfis = json.load(f)
    print(f"\n📦 {len(perfis)} perfis carregados do JSON")
except Exception as e:
    print(f"❌ Erro ao ler JSON: {e}")
    sys.exit(1)

# Importa perfis
print("\n🔄 Importando perfis para o Qdrant Cloud...")
print()

pontos = []
point_id = 0

for perfil in perfis:
    nome = perfil.get("nome", "Desconhecido")
    apelido = perfil.get("apelido", "")
    familia_id = perfil.get("familia_id", "")
    personalidade = perfil.get("personalidade", {})
    
    # Cria 6 embeddings dummy por perfil
    # (Em produção, usarias embeddings reais)
    for i in range(6):
        point_id += 1
        
        pontos.append(
            models.PointStruct(
                id=point_id,  # ✅ INTEGER em vez de string
                vector=np.zeros(768).tolist(),  # Vetor dummy (zeros)
                payload={
                    "nome": nome,
                    "apelido": apelido,
                    "familia_id": familia_id,
                    "personalidade": personalidade,
                    "humor": personalidade.get("humor", ""),
                    "topicos": personalidade.get("topicos_conversa", []),
                    "relacoes": perfil.get("relacoes", {}),
                    "historico": perfil.get("historico_interacoes", []),
                }
            )
        )
    
    print(f"  ✅ {nome}")

# Upload em batch
try:
    print(f"\n☁️  Enviando {len(pontos)} pontos para o cloud...")
    client.upsert(
        collection_name=COLLECTION_PERFIS,
        points=pontos
    )
    print(f"✅ {len(pontos)} pontos importados com sucesso!")
except Exception as e:
    print(f"❌ Erro ao importar perfis: {e}")
    sys.exit(1)

# =====================================================
# 🏡 IMPORTAR QUINTAS
# =====================================================

print("\n" + "=" * 60)
print("🏡 IMPORTAR QUINTAS")
print("=" * 60)

COLLECTION_QUINTAS = "quintas_info"
QUINTAS_DB = Path("data/quintas.db")

# Verifica se ficheiro existe
if not QUINTAS_DB.exists():
    print(f"❌ Ficheiro não encontrado: {QUINTAS_DB}")
    sys.exit(1)

# Cria/verifica collection
try:
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    
    if COLLECTION_QUINTAS in collection_names:
        resposta = input(f"\n⚠️  Collection '{COLLECTION_QUINTAS}' já existe. Apagar e recriar? (s/N): ").strip().lower()
        if resposta == 's':
            print(f"🗑️  Apagando collection antiga...")
            client.delete_collection(COLLECTION_QUINTAS)
            print("✅ Apagada!")
    
    # Cria collection
    if COLLECTION_QUINTAS not in [c.name for c in client.get_collections().collections]:
        print(f"📦 Criando collection '{COLLECTION_QUINTAS}'...")
        client.create_collection(
            collection_name=COLLECTION_QUINTAS,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print("✅ Collection criada!")

except Exception as e:
    print(f"❌ Erro ao criar collection: {e}")

# Lê quintas do SQLite
try:
    conn = sqlite3.connect(QUINTAS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quintas")
    quintas = cursor.fetchall()
    conn.close()
    print(f"\n📦 {len(quintas)} quintas carregadas do SQLite")
except Exception as e:
    print(f"❌ Erro ao ler SQLite: {e}")
    sys.exit(1)

# Importa quintas
print("\n🔄 Importando quintas para o Qdrant Cloud...")
print()

pontos_quintas = []
quinta_id = 1000  # Começa de 1000 para não conflitar com perfis

for quinta in quintas:
    # Converte Row para dict
    quinta_dict = dict(quinta)
    
    quinta_id += 1
    
    pontos_quintas.append(
        models.PointStruct(
            id=quinta_id,  # ✅ INTEGER
            vector=np.zeros(768).tolist(),  # Vetor dummy
            payload=quinta_dict
        )
    )
    
    print(f"  ✅ {quinta_dict.get('nome', 'Sem nome')}")

# Upload
try:
    print(f"\n☁️  Enviando {len(pontos_quintas)} quintas para o cloud...")
    client.upsert(
        collection_name=COLLECTION_QUINTAS,
        points=pontos_quintas
    )
    print(f"✅ {len(pontos_quintas)} quintas importadas com sucesso!")
except Exception as e:
    print(f"❌ Erro ao importar quintas: {e}")

# =====================================================
# 📊 RESUMO FINAL
# =====================================================

print("\n" + "=" * 60)
print("📊 RESUMO FINAL")
print("=" * 60)
print()

for col_name in [COLLECTION_PERFIS, COLLECTION_QUINTAS]:
    try:
        info = client.get_collection(col_name)
        emoji = "👥" if "perfis" in col_name else "🏡"
        print(f"{emoji} {col_name}: {info.points_count} pontos")
    except:
        print(f"⚠️  {col_name}: Não encontrada")

print()
print("=" * 60)
print("✅ IMPORTAÇÃO CONCLUÍDA!")
print("=" * 60)
print()
print("🎯 Próximos passos:")
print("  1. Reinicia o Streamlit:")
print("     streamlit run app.py")
print()
print("  2. Deve aparecer:")
print("     ✅ 35 perfis carregados do Qdrant")
print()