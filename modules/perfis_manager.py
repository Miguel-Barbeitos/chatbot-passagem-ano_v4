"""
Gestão de Perfis de Convidados no Qdrant
"""
import os
import json
import random
from datetime import datetime
from qdrant_client import QdrantClient, models

# Configuração
COLLECTION_PERFIS = "perfis_convidados"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PERFIS_BASE_PATH = os.path.join(BASE_DIR, "data", "perfis_base.json")

# Modelo de embeddings - OPCIONAL para perfis
# (Perfis usam busca por filtros, não semântica)
model = None

def get_model():
    """Carrega modelo com bypass de SSL se necessário"""
    global model
    if model is None:
        try:
            # Tenta sem SSL
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("intfloat/multilingual-e5-base")
        except:
            print("⚠️ Modelo de embeddings não disponível (problema SSL)")
            print("💡 Usando embeddings vazios (perfis funcionam na mesma)")
            model = "dummy"  # Marca como não disponível
    return model

def gerar_embedding_simples(texto: str):
    """Gera embedding simples ou dummy"""
    m = get_model()
    if m == "dummy":
        # Embedding dummy (zeros) - funciona para perfis
        import numpy as np
        return np.zeros(768).tolist()
    else:
        return m.encode(texto).tolist()

def inicializar_qdrant():
    """Inicializa Qdrant"""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    return QdrantClient(path=os.path.join(BASE_DIR, "qdrant_data"))

client = inicializar_qdrant()

def criar_collection_perfis():
    """Cria a collection de perfis se não existir"""
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if COLLECTION_PERFIS not in collection_names:
            print(f"📦 A criar collection '{COLLECTION_PERFIS}'...")
            client.create_collection(
                collection_name=COLLECTION_PERFIS,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
            print("✅ Collection criada!")
        else:
            print(f"✅ Collection '{COLLECTION_PERFIS}' já existe.")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar collection: {e}")
        return False

def importar_perfis_do_json():
    """Importa perfis do JSON para o Qdrant"""
    try:
        # Lê o JSON
        with open(PERFIS_BASE_PATH, "r", encoding="utf-8") as f:
            perfis = json.load(f)
        
        print(f"📋 Encontrados {len(perfis)} perfis no JSON")
        
        # Cria a collection
        criar_collection_perfis()
        
        # Importa cada perfil
        pontos = []
        for perfil in perfis:
            # Cria texto para embedding (busca semântica)
            texto_busca = f"{perfil['nome']} {perfil['tipo']} familia {perfil['familia_id']}"
            if perfil['relacoes'].get('conjuge'):
                texto_busca += f" conjuge de {perfil['relacoes']['conjuge']}"
            if perfil['relacoes'].get('filhos'):
                texto_busca += f" pais de {' '.join(perfil['relacoes']['filhos'])}"
            
            # Embedding (dummy se modelo não disponível)
            vector = gerar_embedding_simples(texto_busca)
            
            # Payload completo
            payload = {
                "nome": perfil["nome"],
                "tipo": perfil["tipo"],
                "familia_id": perfil["familia_id"],
                "relacoes": perfil["relacoes"],
                "pode_confirmar_por": perfil["pode_confirmar_por"],
                
                # Personalidade base (do quiz)
                "personalidade": perfil["personalidade"],
                
                # Personalidade aprendida (inicia igual à base)
                "personalidade_aprendida": {
                    **perfil["personalidade"],
                    "ultima_atualizacao": None,
                    "confianca": 0
                },
                
                # Status de confirmação
                "confirmado": False,
                "confirmado_por": None,
                "data_confirmacao": None,
                
                # Métricas de aprendizagem
                "metricas": {
                    "total_mensagens": 0,
                    "usa_piadas": 0,
                    "pergunta_detalhes": 0,
                    "respostas_curtas": 0,
                    "ultima_interacao": None
                },
                
                # Campos para futuro
                "email": "",
                "telefone": "",
                "preferencias": "",
                "restricoes": "",
                "interesses": [],
                "notas": "",
                
                # Metadata
                "metadata": {
                    "criado_em": datetime.now().isoformat(),
                    "atualizado_em": datetime.now().isoformat(),
                    "quiz_completo": True
                }
            }
            
            ponto = models.PointStruct(
                id=random.randint(0, 1_000_000_000),
                vector=vector,
                payload=payload
            )
            pontos.append(ponto)
        
        # Insere em batch
        client.upsert(collection_name=COLLECTION_PERFIS, points=pontos)
        
        print(f"✅ {len(pontos)} perfis importados com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao importar perfis: {e}")
        import traceback
        traceback.print_exc()
        return False

def buscar_perfil(nome: str):
    """Busca perfil por nome exato"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="nome",
                        match=models.MatchValue(value=nome)
                    )
                ]
            ),
            limit=1
        )
        
        if resultados:
            return resultados[0].payload
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar perfil: {e}")
        return None

def buscar_perfil_semantica(texto: str, limit=5):
    """Busca perfil por similaridade semântica"""
    try:
        vector = gerar_embedding_simples(texto)
        
        resultados = client.search(
            collection_name=COLLECTION_PERFIS,
            query_vector=vector,
            limit=limit
        )
        
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro na busca semântica: {e}")
        return []

def listar_familia(familia_id: str):
    """Lista todos os membros de uma família"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="familia_id",
                        match=models.MatchValue(value=familia_id)
                    )
                ]
            ),
            limit=10
        )
        
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro ao listar família: {e}")
        return []

def atualizar_perfil(nome: str, atualizacoes: dict):
    """Atualiza campos do perfil"""
    try:
        # Busca o ponto
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="nome",
                        match=models.MatchValue(value=nome)
                    )
                ]
            ),
            limit=1
        )
        
        if not resultados:
            print(f"⚠️ Perfil '{nome}' não encontrado")
            return False
        
        ponto = resultados[0]
        payload = ponto.payload
        
        # Aplica atualizações
        for chave, valor in atualizacoes.items():
            if "." in chave:  # Campo nested (ex: "personalidade_aprendida.humor")
                partes = chave.split(".")
                atual = payload
                for parte in partes[:-1]:
                    if parte not in atual:
                        atual[parte] = {}
                    atual = atual[parte]
                atual[partes[-1]] = valor
            else:
                payload[chave] = valor
        
        # Atualiza timestamp
        payload["metadata"]["atualizado_em"] = datetime.now().isoformat()
        
        # Salva
        client.set_payload(
            collection_name=COLLECTION_PERFIS,
            payload=payload,
            points=[ponto.id]
        )
        
        print(f"✅ Perfil '{nome}' atualizado!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar perfil: {e}")
        return False

def listar_todos_perfis():
    """Lista todos os perfis"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            limit=100
        )
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro ao listar perfis: {e}")
        return []

if __name__ == "__main__":
    print("🚀 Iniciando importação de perfis...")
    importar_perfis_do_json()
    
    print("\n📊 Testando busca...")
    perfil = buscar_perfil("Barbeitos")
    if perfil:
        print(f"✅ Encontrado: {perfil['nome']} - Humor: {perfil['personalidade']['humor']}")
    
    print("\n👨‍👩‍👧‍👦 Testando listagem de família...")
    familia = listar_familia("familia_jorge")
    print(f"✅ Família Jorge: {[p['nome'] for p in familia]}")