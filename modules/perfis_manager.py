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
    """Inicializa Qdrant - tenta env vars, depois Streamlit secrets, depois local"""
    qdrant_url = None
    qdrant_key = None
    
    # 1. Tenta variáveis de ambiente (quando executado fora do Streamlit)
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    # 2. Se não encontrou, tenta Streamlit secrets
    if not qdrant_url or not qdrant_key:
        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                qdrant_url = st.secrets.get("QDRANT_URL")
                qdrant_key = st.secrets.get("QDRANT_API_KEY")
                if qdrant_url and qdrant_key:
                    print("☁️  Usando credenciais do Streamlit secrets")
        except Exception as e:
            pass
    
    # 3. Se encontrou credenciais cloud, usa Qdrant Cloud
    if qdrant_url and qdrant_key:
        print(f"☁️  Conectando ao Qdrant Cloud: {qdrant_url}")
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    # 4. Fallback: Qdrant local
    print("💾 Conectando ao Qdrant local...")
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
        # Sem filtro - busca todos e filtra manualmente (mais lento mas funciona sem índice)
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            limit=100  # Pega todos
        )
        
        # Filtra manualmente por nome
        for resultado in resultados:
            if resultado.payload.get('nome') == nome:
                return resultado.payload
        
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
        # Sem filtro - busca todos e filtra manualmente
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            limit=100
        )
        
        # Filtra manualmente por familia_id
        familia = []
        for resultado in resultados:
            if resultado.payload.get('familia_id') == familia_id:
                familia.append(resultado.payload)
        
        return familia
    except Exception as e:
        print(f"❌ Erro ao listar família: {e}")
        return []

def atualizar_perfil(nome: str, atualizacoes: dict):
    """Atualiza campos do perfil"""
    try:
        # Busca sem filtro e filtra manualmente
        resultados, _ = client.scroll(
            collection_name=COLLECTION_PERFIS,
            limit=100
        )
        
        # Procura o perfil manualmente
        ponto = None
        for resultado in resultados:
            if resultado.payload.get('nome') == nome:
                ponto = resultado
                break
        
        if not ponto:
            print(f"⚠️ Perfil '{nome}' não encontrado")
            return False
        
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
        if "metadata" not in payload:
            payload["metadata"] = {}
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
    """Lista todos os perfis únicos (agrupa por nome)"""
    try:
        # Scroll TODOS os pontos (pode haver múltiplos pontos por perfil)
        offset = None
        todos_pontos = []
        
        while True:
            resultados, offset = client.scroll(
                collection_name=COLLECTION_PERFIS,
                limit=100,
                offset=offset
            )
            
            if not resultados:
                break
            
            todos_pontos.extend(resultados)
            
            if offset is None:
                break
        
        # Agrupa por perfil único (usa 'nome' como chave)
        perfis_unicos = {}
        for ponto in todos_pontos:
            nome = ponto.payload.get('nome')
            if nome and nome not in perfis_unicos:
                perfis_unicos[nome] = ponto.payload
        
        print(f"📦 Qdrant: {len(todos_pontos)} pontos → {len(perfis_unicos)} perfis únicos")
        
        return list(perfis_unicos.values())
    
    except Exception as e:
        print(f"❌ Erro ao listar perfis: {e}")
        import traceback
        traceback.print_exc()
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